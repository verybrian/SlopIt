import secrets
from flask import current_app, render_template
from flask_mail import Message
from app import mail

def generate_invite_token(email):
    return secrets.token_urlsafe(32)

def send_invite_email(email, token):
    site_url = current_app.config['SITE_URL']
    site_name = current_app.config['SITE_NAME']
    site_description = current_app.config['SITE_DESCRIPTION']
    invite_url = f"{site_url}/auth/accept-invite/{token}"
    
    html_body = render_template('email/invite.html', 
                                invite_url=invite_url,
                                site_name=site_name,
                                site_description=site_description)
    text_body = render_template('email/invite.txt', 
                                invite_url=invite_url,
                                site_name=site_name)
    
    msg = Message(
        subject=f"You're invited to join {site_name}",
        recipients=[email],
        body=text_body,
        html=html_body
    )
    
    mail.send(msg)