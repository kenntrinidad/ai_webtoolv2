from app.core.database import SessionLocal
from app.models import User
from app.core.config import get_settings
from app.services.password_service import verify_password
settings = get_settings()
with SessionLocal() as db:
    admin = db.query(User).filter(User.role == 'admin').first()
    print('admin_found', bool(admin))
    if admin:
        print('username', admin.username)
        print('email', admin.email)
        print('status', admin.status)
        print('must_change_password', admin.must_change_password)
        print('password_hash', admin.password_hash[:60])
        print('password_matches_env', verify_password(settings.initial_admin_password.get_secret_value(), admin.password_hash))
    print('configured_username', settings.initial_admin_username)
    print('configured_email', settings.initial_admin_email)
    print('configured_password', settings.initial_admin_password.get_secret_value() if settings.initial_admin_password else None)
