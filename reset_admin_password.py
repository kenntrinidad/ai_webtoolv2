from app.core.database import SessionLocal
from app.models import User
from app.core.config import get_settings
from app.services.password_service import hash_password
settings = get_settings()
with SessionLocal() as db:
    admin = db.query(User).filter(User.role == 'admin').first()
    if admin is None:
        raise SystemExit('No admin user found')
    admin.password_hash = hash_password(settings.initial_admin_password.get_secret_value(), rounds=settings.password_hash_rounds)
    db.commit()
    print('updated admin password hash for', admin.username)
