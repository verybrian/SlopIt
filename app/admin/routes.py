from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.admin import bp
from app.models import Collection, Entry, User
from app.models.user import UserRole
from app.utils import generate_invite_token, send_invite_email
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