from datetime import date
from sqlalchemy.orm import Session
from .config import settings
from .database import SessionLocal, Base, engine, upgrade_legacy_schema
from .models import User, Department, Employee, LeaveType
from .security import hash_password

Base.metadata.create_all(bind=engine)
upgrade_legacy_schema()
db: Session = SessionLocal()
try:
    email = settings.hrms_admin_email.strip().lower()
    password = settings.hrms_admin_password
    if not email or "@" not in email:
        raise RuntimeError("Set HRMS_ADMIN_EMAIL to the administrator email before seeding")
    if len(password) < 12:
        raise RuntimeError("Set HRMS_ADMIN_PASSWORD to a unique password of at least 12 characters before seeding")
    admin_user = db.query(User).filter_by(email=email).first()
    if not admin_user:
        admin_user = User(email=email, password_hash=hash_password(password), role="admin")
        db.add(admin_user)
        db.flush()

    for name, allowance in [("Annual", 12), ("Sick", 6), ("Casual", 6)]:
        if not db.query(LeaveType).filter_by(name=name).first():
            db.add(LeaveType(name=name, annual_allowance=allowance))

    engineering = db.query(Department).filter_by(name="Engineering").first()
    if not engineering:
        engineering = Department(name="Engineering")
        db.add(engineering)
        db.flush()

    if not db.query(Employee).filter_by(user_id=admin_user.id).first():
        admin_employee = Employee(
            user_id=admin_user.id,
            employee_code="ADMIN-001",
            full_name="System Administrator",
            department_id=engineering.id,
            designation="Administrator",
            joining_date=date.today(),
            monthly_salary=0,
        )
        db.add(admin_employee)
        db.flush()

    db.commit()
    print(f"Seed complete. Admin email: {email}. Use the password you configured in HRMS_ADMIN_PASSWORD.")
finally:
    db.close()