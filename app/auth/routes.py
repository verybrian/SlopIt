from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.auth import bp
from app.models.user import User
from datetime import datetime, timedelta, timezone
from app.utils import generate_invite_token, send_reset_email
from app import db

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user is None or not user.check_password(password):
            flash('Invalid username or password', 'error')
            return redirect(url_for('auth.login'))
        
        login_user(user)
        next_page = request.args.get('next')
        flash('Welcome back!', 'success')
        return redirect(next_page or url_for('admin.dashboard'))
    
    return render_template('auth/login.html')

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))

@bp.route('/accept-invite/<token>', methods=['GET', 'POST'])
def accept_invite(token):
    user = User.query.filter_by(invite_token=token, is_active=False).first()
    
    if not user:
        flash('Invalid or expired invitation link.', 'error')
        return redirect(url_for('main.index'))
    
    if user.invite_expires_at and user.invite_expires_at < datetime.utcnow():
        flash('This invitation has expired.', 'error')
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        errors = []
        if len(username) < 3:
            errors.append('Username must be at least 3 characters.')
        if User.query.filter_by(username=username).first():
            errors.append('Username already taken.')
        if password != confirm_password:
            errors.append('Passwords do not match.')
        if len(password) < 8:
            errors.append('Password must be at least 8 characters.')
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('auth/accept_invite.html')
        
        user.username = username
        user.set_password(password)
        user.is_active = True
        user.invite_token = None
        user.invite_expires_at = None
        
        db.session.commit()
        
        login_user(user)
        flash('Account created! Welcome aboard.', 'success')
        return redirect(url_for('admin.dashboard'))
    
    return render_template('auth/accept_invite.html')


@bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        user = User.query.filter_by(email=email, is_active=True, is_deleted=False).first()
        
        if user:
            token = generate_invite_token(email)
            user.reset_token = token
            user.reset_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
            db.session.commit()
            send_reset_email(email, token, user.username)
        
        flash('If an account with that email exists, a reset link has been sent.', 'info')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/forgot_password.html')

@bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('admin.dashboard'))
    
    user = User.query.filter_by(reset_token=token, is_active=True, is_deleted=False).first()
    
    now_utc = datetime.now(timezone.utc)
    
    if not user:
        flash('Invalid or expired reset link. Please request a new one.', 'error')
        return redirect(url_for('auth.forgot_password'))
    
    if user.reset_expires_at:
        if user.reset_expires_at.tzinfo is None:
            from datetime import timezone as tz
            reset_expiry = user.reset_expires_at.replace(tzinfo=tz.utc)
        else:
            reset_expiry = user.reset_expires_at
        
        if reset_expiry < now_utc:
            flash('This reset link has expired. Please request a new one.', 'error')
            return redirect(url_for('auth.forgot_password'))
    
    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        errors = []
        if password != confirm_password:
            errors.append('Passwords do not match.')
        if len(password) < 8:
            errors.append('Password must be at least 8 characters.')
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('auth/reset_password.html')
        
        user.set_password(password)
        user.reset_token = None
        user.reset_expires_at = None
        db.session.commit()
        
        flash('Your password has been reset. Please log in.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/reset_password.html')