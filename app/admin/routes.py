import os
from flask import render_template, redirect, url_for, flash, request, current_app, jsonify
from flask_login import login_required, current_user
from app.admin import bp
from app.models import Collection, CollectionKind, Entry, User
from app.models.user import UserRole
from app.models.api_key import ApiKey
from app.models.media import Media
from app.models.field import Field, FieldType
from app.utils import generate_invite_token, send_invite_email
from app.services.s3 import S3Service
from app.services.media_service import upload_media, delete_media
from app import db
from datetime import datetime, timedelta, timezone


@bp.route('/')
@login_required
def dashboard():
    is_admin = current_user.role.value == 'admin'
    collections = Collection.query.order_by(Collection.label).all()
    stats = {
        'media_total': Media.query.count(),
        'users_total': User.query.filter_by(is_deleted=False).count() if is_admin else 0,
    }
    activity = generate_activity_feed() if is_admin else []
    return render_template('admin/dashboard.html', stats=stats, collections=collections,  activity=activity, is_admin=is_admin)


def generate_activity_feed():
    activities = []
    recent_entries = Entry.query.order_by(Entry.updated_at.desc()).limit(8).all()

    for entry in recent_entries:
        collection = Collection.query.get(entry.collection_id)
        entry_data = entry.to_dict()
        
        title = (entry_data.get('title') or 
                 entry_data.get('heading') or 
                 entry_data.get('copyright') or 
                 collection.label)

        time_diff = (entry.updated_at - entry.created_at).total_seconds()
        
        if time_diff < 5:
            action = f'created'
            activity_type = 'create'
        else:
            action = f'updated'
            activity_type = 'edit'

        activities.append({
            'actor': title,
            'action': action,
            'type': activity_type,
            'timestamp': entry.updated_at,
            'collection': collection.label,
        })

    return activities


@bp.route('/users')
@login_required
def user_list():
    if current_user.role.value != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('admin.dashboard'))

    users = User.query.filter_by(is_deleted=False).order_by(User.created_at.desc()).all()
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

    user.is_deleted = True
    user.is_active = False
    user.deleted_at = datetime.now(timezone.utc)
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

    key = ApiKey.generate_key()

    api_key = ApiKey(
        name=name,
        key=key,
        created_by=current_user.id
    )

    db.session.add(api_key)
    db.session.commit()

    flash(f'API key created: {key}', 'success')
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
                media = upload_media(
                    file=file,
                    user_id=current_user.id,
                    folder='avatars',
                    alt_text=f"{current_user.display_name or current_user.username}'s avatar"
                )

                if current_user.avatar_url:
                    old_media = Media.query.filter_by(url=current_user.avatar_url).first()
                    if old_media:
                        delete_media(old_media.id)

                current_user.avatar_url = media.url
                db.session.commit()
                flash('Avatar uploaded successfully.', 'success')

            except ValueError as e:
                flash(str(e), 'error')
            except Exception as e:
                current_app.logger.error(f'Avatar upload failed: {str(e)}')
                flash('Upload failed. Please try again.', 'error')

        return redirect(url_for('admin.settings'))

    return render_template('admin/settings.html', user=current_user)


@bp.route('/media')
@login_required
def media_library():
    media_type = request.args.get('type', '')
    page = request.args.get('page', 1, type=int)

    query = Media.query.order_by(Media.created_at.desc())

    if media_type:
        query = query.filter_by(media_type=media_type)

    media_items = query.paginate(page=page, per_page=24)

    return render_template('admin/media.html', media_items=media_items, current_type=media_type)


@bp.route('/media/upload', methods=['POST'])
@login_required
def media_upload():
    if 'file' not in request.files or not request.files['file'].filename:
        flash('Please select a file.', 'error')
        return redirect(url_for('admin.media_library'))

    try:
        file = request.files['file']
        folder = request.form.get('folder', 'general')
        alt_text = request.form.get('alt_text', '').strip() or None

        media = upload_media(
            file=file,
            user_id=current_user.id,
            folder=folder,
            alt_text=alt_text
        )

        flash(f'File "{media.filename}" uploaded.', 'success')
    except ValueError as e:
        flash(str(e), 'error')
    except Exception as e:
        flash('Upload failed.', 'error')

    return redirect(url_for('admin.media_library'))


@bp.route('/media/<media_id>/delete', methods=['POST'])
@login_required
def media_delete(media_id):
    if delete_media(media_id):
        flash('Media deleted.', 'success')
    else:
        flash('Media not found.', 'error')
    return redirect(url_for('admin.media_library'))


