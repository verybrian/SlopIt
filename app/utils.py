import secrets
from datetime import datetime, timedelta

def generate_invite_token(email):
    """Generate a unique invitation token"""
    return secrets.token_urlsafe(32)

def send_invite_email(email, token):
    """Mock email function - replace with real email sending later"""
    accept_url = f"http://localhost:5000/auth/accept-invite/{token}"
    print(f"""
    ═══════════════════════════════════════
    📧 INVITATION EMAIL (Mock)
    To: {email}
    Subject: You're invited to join SlopIt CMS
    
    Click the link to set up your account:
    {accept_url}
    
    This link expires in 7 days.
    ═══════════════════════════════════════
    """)