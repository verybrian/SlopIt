import secrets
from flask import current_app, render_template
from flask_mail import Message
from app import mail

def generate_invite_token(email):
    return secrets.token_urlsafe(32)

def send_invite_email(email, token):
    site_url = current_app.config.get('SITE_URL')
    invite_url = f"{site_url}/auth/accept-invite/{token}"
    
    html_body = render_template('email/invite.html', invite_url=invite_url)
    text_body = render_template('email/invite.txt', invite_url=invite_url)
    
    msg = Message(
        subject="You're invited to join SlopIt CMS",
        recipients=[email],
        body=text_body,
        html=html_body
    )
    
    mail.send(msg)