@bp.route('/api/categories')
@login_required
def api_categories():
    cat_collection = Collection.query.filter_by(name='categories').first()
    if not cat_collection:
        return jsonify([])
    
    entries = Entry.query.filter_by(collection_id=cat_collection.id).order_by(Entry.updated_at.desc()).all()
    categories = []
    for entry in entries:
        categories.append({
            'value': entry.get_value('title') or '',
            'label': entry.get_value('title') or '',
            'slug': entry.get_value('slug') or '',
        })
    
    return jsonify(categories)


@bp.route('/collections', methods=['GET', 'POST'])
@login_required
def collections():
    if current_user.role.value != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('admin.dashboard'))

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'create':
            name = request.form.get('name', '').strip().lower().replace(' ', '_')
            label = request.form.get('label', '').strip()
            kind = request.form.get('kind', 'post')

            if not name or not label:
                flash('Name and label are required.', 'error')
                return redirect(url_for('admin.collections'))

            existing = Collection.query.filter_by(name=name).first()
            if existing:
                flash(f'Collection "{name}" already exists.', 'error')
                return redirect(url_for('admin.collections'))

            collection = Collection(
                name=name,
                label=label,
                kind=CollectionKind(kind)
            )
            db.session.add(collection)
            db.session.commit()

            flash(f'Collection "{label}" created.', 'success')
            return redirect(url_for('admin.collection_fields', collection_id=collection.id))

        elif action == 'delete':
            collection_id = request.form.get('collection_id')
            collection = Collection.query.get_or_404(collection_id)

            # Count entries for confirmation message
            entry_count = collection.entries.count()
            db.session.delete(collection)
            db.session.commit()

            flash(f'Collection "{collection.label}" and {entry_count} entries deleted.', 'success')
            return redirect(url_for('admin.collections'))

        elif action == 'edit':
            collection_id = request.form.get('collection_id')
            collection = Collection.query.get_or_404(collection_id)
            label = request.form.get('label', '').strip()
            description = request.form.get('description', '').strip()

            if label:
                collection.label = label
            if collection.kind == CollectionKind.LIST:
                collection.description = description or None

            db.session.commit()
            flash(f'Collection "{collection.label}" updated.', 'success')
            return redirect(url_for('admin.collections'))

    collections = Collection.query.order_by(Collection.label).all()
    return render_template('admin/collections.html', collections=collections)


@bp.route('/collections/<collection_id>')
@login_required
def collection_edit(collection_id):
    collection = Collection.query.get_or_404(collection_id)

    if collection.kind == CollectionKind.SECTION:
        entry = collection.entries.first()
        if entry:
            return redirect(url_for('admin.entry_edit', collection_id=collection.id, entry_id=entry.id))
        return redirect(url_for('admin.entry_edit', collection_id=collection.id))

    if collection.kind == CollectionKind.LIST:
        items = collection.entries.order_by(Entry.updated_at.desc()).all()
        return render_template('admin/collection_list_editor.html', collection=collection, items=items)

    entries = collection.entries.order_by(Entry.updated_at.desc()).all()

    title_field = collection.fields.filter(
        Field.field_type.in_([FieldType.TEXT, FieldType.RICH_TEXT])
    ).order_by(Field.order).first()

    return render_template('admin/collection_content.html', collection=collection, entries=entries, title_field=title_field)


@bp.route('/collections/<collection_id>/save', methods=['POST'])
@login_required
def collection_save(collection_id):
    collection = Collection.query.get_or_404(collection_id)

    if collection.kind != CollectionKind.LIST:
        flash('Not applicable for this collection.', 'error')
        return redirect(url_for('admin.collection_edit', collection_id=collection.id))

    label = request.form.get('label', '').strip()
    if label:
        collection.label = label
    collection.description = request.form.get('description', '').strip()

    db.session.commit()
    flash('Saved.', 'success')
    return redirect(url_for('admin.collection_edit', collection_id=collection.id))


