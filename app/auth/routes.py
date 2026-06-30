from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.auth import bp
from app.models.user import User
from datetime import datetime
from app import db

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
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
        return redirect(next_page or url_for('main.index'))
    
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