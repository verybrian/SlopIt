import os
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.admin import bp
from app.models import Collection, Entry, User
from app.models.user import UserRole
from app.models.api_key import ApiKey
from app.utils import generate_invite_token, send_invite_email
from app.services.s3 import S3Service
from werkzeug.utils import secure_filename
from app import db
from datetime import datetime, timedelta, timezone


@bp.route('/')
@login_required
def dashboard():
    pages_collection = Collection.query.filter_by(name='pages').first()
    posts_collection = Collection.query.filter_by(name='posts').first()
    
    stats = {
        'pages_total': Entry.query.filter_by(collection_id=pages_collection.id).count() if pages_collection else 0,
        'pages_published': Entry.query.filter_by(
            collection_id=pages_collection.id, status='published'
        ).count() if pages_collection else 0,
        'posts_total': Entry.query.filter_by(collection_id=posts_collection.id).count() if posts_collection else 0,
        'posts_published': Entry.query.filter_by(
            collection_id=posts_collection.id, status='published'
        ).count() if posts_collection else 0,
        'media_total': 0,  # Placeholder for media system
        'users_total': User.query.count(),
    }
    
    recent_posts = []
    if posts_collection:
        entries = Entry.query.filter_by(
            collection_id=posts_collection.id
        ).order_by(Entry.updated_at.desc()).limit(5).all()
        
        for entry in entries:
            post_data = entry.to_dict()
            author_name = 'System'
            author_value = entry.get_value('author')
            if author_value:
                author_name = author_value
            
            recent_posts.append({
                'id': entry.id,
                'title': post_data.get('title', 'Untitled'),
                'status': entry.status,
                'author': {'username': author_name},
                'updated_at': entry.updated_at
            })
    
    activity = generate_activity_feed()
    
    return render_template('admin/dashboard.html',
                         stats=stats,
                         recent_posts=recent_posts,
                         activity=activity)

def generate_activity_feed():
    activities = []
    
    recent_entries = Entry.query.order_by(
        Entry.updated_at.desc()
    ).limit(8).all()
    
    for entry in recent_entries:
        collection = Collection.query.get(entry.collection_id)
        entry_data = entry.to_dict()
        title = entry_data.get('title', 'Untitled')
        
        if entry.status == 'published':
            action = f'published "{title}" in {collection.label}'
            activity_type = 'publish'
        elif entry.created_at == entry.updated_at:
            action = f'created "{title}" in {collection.label}'
            activity_type = 'create'
        else:
            action = f'edited "{title}" in {collection.label}'
            activity_type = 'edit'
        
        activities.append({
            'actor': 'Admin',
            'action': action,
            'type': activity_type,
            'timestamp': entry.updated_at
        })
    
    return activities

@bp.route('/users')
@login_required
def user_list():
    if current_user.role.value != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('admin.dashboard'))
    
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/user_list.html', users=users)

@bp.route('/users/invite', methods=['GET', 'POST'])
@login_required
def user_invite():
    if current_user.role.value != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('admin.dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('A user with that email already exists.', 'error')
            return redirect(url_for('admin.user_invite'))
        
        token = generate_invite_token(email)
        
        user = User(
            username=f"pending_{token[:8]}",
            email=email,
            role=UserRole.EDITOR,
            is_active=False,
            invite_token=token,
            invite_expires_at=datetime.now(timezone.utc) + timedelta(days=7)
        )
        user.set_password(token)
        
        db.session.add(user)
        db.session.commit()
        
        send_invite_email(email, token)
        
        flash(f'Invitation sent to {email}. They have 7 days to accept.', 'success')
        return redirect(url_for('admin.user_list'))
    
    return render_template('admin/user_invite.html')

@bp.route('/users/<user_id>/delete', methods=['POST'])
@login_required
def user_delete(user_id):
    if current_user.role.value != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('admin.dashboard'))
    
    user = User.query.get_or_404(user_id)
    
    if user.id == current_user.id:
        flash('You cannot delete your own account.', 'error')
        return redirect(url_for('admin.user_list'))
    
    db.session.delete(user)
    db.session.commit()
    
    flash(f'User "{user.username}" deleted.', 'success')
    return redirect(url_for('admin.user_list'))


@bp.route('/api-keys')
@login_required
def api_keys():
    if current_user.role.value != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('admin.dashboard'))
    
    keys = ApiKey.query.order_by(ApiKey.created_at.desc()).all()
    return render_template('admin/api_keys.html', keys=keys)