@bp.route('/collections/<collection_id>/fields', methods=['GET', 'POST'])
@login_required
def collection_fields(collection_id):
    if current_user.role.value != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('admin.dashboard'))

    collection = Collection.query.get_or_404(collection_id)

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add_field':
            name = request.form.get('name', '').strip().lower().replace(' ', '_')
            label = request.form.get('label', '').strip()
            field_type = request.form.get('field_type', 'text')
            required = request.form.get('required') == 'on'
            options = None

            if field_type == 'select':
                options_text = request.form.get('options', '')
                options = [o.strip() for o in options_text.split(',') if o.strip()]

            if not name or not label:
                flash('Name and label are required.', 'error')
                return redirect(url_for('admin.collection_fields', collection_id=collection.id))

            existing = Field.query.filter_by(collection_id=collection.id, name=name).first()
            if existing:
                flash(f'Field "{name}" already exists.', 'error')
                return redirect(url_for('admin.collection_fields', collection_id=collection.id))

            max_order = db.session.query(db.func.max(Field.order)).filter_by(collection_id=collection.id).scalar() or 0

            field = Field(
                collection_id=collection.id,
                name=name,
                label=label,
                field_type=FieldType(field_type),
                required=required,
                options=options,
                order=max_order + 1
            )
            db.session.add(field)
            db.session.commit()

            flash(f'Field "{label}" added.', 'success')

        elif action == 'delete_field':
            field_id = request.form.get('field_id')
            field = Field.query.get_or_404(field_id)
            label = field.label
            db.session.delete(field)
            db.session.commit()
            flash(f'Field "{label}" deleted.', 'success')

        return redirect(url_for('admin.collection_fields', collection_id=collection.id))

    fields = collection.fields.order_by(Field.order).all()
    field_types = [ft.value for ft in FieldType]

    return render_template('admin/collection_fields.html', collection=collection, fields=fields, field_types=field_types)


@bp.route('/collections/<collection_id>/entries/new', methods=['GET', 'POST'])
@bp.route('/collections/<collection_id>/entries/<entry_id>', methods=['GET', 'POST'])
@login_required
def entry_edit(collection_id, entry_id=None):
    collection = Collection.query.get_or_404(collection_id)
    entry = None

    if entry_id:
        entry = Entry.query.get_or_404(entry_id)
        if entry.collection_id != collection.id:
            flash('Entry not found in this collection.', 'error')
            return redirect(url_for('admin.collection_edit', collection_id=collection.id))

    fields = collection.fields.order_by(Field.order).all()

    if request.method == 'POST':
        if not entry:
            entry = Entry(collection_id=collection.id, data={})
            db.session.add(entry)
            db.session.flush()

        slug_value = request.form.get('slug')
        if slug_value:
            entry.slug = slug_value

        data = dict(entry.data or {})

        for field in fields:
            if field.name == 'author':
                data['author'] = current_user.display_name or current_user.username
                continue

            if field.field_type.value == 'image':
                file_key = f'{field.name}_file'
                media_id_key = f'{field.name}_media_id'
                value = data.get(field.name)

                if file_key in request.files and request.files[file_key].filename:
                    try:
                        media = upload_media(
                            file=request.files[file_key],
                            user_id=current_user.id,
                            folder=collection.name,
                            alt_text=request.form.get(f'{field.name}_alt', '')
                        )
                        value = media.url
                    except ValueError as e:
                        flash(f'Image upload failed: {str(e)}', 'error')
                        continue
                elif request.form.get(media_id_key):
                    media = Media.query.get(request.form.get(media_id_key))
                    if media:
                        value = media.url

                data[field.name] = value or ''
                continue

            data[field.name] = request.form.get(field.name, '')

        entry.data = data
        db.session.commit()
        flash('Entry saved.', 'success')

        if collection.kind == CollectionKind.LIST:
            return redirect(url_for('admin.collection_edit', collection_id=collection.id))
        return redirect(url_for('admin.entry_edit', collection_id=collection.id, entry_id=entry.id))

    cat_collection = Collection.query.filter_by(name='categories').first()

    return render_template('admin/entry_edit.html', collection=collection, entry=entry, fields=fields, cat_collection_id=cat_collection.id if cat_collection else None)


@bp.route('/collections/<collection_id>/entries/<entry_id>/delete', methods=['POST'])
@login_required
def entry_delete(collection_id, entry_id):
    collection = Collection.query.get_or_404(collection_id)
    entry = Entry.query.get_or_404(entry_id)

    if entry.collection_id != collection.id:
        flash('Entry not found.', 'error')
        return redirect(url_for('admin.collection_edit', collection_id=collection.id))

    db.session.delete(entry)
    db.session.commit()

    flash('Entry deleted.', 'success')
    return redirect(url_for('admin.collection_edit', collection_id=collection.id))