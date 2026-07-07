import getpass
from app import create_app, db
from app.models import User
from app.models.user import UserRole

app = create_app()

with app.app_context():
    print("\n=== Create Admin User ===\n")
    
    display_name = input("Display Name: ").strip()
    username = input("Username: ").strip()
    email = input("Email: ").strip()
    
    while True:
        password = getpass.getpass("Password: ")
        confirm = getpass.getpass("Confirm password: ")
        if password == confirm:
            break
        print("Passwords don't match. Try again.\n")
    
    existing = User.query.filter_by(username=username).first()
    if existing:
        print(f"\nUser '{username}' already exists. Delete first or choose another username.")
        exit()
    
    admin = User(
        display_name=display_name,
        username=username,
        email=email,
        role=UserRole.ADMIN
    )
    admin.set_password(password)
    
    db.session.add(admin)
    db.session.commit()
    
    verify = User.query.filter_by(username=username).first()
    if verify and verify.check_password(password):
        print(f"\n✓ Admin user '{username}' created and verified successfully!")
    else:
        print(f"\n✗ Something went wrong. Password verification failed.")