@bp.route('/api-keys/generate', methods=['POST'])
@login_required
def api_key_generate():
    if current_user.role.value != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('admin.dashboard'))
    
    name = request.form.get('name', '').strip()
    if not name:
        flash('Please provide a name for the key.', 'error')
        return redirect(url_for('admin.api_keys'))
    
    public_key, secret_key = ApiKey.generate_keys()
    
    api_key = ApiKey(
        name=name,
        public_key=public_key,
        secret_hash=ApiKey.hash_secret(secret_key),
        created_by=current_user.id
    )
    
    db.session.add(api_key)
    db.session.commit()
    
    flash(f'API key created! Secret key (shown once): {secret_key}', 'success')
    return redirect(url_for('admin.api_keys'))

@bp.route('/api-keys/<key_id>/toggle', methods=['POST'])
@login_required
def api_key_toggle(key_id):
    if current_user.role.value != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('admin.dashboard'))
    
    api_key = ApiKey.query.get_or_404(key_id)
    api_key.is_active = not api_key.is_active
    db.session.commit()
    
    status = 'enabled' if api_key.is_active else 'disabled'
    flash(f'API key "{api_key.name}" {status}.', 'info')
    return redirect(url_for('admin.api_keys'))

@bp.route('/api-keys/<key_id>/delete', methods=['POST'])
@login_required
def api_key_delete(key_id):
    if current_user.role.value != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('admin.dashboard'))
    
    api_key = ApiKey.query.get_or_404(key_id)
    name = api_key.name
    db.session.delete(api_key)
    db.session.commit()
    
    flash(f'API key "{name}" deleted.', 'success')
    return redirect(url_for('admin.api_keys'))

@bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'profile':
            display_name = request.form.get('display_name', '').strip()
            email = request.form.get('email', '').strip().lower()
            bio = request.form.get('bio', '').strip()
            
            errors = []
            
            if email and email != current_user.email:
                existing = User.query.filter_by(email=email).first()
                if existing:
                    errors.append('Email already in use.')
            
            if errors:
                for error in errors:
                    flash(error, 'error')
                return redirect(url_for('admin.settings'))
            
            current_user.display_name = display_name or None
            current_user.bio = bio or None
            if email:
                current_user.email = email
            
            db.session.commit()
            flash('Profile updated.', 'success')
            
        elif action == 'password':
            current_password = request.form.get('current_password', '')
            new_password = request.form.get('new_password', '')
            confirm_password = request.form.get('confirm_password', '')
            
            errors = []
            
            if not current_user.check_password(current_password):
                errors.append('Current password is incorrect.')
            if len(new_password) < 8:
                errors.append('New password must be at least 8 characters.')
            if new_password != confirm_password:
                errors.append('New passwords do not match.')
            
            if errors:
                for error in errors:
                    flash(error, 'error')
                return redirect(url_for('admin.settings'))
            
            current_user.set_password(new_password)
            db.session.commit()
            flash('Password changed.', 'success')
        
        elif action == 'avatar':
            if 'avatar_file' not in request.files or not request.files['avatar_file'].filename:
                flash('Please select an image to upload.', 'error')
                return redirect(url_for('admin.settings'))
            
            try:
                file = request.files['avatar_file']
                result = S3Service.upload_file(
                    file,
                    folder='avatars',
                    allowed_extensions={'jpg', 'jpeg', 'png', 'gif', 'webp'}
                )
                
                if current_user.avatar_url:
                    old_key = extract_s3_key(current_user.avatar_url)
                    if old_key and 'avatars/' in old_key:
                        try:
                            S3Service.delete_file(old_key)
                        except:
                            pass
                
                current_user.avatar_url = result['url']
                db.session.commit()
                flash('Avatar uploaded successfully.', 'success')
                
            except ValueError as e:
                flash(str(e), 'error')
            except Exception as e:
                flash(f'Upload failed. Please try again.', 'error')
            
        return redirect(url_for('admin.settings'))
    
    return render_template('admin/settings.html', user=current_user)

def extract_s3_key(url):
    public_url = current_app.config.get('S3_PUBLIC_URL', '')
    if public_url and public_url in url:
        return url.split(public_url)[-1].lstrip('/')

    bucket = current_app.config['S3_BUCKET_NAME']
    if bucket in url:
        parts = url.split(f'{bucket}/')
        return parts[-1] if len(parts) > 1 else None
    return None