from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import csv, io, secrets
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Response, Query, Cookie
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import func, update
from sqlalchemy.exc import IntegrityError
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from .config import settings
from .notifications import EMAIL_TEMPLATES, send_notification
from .database import Base, engine, get_db, upgrade_legacy_schema
from .models import AuthSession, User, Department, Employee, EmployeeDocument, Attendance, Holiday, LeaveType, LeaveBalance, LeaveRequest, Payroll, PayrollAdjustment, NotificationLog, AuditLog, InAppNotification, NotificationPreference, Shift, ShiftAssignment, SalaryComponent, EmployeeSalaryComponent, EmployeeCompensation
from .salary_slip import generate_salary_slip_pdf
from .schemas import LoginIn, RegisterIn, EmployeeCreate, EmployeeUpdate, EmployeeSelfProfileUpdate, AttendanceCorrection, LeaveApply, LeaveDecision, LeaveTypeCreate, DepartmentCreate, HolidayCreate, PayrollGenerate, PayrollAdjustmentCreate, UserCreate, UserRoleUpdate
from .security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from .dependencies import current_user, current_employee, require_roles
from .phase_two import employee_compensation_values, record_compensation_revision, router as phase_two_router

app = FastAPI(title=settings.app_name, version="1.0.0")
cors_origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
if not cors_origins or "*" in cors_origins:
    raise ValueError("CORS_ORIGINS must contain explicit origins when cookie-based authentication is enabled")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
Base.metadata.create_all(bind=engine)  # Use Alembic migrations for production deployments.
upgrade_legacy_schema()
Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)

@app.get("/api/health")
def health(): return {"status":"ok", "service":"hrms-api"}

def working_days_between(start_date: date, end_date: date, holiday_dates: set[date]) -> int:
    total = 0
    current = start_date
    while current <= end_date:
        if current.weekday() < 5 and current not in holiday_dates:
            total += 1
        current += timedelta(days=1)
    return total


def applicable_holiday_dates(db: Session, start_date: date, end_date: date, department_id: int | None) -> set[date]:
    query = db.query(Holiday.holiday_date).filter(
        Holiday.holiday_date.between(start_date, end_date),
        Holiday.is_optional.is_(False),
    )
    if department_id is None:
        query = query.filter(Holiday.department_id.is_(None))
    else:
        query = query.filter(
            (Holiday.department_id.is_(None)) | (Holiday.department_id == department_id)
        )
    return {row[0] for row in query.all()}


def shift_for_employee(db: Session, employee: Employee, work_date: date):
    date_filter = (
        ShiftAssignment.effective_from <= work_date,
        (ShiftAssignment.effective_to.is_(None)) | (ShiftAssignment.effective_to >= work_date),
    )
    assignment = db.query(ShiftAssignment, Shift).join(
        Shift, Shift.id == ShiftAssignment.shift_id
    ).filter(
        ShiftAssignment.employee_id == employee.id,
        *date_filter,
    ).order_by(ShiftAssignment.effective_from.desc()).first()
    if assignment:
        return assignment[1]
    if employee.department_id is not None:
        assignment = db.query(ShiftAssignment, Shift).join(
            Shift, Shift.id == ShiftAssignment.shift_id
        ).filter(
            ShiftAssignment.department_id == employee.department_id,
            *date_filter,
        ).order_by(ShiftAssignment.effective_from.desc()).first()
        if assignment:
            return assignment[1]
    return None


def attendance_shift_metrics(shift: Shift | None, check_in: datetime | None, check_out: datetime | None):
    if shift is None:
        return 0, 0, 0
    late_minutes = 0
    early_minutes = 0
    overtime_minutes = 0
    scheduled_end = None
    if check_in is not None:
        scheduled_start = datetime.combine(check_in.date(), shift.start_time)
        late_minutes = max(
            0,
            int((check_in - scheduled_start).total_seconds() // 60) - shift.grace_minutes,
        )
        scheduled_end_date = check_in.date()
        if shift.end_time <= shift.start_time:
            scheduled_end_date += timedelta(days=1)
        scheduled_end = datetime.combine(scheduled_end_date, shift.end_time)
    if check_in is not None and check_out is not None and scheduled_end is not None:
        early_minutes = max(0, int((scheduled_end - check_out).total_seconds() // 60))
        overtime_minutes = max(0, int((check_out - scheduled_end).total_seconds() // 60))
    return late_minutes, early_minutes, overtime_minutes


def attendance_status_for_minutes(minutes: int, expected_minutes: int = 8 * 60) -> str:
    if minutes >= expected_minutes:
        return "present"
    if minutes >= expected_minutes / 2:
        return "half_day"
    return "absent"


def audit(db, actor, action, entity, entity_id=None, details=None):
    db.add(AuditLog(actor_user_id=actor.id if actor else None, action=action, entity_type=entity, entity_id=str(entity_id) if entity_id is not None else None, details=details))
def log_notification(db, recipient, event_type, context):
    send_notification(db, recipient, event_type, **context)
    user = db.query(User).filter(func.lower(User.email) == recipient.lower()).first()
    if user:
        preference = db.query(NotificationPreference).filter_by(
            user_id=user.id, event_type=event_type
        ).first()
        if preference is None or preference.enabled:
            subject_template, body_template = EMAIL_TEMPLATES[event_type]
            db.add(InAppNotification(
                user_id=user.id,
                event_type=event_type,
                title=subject_template.format_map(context),
                message=body_template.format_map(context).strip(),
            ))

def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)

@app.post("/api/auth/login")
def login(payload: LoginIn, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(func.lower(User.email) == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.password_hash) or not user.is_active:
        raise HTTPException(401, "Incorrect email or password")
    if user.role in {"admin", "hr"}:
        audit(db, user, "auth.login", "user", user.id)
    now = utc_now()
    session_id = secrets.token_urlsafe(32)
    token_id = secrets.token_urlsafe(32)
    expires_at = now + timedelta(minutes=settings.refresh_token_minutes)
    refresh_token = create_refresh_token(str(user.id), session_id, token_id)
    db.add(AuthSession(id=session_id, user_id=user.id, token_jti=token_id, expires_at=expires_at))
    db.commit()
    response.set_cookie(
        key="hrms_refresh_token",
        value=refresh_token,
        max_age=settings.refresh_token_minutes * 60,
        httponly=True,
        secure=settings.refresh_cookie_secure,
        samesite=settings.refresh_cookie_samesite,
        path="/api/auth",
    )
    return {
        "access_token": create_access_token(str(user.id), user.role, session_id),
        "token_type": "bearer",
        "role": user.role,
        "user_id": user.id,
    }

@app.post("/api/auth/register", status_code=201)
def register(payload: RegisterIn, response: Response, db: Session = Depends(get_db)):
    email = str(payload.email).lower().strip()
    if db.query(User).filter(func.lower(User.email) == email).first():
        raise HTTPException(409, "An account with this email already exists")

    user = User(email=email, password_hash=hash_password(payload.password), role="employee")
    db.add(user)
    db.flush()
    employee = Employee(
        user_id=user.id,
        employee_code=f"VINO-SELF-{user.id}-{secrets.token_hex(3).upper()}",
        full_name=payload.full_name,
        designation="Employee",
        joining_date=date.today(),
        monthly_salary=Decimal("0.00"),
    )
    db.add(employee)

    now = utc_now()
    session_id = secrets.token_urlsafe(32)
    token_id = secrets.token_urlsafe(32)
    expires_at = now + timedelta(minutes=settings.refresh_token_minutes)
    db.add(AuthSession(id=session_id, user_id=user.id, token_jti=token_id, expires_at=expires_at))
    audit(db, user, "auth.registered", "user", user.id, "Public self-registration; employee role assigned")
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "An account with this email already exists")

    response.set_cookie(
        key="hrms_refresh_token",
        value=create_refresh_token(str(user.id), session_id, token_id),
        max_age=settings.refresh_token_minutes * 60,
        httponly=True,
        secure=settings.refresh_cookie_secure,
        samesite=settings.refresh_cookie_samesite,
        path="/api/auth",
    )
    return {
        "access_token": create_access_token(str(user.id), user.role, session_id),
        "token_type": "bearer",
        "role": user.role,
        "user_id": user.id,
    }

@app.post("/api/auth/refresh")
def refresh_access_token(response: Response, refresh_token: str | None = Cookie(default=None, alias="hrms_refresh_token"), db: Session = Depends(get_db)):
    token_payload = decode_token(refresh_token) if refresh_token else None
    if not token_payload or token_payload.get("token_type") != "refresh":
        raise HTTPException(401, "Invalid or expired refresh token", headers={"WWW-Authenticate": "Bearer"})
    try:
        user_id = int(token_payload["sub"])
    except (TypeError, ValueError):
        raise HTTPException(401, "Invalid refresh token", headers={"WWW-Authenticate": "Bearer"})
    session_id = token_payload.get("sid")
    token_id = token_payload.get("jti")
    if not isinstance(session_id, str) or not isinstance(token_id, str):
        raise HTTPException(401, "Invalid refresh token", headers={"WWW-Authenticate": "Bearer"})
    user = db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
    if not user:
        raise HTTPException(401, "User is inactive or does not exist", headers={"WWW-Authenticate": "Bearer"})
    now = utc_now()
    session_expires_at = now + timedelta(minutes=settings.refresh_token_minutes)
    next_token_id = secrets.token_urlsafe(32)
    next_refresh_token = create_refresh_token(str(user.id), session_id, next_token_id)
    rotated = db.execute(
        update(AuthSession)
        .where(
            AuthSession.id == session_id,
            AuthSession.user_id == user.id,
            AuthSession.token_jti == token_id,
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > now,
        )
        .values(token_jti=next_token_id, expires_at=session_expires_at)
    )
    if rotated.rowcount != 1:
        db.rollback()
        raise HTTPException(401, "Invalid or expired refresh token", headers={"WWW-Authenticate": "Bearer"})
    db.commit()
    response.set_cookie(
        key="hrms_refresh_token",
        value=next_refresh_token,
        max_age=settings.refresh_token_minutes * 60,
        httponly=True,
        secure=settings.refresh_cookie_secure,
        samesite=settings.refresh_cookie_samesite,
        path="/api/auth",
    )
    return {
        "access_token": create_access_token(str(user.id), user.role, session_id),
        "token_type": "bearer",
        "role": user.role,
        "user_id": user.id,
    }

@app.post("/api/auth/logout")
def logout(
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias="hrms_refresh_token"),
    db: Session = Depends(get_db),
):
    token_payload = decode_token(refresh_token) if refresh_token else None
    if token_payload and token_payload.get("token_type") == "refresh":
        session_id = token_payload.get("sid")
        token_id = token_payload.get("jti")
        if isinstance(session_id, str) and isinstance(token_id, str):
            db.execute(
                update(AuthSession)
                .where(
                    AuthSession.id == session_id,
                    AuthSession.token_jti == token_id,
                    AuthSession.revoked_at.is_(None),
                )
                .values(revoked_at=utc_now())
            )
            db.commit()
    response.delete_cookie(
        key="hrms_refresh_token",
        httponly=True,
        secure=settings.refresh_cookie_secure,
        samesite=settings.refresh_cookie_samesite,
        path="/api/auth",
    )
    return {"message": "Signed out"}

@app.get("/api/auth/me")
def me(user: User = Depends(current_user)):
    return {"id":user.id,"email":user.email,"role":user.role}

@app.post("/api/admin/users", status_code=201)
def create_user(payload: UserCreate, db: Session = Depends(get_db), actor: User = Depends(require_roles("admin"))):
    email = str(payload.email).lower().strip()
    password = payload.password
    role = payload.role
    if db.query(User).filter(func.lower(User.email) == email).first(): raise HTTPException(409, "Email already exists")
    user = User(email=email, password_hash=hash_password(password), role=role)
    db.add(user); db.flush(); audit(db, actor, "user.created", "user", user.id, f"role={role}"); db.commit()
    return {"id":user.id,"email":user.email,"role":user.role}

@app.get("/api/admin/users")
def admin_users(db: Session = Depends(get_db), actor: User = Depends(require_roles("admin"))):
    rows = db.query(User, Employee).outerjoin(Employee, Employee.user_id == User.id).order_by(User.email).all()
    return [
        {
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
            "employee_name": employee.full_name if employee else None,
        }
        for user, employee in rows
    ]

@app.patch("/api/admin/users/{user_id}/role")
def update_user_role(user_id: int, payload: UserRoleUpdate, db: Session = Depends(get_db), actor: User = Depends(require_roles("admin"))):
    target = db.query(User).filter_by(id=user_id).with_for_update().first()
    if not target:
        raise HTTPException(404, "User not found")
    if target.id == actor.id:
        raise HTTPException(409, "You cannot change your own role")
    if target.role == "admin" and payload.role != "admin" and target.is_active:
        active_admins = db.query(User).filter(User.role == "admin", User.is_active.is_(True)).count()
        if active_admins <= 1:
            raise HTTPException(409, "The last active administrator cannot be demoted")
    previous_role = target.role
    target.role = payload.role
    audit(db, actor, "user.role_changed", "user", target.id, f"from={previous_role}; to={payload.role}")
    db.commit()
    return {"id": target.id, "email": target.email, "role": target.role, "is_active": target.is_active}

@app.get("/api/admin/roles")
def role_permissions(actor: User = Depends(require_roles("admin"))):
    return {
        "roles": [
            {"role": "admin", "permissions": ["manage_users", "manage_employees", "correct_attendance", "review_leave", "generate_payroll", "adjust_payroll", "download_all_salary_slips", "view_reports"]},
            {"role": "hr", "permissions": ["manage_employees", "view_attendance", "review_leave", "generate_payroll", "download_all_salary_slips", "view_reports"]},
            {"role": "employee", "permissions": ["create_employee", "view_own_profile", "manage_own_attendance", "apply_for_leave", "view_own_payroll", "download_own_salary_slips"]},
        ]
    }

@app.post("/api/employees", status_code=201)
def create_employee(payload: EmployeeCreate, db: Session = Depends(get_db), actor: User = Depends(current_user)):
    email = payload.email.lower()
    if db.query(User).filter_by(email=email).first(): raise HTTPException(409, "Email already exists")
    if db.query(Employee).filter_by(employee_code=payload.employee_code).first(): raise HTTPException(409, "Employee code already exists")
    if payload.department_id is not None and not db.query(Department).filter_by(id=payload.department_id).first():
        raise HTTPException(422, "Department not found")
    try:
        user = User(email=email, password_hash=hash_password(payload.temporary_password), role="employee")
        db.add(user); db.flush()
        salary_components = (
            payload.basic_salary,
            payload.hra,
            payload.special_allowance,
        )
        if all(component is None for component in salary_components):
            basic_salary, hra, special_allowance = payload.monthly_salary, Decimal("0"), Decimal("0")
        else:
            basic_salary, hra, special_allowance = (
                component if component is not None else Decimal("0")
                for component in salary_components
            )
            if basic_salary + hra + special_allowance != payload.monthly_salary:
                raise HTTPException(422, "Monthly salary must equal basic salary plus HRA and special allowance")
        employee = Employee(
            user_id=user.id,
            employee_code=payload.employee_code,
            full_name=payload.full_name,
            department_id=payload.department_id,
            designation=payload.designation,
            joining_date=payload.joining_date,
            monthly_salary=payload.monthly_salary,
            basic_salary=basic_salary,
            hra=hra,
            special_allowance=special_allowance,
            pf_percentage=payload.pf_percentage,
            professional_tax=payload.professional_tax,
            tds=payload.tds,
            phone=payload.phone,
            date_of_birth=payload.date_of_birth,
            address=payload.address,
            emergency_contact_name=payload.emergency_contact_name,
            emergency_contact_relationship=payload.emergency_contact_relationship,
            emergency_contact_phone=payload.emergency_contact_phone,
        )
        db.add(employee)
        db.flush()
        record_compensation_revision(
            db, employee, actor, employee.joining_date,
            employee_compensation_values(employee),
        )
        seed_employee_leave_balances(db, employee.id)
        audit(db, actor, "employee.created", "employee", employee.id)
        log_notification(db, email, "employee_onboarding", {"full_name": employee.full_name})
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Employee email or code already exists")
    db.refresh(employee)
    return employee_dict(employee, user)

def employee_dict(e, user=None):
    return {
        "id":e.id,"user_id":e.user_id,"email":user.email if user else None,
        "role":user.role if user else "employee",
        "employee_code":e.employee_code,"full_name":e.full_name,"department_id":e.department_id,
        "department_name":e.department.name if e.department else None,"designation":e.designation,
        "joining_date":e.joining_date,"monthly_salary":str(e.monthly_salary),
        "basic_salary":str(e.basic_salary),"hra":str(e.hra),
        "special_allowance":str(e.special_allowance),"pf_percentage":str(e.pf_percentage),
        "professional_tax":str(e.professional_tax),"tds":str(e.tds),
        "phone":e.phone,"date_of_birth":e.date_of_birth,"address":e.address,
        "emergency_contact_name":e.emergency_contact_name,
        "emergency_contact_relationship":e.emergency_contact_relationship,
        "emergency_contact_phone":e.emergency_contact_phone,
        "is_active":e.is_active,
    }

def seed_employee_leave_balances(db: Session, employee_id: int, year: int | None = None):
    year = year or date.today().year
    for leave_type in db.query(LeaveType).all():
        balance = db.query(LeaveBalance).filter_by(employee_id=employee_id, leave_type_id=leave_type.id, year=year).first()
        if balance is not None:
            continue
        db.add(LeaveBalance(employee_id=employee_id, leave_type_id=leave_type.id, year=year, remaining_days=Decimal(leave_type.annual_allowance)))
    db.flush()


def get_or_create_leave_balance(db: Session, employee_id: int, leave_type_id: int, year: int | None = None):
    year = year or date.today().year
    balance = db.query(LeaveBalance).filter_by(employee_id=employee_id, leave_type_id=leave_type_id, year=year).first()
    if balance is not None:
        return balance
    leave_type = db.query(LeaveType).filter_by(id=leave_type_id).first()
    balance = LeaveBalance(employee_id=employee_id, leave_type_id=leave_type_id, year=year, remaining_days=Decimal(leave_type.annual_allowance) if leave_type else Decimal("0"))
    db.add(balance)
    db.flush()
    return balance

@app.get("/api/employees")
def list_employees(department_id: int | None = None, include_inactive: bool = False, db: Session = Depends(get_db), actor: User = Depends(require_roles("admin","hr"))):
    q = db.query(Employee).join(User, User.id == Employee.user_id)
    if department_id: q = q.filter(Employee.department_id == department_id)
    if not include_inactive: q = q.filter(Employee.is_active.is_(True), User.is_active.is_(True))
    return [employee_dict(e, e.user) for e in q.order_by(Employee.id.desc()).all()]

@app.get("/api/employees/directory")
def employee_directory(db: Session = Depends(get_db), actor: User = Depends(current_user)):
    employees = (
        db.query(Employee)
        .join(User, User.id == Employee.user_id)
        .filter(Employee.is_active.is_(True), User.is_active.is_(True))
        .order_by(Employee.full_name)
        .all()
    )
    return [
        {
            "id": employee.id,
            "employee_code": employee.employee_code,
            "full_name": employee.full_name,
            "department_name": employee.department.name if employee.department else None,
            "designation": employee.designation,
            "role": employee.user.role,
            "is_active": employee.is_active,
            "is_self": employee.user_id == actor.id,
        }
        for employee in employees
    ]

@app.get("/api/departments")
def list_departments(db: Session = Depends(get_db), actor: User = Depends(current_user)):
    return [{"id": department.id, "name": department.name} for department in db.query(Department).order_by(Department.name).all()]

@app.post("/api/departments", status_code=201)
def create_department(payload: DepartmentCreate, db: Session = Depends(get_db), actor: User = Depends(require_roles("admin", "hr"))):
    existing = db.query(Department).filter(func.lower(Department.name) == payload.name.lower()).first()
    if existing:
        raise HTTPException(409, "A department with this name already exists")
    department = Department(name=payload.name)
    db.add(department)
    try:
        db.flush()
        audit(db, actor, "department.created", "department", department.id, f"name={department.name}")
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "A department with this name already exists") from exc
    return {"id": department.id, "name": department.name}

@app.get("/api/holidays")
def list_holidays(year: int | None = Query(default=None, ge=2000, le=2100), db: Session = Depends(get_db), actor: User = Depends(require_roles("admin", "hr"))):
    query = db.query(Holiday)
    if year is not None:
        query = query.filter(Holiday.holiday_date >= date(year, 1, 1), Holiday.holiday_date < date(year + 1, 1, 1))
    return [
        {"id": holiday.id, "holiday_date": holiday.holiday_date, "name": holiday.name,
         "scope": holiday.scope, "department_id": holiday.department_id,
         "is_optional": holiday.is_optional}
        for holiday in query.order_by(Holiday.holiday_date, Holiday.name).all()
    ]

@app.post("/api/holidays", status_code=201)
def create_holiday(payload: HolidayCreate, db: Session = Depends(get_db), actor: User = Depends(require_roles("admin"))):
    if payload.department_id is not None and not db.query(Department).filter_by(id=payload.department_id).first():
        raise HTTPException(422, "Department not found")
    duplicate = db.query(Holiday).filter_by(
        holiday_date=payload.holiday_date,
        scope=payload.scope,
        department_id=payload.department_id,
    ).first()
    if duplicate:
        raise HTTPException(409, "This holiday is already registered")
    holiday = Holiday(
        holiday_date=payload.holiday_date,
        name=payload.name,
        scope=payload.scope,
        department_id=payload.department_id,
        is_optional=payload.is_optional,
    )
    try:
        db.add(holiday)
        db.flush()
        audit(db, actor, "holiday.created", "holiday", holiday.id, f"date={holiday.holiday_date}; name={holiday.name}")
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "A holiday is already registered for this date")
    db.refresh(holiday)
    return {"id": holiday.id, "holiday_date": holiday.holiday_date, "name": holiday.name,
            "scope": holiday.scope, "department_id": holiday.department_id,
            "is_optional": holiday.is_optional}

@app.delete("/api/holidays/{holiday_id}", status_code=204)
def delete_holiday(holiday_id: int, db: Session = Depends(get_db), actor: User = Depends(require_roles("admin"))):
    holiday = db.query(Holiday).filter_by(id=holiday_id).first()
    if holiday is None:
        raise HTTPException(404, "Holiday not found")
    audit(db, actor, "holiday.deleted", "holiday", holiday.id, f"date={holiday.holiday_date}; name={holiday.name}")
    db.delete(holiday)
    db.commit()
    return Response(status_code=204)

@app.get("/api/employees/me")
def my_profile(employee: Employee = Depends(current_employee), user: User = Depends(current_user)):
    return employee_dict(employee, user)

@app.patch("/api/employees/me/profile")
def update_my_profile(
    payload: EmployeeSelfProfileUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
    employee: Employee = Depends(current_employee),
):
    changes = payload.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(employee, key, value)
    audit(db, actor, "employee.self_profile_updated", "employee", employee.id)
    db.commit()
    db.refresh(employee)
    return employee_dict(employee, actor)

@app.get("/api/employees/{employee_id}")
def get_employee(employee_id: int, db: Session = Depends(get_db), actor: User = Depends(current_user)):
    e = db.query(Employee).filter_by(id=employee_id).first()
    if not e: raise HTTPException(404, "Employee not found")
    if actor.role == "employee" and e.user_id != actor.id: raise HTTPException(403, "You can only view your own profile")
    return employee_dict(e, e.user)

@app.patch("/api/employees/{employee_id}")
def update_employee(employee_id: int, payload: EmployeeUpdate, db: Session = Depends(get_db), actor: User = Depends(require_roles("admin","hr"))):
    e = db.query(Employee).filter_by(id=employee_id).first()
    if not e: raise HTTPException(404, "Employee not found")
    changes = payload.model_dump(exclude_unset=True)
    previous_compensation = employee_compensation_values(e)
    salary_component_names = ("basic_salary", "hra", "special_allowance")
    components_changed = any(name in changes for name in salary_component_names)
    if components_changed:
        component_values = {
            name: Decimal(changes.get(name, getattr(e, name)))
            for name in salary_component_names
        }
        gross_salary = sum(component_values.values(), Decimal("0"))
        if "monthly_salary" in changes and Decimal(changes["monthly_salary"]) != gross_salary:
            raise HTTPException(422, "Monthly salary must equal basic salary plus HRA and special allowance")
        changes.update(component_values)
        changes["monthly_salary"] = gross_salary
    elif "monthly_salary" in changes:
        changes["basic_salary"] = changes["monthly_salary"]
        changes["hra"] = Decimal("0")
        changes["special_allowance"] = Decimal("0")
    if "email" in changes:
        email = str(changes.pop("email")).lower()
        existing_user = db.query(User).filter(func.lower(User.email) == email, User.id != e.user_id).first()
        if existing_user: raise HTTPException(409, "Email already exists")
        e.user.email = email
    if "employee_code" in changes:
        existing_code = db.query(Employee).filter(Employee.employee_code == changes["employee_code"], Employee.id != e.id).first()
        if existing_code: raise HTTPException(409, "Employee code already exists")
    if "is_active" in changes and changes["is_active"] != e.is_active and e.user.role != "employee":
        raise HTTPException(409, "Only employee accounts can be deactivated or reactivated here")
    if changes.get("department_id") is not None and not db.query(Department).filter_by(id=changes["department_id"]).first():
        raise HTTPException(422, "Department not found")
    was_active = e.is_active
    for key, value in changes.items():
        setattr(e, key, value)
    if set(changes).intersection({
        "monthly_salary", "basic_salary", "hra", "special_allowance",
        "pf_percentage", "professional_tax", "tds",
    }):
        record_compensation_revision(
            db, e, actor, date.today(), employee_compensation_values(e),
            previous_compensation,
        )
    if "is_active" in changes:
        e.user.is_active = e.is_active
        if was_active and not e.is_active:
            db.execute(
                update(AuthSession)
                .where(AuthSession.user_id == e.user_id, AuthSession.revoked_at.is_(None))
                .values(revoked_at=utc_now())
            )
    audit(db, actor, "employee.updated", "employee", e.id)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Employee email or code already exists")
    db.refresh(e)
    return employee_dict(e, e.user)

@app.delete("/api/employees/{employee_id}", status_code=204)
def deactivate_employee(employee_id: int, db: Session = Depends(get_db), actor: User = Depends(require_roles("admin", "hr"))):
    employee = db.query(Employee).filter_by(id=employee_id).first()
    if not employee:
        raise HTTPException(404, "Employee not found")
    if employee.is_active:
        employee.is_active = False
        employee.user.is_active = False
        db.execute(
            update(AuthSession)
            .where(AuthSession.user_id == employee.user_id, AuthSession.revoked_at.is_(None))
            .values(revoked_at=utc_now())
        )
        audit(db, actor, "employee.deactivated", "employee", employee.id)
        db.commit()
    return Response(status_code=204)

@app.post("/api/employees/{employee_id}/documents", status_code=201)
async def upload_document(employee_id: int, file: UploadFile = File(...), db: Session = Depends(get_db), actor: User = Depends(current_user)):
    e = db.query(Employee).filter_by(id=employee_id).first()
    if not e: raise HTTPException(404, "Employee not found")
    if e.user.role != "employee":
        raise HTTPException(409, "Documents can only be uploaded for employee accounts")
    if actor.role == "employee" and e.user_id != actor.id:
        raise HTTPException(403, "You can only upload documents to your own profile")
    if actor.role not in {"admin", "hr", "employee"}:
        raise HTTPException(403, "You are not allowed to upload employee documents")
    allowed = {"application/pdf", "image/jpeg", "image/png"}
    signatures = {
        "application/pdf": (b"%PDF-",),
        "image/jpeg": (b"\xff\xd8\xff",),
        "image/png": (b"\x89PNG\r\n\x1a\n",),
    }
    if file.content_type not in allowed: raise HTTPException(415, "Only PDF, JPEG, and PNG files are allowed")
    data = await file.read(5 * 1024 * 1024 + 1)
    if len(data) > 5 * 1024 * 1024: raise HTTPException(413, "Maximum file size is 5 MB")
    if not any(data.startswith(signature) for signature in signatures[file.content_type]):
        raise HTTPException(415, "File contents do not match the declared file type")
    extensions = {"application/pdf": ".pdf", "image/jpeg": ".jpg", "image/png": ".png"}
    stored = secrets.token_hex(16) + extensions[file.content_type]
    Path(settings.upload_dir, stored).write_bytes(data)
    doc = EmployeeDocument(employee_id=e.id, original_name=Path(file.filename or "document").name[:255], stored_name=stored, content_type=file.content_type)
    db.add(doc); db.flush(); audit(db, actor, "employee.document_uploaded", "employee_document", doc.id); db.commit()
    return {"id":doc.id,"original_name":doc.original_name,"uploaded_at":doc.uploaded_at}

@app.get("/api/employees/{employee_id}/documents")
def list_employee_documents(employee_id: int, db: Session = Depends(get_db), actor: User = Depends(current_user)):
    employee = db.query(Employee).filter_by(id=employee_id).first()
    if not employee:
        raise HTTPException(404, "Employee not found")
    if actor.role == "employee" and employee.user_id != actor.id:
        raise HTTPException(403, "You can only view your own documents")
    documents = db.query(EmployeeDocument).filter_by(employee_id=employee.id).order_by(EmployeeDocument.uploaded_at.desc()).all()
    audit(db, actor, "employee.documents_listed", "employee", employee.id)
    db.commit()
    return [
        {"id": document.id, "original_name": document.original_name, "content_type": document.content_type, "uploaded_at": document.uploaded_at}
        for document in documents
    ]

@app.get("/api/employees/{employee_id}/documents/{document_id}")
def download_employee_document(employee_id: int, document_id: int, db: Session = Depends(get_db), actor: User = Depends(current_user)):
    employee = db.query(Employee).filter_by(id=employee_id).first()
    if not employee:
        raise HTTPException(404, "Employee not found")
    if actor.role == "employee" and employee.user_id != actor.id:
        raise HTTPException(403, "You can only download your own documents")
    document = db.query(EmployeeDocument).filter_by(id=document_id, employee_id=employee.id).first()
    if not document:
        raise HTTPException(404, "Document not found")
    path = (Path(settings.upload_dir) / document.stored_name).resolve()
    if path.parent != Path(settings.upload_dir).resolve() or not path.is_file():
        raise HTTPException(404, "Document file not found")
    audit(db, actor, "employee.document_downloaded", "employee_document", document.id, f"employee_id={employee.id}")
    db.commit()
    return FileResponse(path, media_type=document.content_type, filename=document.original_name)

@app.post("/api/attendance/check-in")
def check_in(db: Session = Depends(get_db), employee: Employee = Depends(current_employee), user: User = Depends(current_user)):
    today = date.today(); row = db.query(Attendance).filter_by(employee_id=employee.id, work_date=today).first()
    if row and row.check_in: raise HTTPException(409, "Already checked in today")
    check_in_at = datetime.now(timezone.utc).replace(tzinfo=None)
    shift = shift_for_employee(db, employee, today)
    late_minutes, _, _ = attendance_shift_metrics(shift, check_in_at, None)
    if row is not None:
        changed = db.execute(
            update(Attendance)
            .where(Attendance.id == row.id, Attendance.check_in.is_(None))
            .values(check_in=check_in_at, status="present", shift_id=shift.id if shift else None,
                    late_minutes=late_minutes)
        )
        if changed.rowcount != 1:
            db.rollback()
            raise HTTPException(409, "Already checked in today")
    else:
        row = Attendance(employee_id=employee.id, work_date=today, check_in=check_in_at,
                         status="present", shift_id=shift.id if shift else None,
                         late_minutes=late_minutes)
        db.add(row)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, "Already checked in today")
    audit(db, user, "attendance.check_in", "attendance", row.id, f"work_date={today.isoformat()}")
    if late_minutes:
        log_notification(db, user.email, "attendance_alert", {
            "message": f"You checked in {late_minutes} minutes after your shift start.",
        })
    db.commit()
    db.refresh(row)
    return attendance_dict(row)

def attendance_dict(a, employee=None):
    result = {
        "id": a.id,
        "employee_id": a.employee_id,
        "work_date": a.work_date,
        "check_in": a.check_in.replace(tzinfo=timezone.utc).isoformat() if a.check_in else None,
        "check_out": a.check_out.replace(tzinfo=timezone.utc).isoformat() if a.check_out else None,
        "working_minutes": a.working_minutes,
        "status": a.status,
        "shift_id": a.shift_id,
        "shift_name": a.shift.name if a.shift else None,
        "late_minutes": a.late_minutes,
        "early_checkout_minutes": a.early_checkout_minutes,
        "overtime_minutes": a.overtime_minutes,
    }
    if employee is not None:
        result["employee_name"] = employee.full_name
        result["employee_code"] = employee.employee_code
    return result

@app.post("/api/attendance/check-out")
def check_out(db: Session = Depends(get_db), employee: Employee = Depends(current_employee), actor: User = Depends(current_user)):
    today = date.today()
    row = db.query(Attendance).filter_by(
        employee_id=employee.id, work_date=today
    ).first()
    if row is None:
        prior = db.query(Attendance).filter_by(
            employee_id=employee.id, work_date=today - timedelta(days=1)
        ).filter(Attendance.check_out.is_(None)).first()
        prior_shift = db.query(Shift).filter_by(id=prior.shift_id).first() if prior and prior.shift_id else None
        if prior_shift and prior_shift.end_time <= prior_shift.start_time:
            row = prior
    if not row or not row.check_in: raise HTTPException(409, "Check in before checking out")
    if row.check_out: raise HTTPException(409, "Already checked out today")
    checked_out_at = datetime.now(timezone.utc).replace(tzinfo=None)
    working_minutes = max(0, int((checked_out_at - row.check_in).total_seconds() // 60))
    shift = db.query(Shift).filter_by(id=row.shift_id).first() if row.shift_id else None
    status = attendance_status_for_minutes(
        working_minutes, shift.expected_minutes if shift else 8 * 60
    )
    _, early_minutes, overtime_minutes = attendance_shift_metrics(
        shift, row.check_in, checked_out_at
    )
    changed = db.execute(
        update(Attendance)
        .where(Attendance.id == row.id, Attendance.check_in.is_not(None), Attendance.check_out.is_(None))
        .values(check_out=checked_out_at, working_minutes=working_minutes, status=status,
                early_checkout_minutes=early_minutes, overtime_minutes=overtime_minutes)
    )
    if changed.rowcount != 1:
        db.rollback()
        raise HTTPException(409, "Already checked out today")
    audit(db, actor, "attendance.check_out", "attendance", row.id, f"work_date={row.work_date.isoformat()}; working_minutes={working_minutes}")
    if early_minutes or overtime_minutes:
        messages = []
        if early_minutes:
            messages.append(f"early checkout: {early_minutes} minutes")
        if overtime_minutes:
            messages.append(f"overtime: {overtime_minutes} minutes")
        log_notification(db, actor.email, "attendance_alert", {
            "message": "Attendance alert — " + "; ".join(messages) + ".",
        })
    db.commit()
    row = db.query(Attendance).filter_by(id=row.id).one()
    db.refresh(row)
    return attendance_dict(row)

@app.get("/api/attendance/me")
def my_attendance(month: int = Query(default=date.today().month, ge=1, le=12), year: int = Query(default=date.today().year, ge=2000, le=2100), db: Session = Depends(get_db), employee: Employee = Depends(current_employee)):
    month_start = date(year, month, 1)
    next_month = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    month_end = next_month - timedelta(days=1)
    elapsed_end = min(month_end, date.today())
    holidays = set()
    holiday_rows = []
    if elapsed_end >= month_start:
        holidays = applicable_holiday_dates(db, month_start, elapsed_end, employee.department_id)
    if month_end >= month_start:
        holiday_rows = db.query(Holiday).filter(
            Holiday.holiday_date >= month_start,
            Holiday.holiday_date <= month_end,
            (Holiday.department_id.is_(None)) | (Holiday.department_id == employee.department_id),
        ).order_by(Holiday.holiday_date).all()
    rows = db.query(Attendance).filter(Attendance.employee_id == employee.id, Attendance.work_date >= month_start, Attendance.work_date < next_month).order_by(Attendance.work_date.desc()).all()
    return {
        "records": [attendance_dict(a) for a in rows],
        "working_days": working_days_between(month_start, elapsed_end, holidays) if elapsed_end >= month_start else 0,
        "days_present": sum(1 if a.status == "present" else 0.5 if a.status == "half_day" else 0 for a in rows),
        "days_half_day": sum(1 for a in rows if a.status == "half_day"),
        "days_on_leave": sum(1 for a in rows if a.status == "on_leave"),
        "days_absent": sum(1 for a in rows if a.status == "absent"),
        "total_working_minutes": sum(a.working_minutes for a in rows),
        "holiday_count": len({holiday.holiday_date for holiday in holiday_rows}),
        "holidays": [{"date": row.holiday_date, "name": row.name} for row in holiday_rows],
    }

@app.get("/api/attendance")
def all_attendance(start_date: date, end_date: date, department_id: int | None = None, db: Session = Depends(get_db), actor: User = Depends(require_roles("admin","hr"))):
    if end_date < start_date:
        raise HTTPException(422, "end_date must be on or after start_date")
    q = db.query(Attendance, Employee).join(Employee, Employee.id == Attendance.employee_id).filter(Attendance.work_date.between(start_date,end_date))
    if department_id is not None: q = q.filter(Employee.department_id==department_id)
    return [attendance_dict(attendance, employee) for attendance, employee in q.order_by(Attendance.work_date.desc()).all()]

@app.patch("/api/attendance/{attendance_id}/correct")
def correct_attendance(attendance_id: int, payload: AttendanceCorrection, db: Session = Depends(get_db), actor: User = Depends(require_roles("admin"))):
    row = db.query(Attendance).filter_by(id=attendance_id).first()
    if not row: raise HTTPException(404,"Attendance not found")
    changes = payload.model_dump(exclude_unset=True)
    if "shift_id" in changes and changes["shift_id"] is not None:
        if db.query(Shift.id).filter_by(id=changes["shift_id"]).first() is None:
            raise HTTPException(404, "Shift not found")
    for key, value in changes.items():
        if key in {"check_in", "check_out"} and value is not None and value.tzinfo is not None:
            value = value.astimezone(timezone.utc).replace(tzinfo=None)
        setattr(row, key, value)
    if row.check_in and row.check_out and row.check_out < row.check_in:
        raise HTTPException(422, "check_out must be at or after check_in")
    if row.check_in and row.check_out: row.working_minutes=max(0,int((row.check_out-row.check_in).total_seconds()//60))
    else: row.working_minutes = 0
    shift = db.query(Shift).filter_by(id=row.shift_id).first() if row.shift_id else None
    if row.check_in and row.check_out and "status" not in changes:
        row.status = attendance_status_for_minutes(
            row.working_minutes, shift.expected_minutes if shift else 8 * 60
        )
    row.late_minutes, row.early_checkout_minutes, row.overtime_minutes = attendance_shift_metrics(
        shift, row.check_in, row.check_out
    )
    audit(db,actor,"attendance.corrected","attendance",row.id,payload.reason)
    db.commit(); db.refresh(row); return attendance_dict(row, db.query(Employee).filter_by(id=row.employee_id).first())

@app.post("/api/leave-types", status_code=201)
def create_leave_type(payload: LeaveTypeCreate, db: Session = Depends(get_db), actor: User = Depends(require_roles("admin","hr"))):
    existing = db.query(LeaveType).filter(func.lower(LeaveType.name) == payload.name.lower()).first()
    if existing: raise HTTPException(409,"Leave type exists")
    row=LeaveType(name=payload.name,annual_allowance=payload.annual_allowance); db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Leave type exists")
    db.refresh(row)
    audit(db, actor, "leave_type.created", "leave_type", row.id)
    db.commit()
    return {"id":row.id,"name":row.name,"annual_allowance":row.annual_allowance}

@app.get("/api/leave-types")
def list_leave_types(db: Session = Depends(get_db), actor: User = Depends(current_user)):
    return [{"id":x.id,"name":x.name,"annual_allowance":x.annual_allowance} for x in db.query(LeaveType).order_by(LeaveType.name).all()]

@app.post("/api/leaves", status_code=201)
def apply_leave(payload: LeaveApply, db: Session = Depends(get_db), employee: Employee = Depends(current_employee), user: User = Depends(current_user)):
    if payload.start_date < date.today(): raise HTTPException(422,"Leave must start today or in the future")
    leave_type = db.query(LeaveType).filter_by(id=payload.leave_type_id).first()
    if not leave_type: raise HTTPException(404,"Leave type not found")
    overlapping = db.query(LeaveRequest).filter(
        LeaveRequest.employee_id == employee.id,
        LeaveRequest.status.in_(("pending", "approved")),
        LeaveRequest.start_date <= payload.end_date,
        LeaveRequest.end_date >= payload.start_date,
    ).first()
    if overlapping:
        raise HTTPException(409, "This request overlaps an existing pending or approved leave")
    holiday_dates = applicable_holiday_dates(
        db, payload.start_date, payload.end_date, employee.department_id
    )
    days = Decimal(working_days_between(payload.start_date, payload.end_date, holiday_dates))
    if days == 0:
        raise HTTPException(422, "Leave dates must include at least one working day")
    row=LeaveRequest(employee_id=employee.id,leave_type_id=payload.leave_type_id,start_date=payload.start_date,end_date=payload.end_date,days=days,reason=payload.reason)
    hr_recipients = db.query(User.email).filter(User.role.in_(("admin", "hr")), User.is_active.is_(True)).all()
    for (recipient,) in hr_recipients:
        log_notification(db, recipient, "leave_application", {
            "employee_name": employee.full_name,
            "start_date": payload.start_date.isoformat(),
            "end_date": payload.end_date.isoformat(),
        })
    db.add(row)
    db.flush()
    audit(db, user, "leave.submitted", "leave_request", row.id, f"leave_type_id={leave_type.id}; start_date={payload.start_date}; end_date={payload.end_date}")
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "A leave request conflicts with an existing request")
    db.refresh(row)
    return leave_dict(row, leave_type, employee)

def leave_dict(l, leave_type=None, employee=None):
    return {
        "id": l.id,
        "employee_id": l.employee_id,
        "employee_name": employee.full_name if employee else None,
        "employee_code": employee.employee_code if employee else None,
        "leave_type_id": l.leave_type_id,
        "leave_type": leave_type.name if leave_type else None,
        "annual_allowance": leave_type.annual_allowance if leave_type else None,
        "start_date": l.start_date,
        "end_date": l.end_date,
        "days": str(l.days),
        "reason": l.reason,
        "status": l.status,
        "reviewer_id": l.reviewer_id,
        "reviewed_at": l.reviewed_at,
        "review_note": l.review_note,
    }

@app.get("/api/leaves/me")
def my_leaves(db: Session = Depends(get_db), employee: Employee = Depends(current_employee)):
    rows = db.query(LeaveRequest, LeaveType).join(LeaveType, LeaveType.id == LeaveRequest.leave_type_id).filter(
        LeaveRequest.employee_id == employee.id,
    ).order_by(LeaveRequest.start_date.desc(), LeaveRequest.id.desc()).all()
    return [leave_dict(leave, leave_type, employee) for leave, leave_type in rows]

@app.get("/api/leaves")
def all_leaves(status: str | None = None, db: Session = Depends(get_db), actor: User = Depends(require_roles("admin","hr"))):
    q=db.query(LeaveRequest, LeaveType, Employee).join(LeaveType, LeaveType.id == LeaveRequest.leave_type_id).join(Employee, Employee.id == LeaveRequest.employee_id)
    if status: q=q.filter(LeaveRequest.status == status)
    return [leave_dict(leave, leave_type, employee) for leave, leave_type, employee in q.order_by(LeaveRequest.start_date.desc(), LeaveRequest.id.desc()).all()]

@app.post("/api/leaves/{leave_id}/decision")
def decide_leave(leave_id: int, payload: LeaveDecision, db: Session = Depends(get_db), actor: User = Depends(require_roles("admin","hr"))):
    row=db.query(LeaveRequest).filter_by(id=leave_id).with_for_update().first()
    if not row: raise HTTPException(404,"Leave request not found")
    if row.status != "pending": raise HTTPException(409,"Request has already been reviewed")
    employee=db.query(Employee).filter_by(id=row.employee_id).first()
    leave_type=db.query(LeaveType).filter_by(id=row.leave_type_id).first()
    if not employee or not leave_type:
        raise HTTPException(409, "Leave request is missing its employee or leave type")
    changed = db.execute(
        update(LeaveRequest)
        .where(LeaveRequest.id == row.id, LeaveRequest.status == "pending")
        .values(status=payload.status, reviewer_id=actor.id, reviewed_at=utc_now())
    )
    if changed.rowcount != 1:
        db.rollback()
        raise HTTPException(409, "Request has already been reviewed")
    if payload.status == "approved":
        for year in range(row.start_date.year, row.end_date.year + 1):
            year_balance = get_or_create_leave_balance(db, row.employee_id, row.leave_type_id, year)
            year_start = date(year, 1, 1)
            year_end = date(year, 12, 31)
            period_start = max(row.start_date, year_start)
            period_end = min(row.end_date, year_end)
            holidays = applicable_holiday_dates(
                db, period_start, period_end, employee.department_id
            )
            charged_days = Decimal(working_days_between(period_start, period_end, holidays))
            year_balance.remaining_days = max(Decimal("0"), year_balance.remaining_days - charged_days)
    row.review_note = payload.note
    log_notification(db, employee.user.email, "leave_decision", {
        "status": payload.status,
        "leave_type": leave_type.name,
        "start_date": row.start_date.isoformat(),
        "end_date": row.end_date.isoformat(),
    })
    audit(db,actor,f"leave.{payload.status}","leave_request",row.id,payload.note)
    db.commit()
    db.refresh(row)
    return leave_dict(row, leave_type, employee)

@app.get("/api/leaves/balances/me")
def my_leave_balances(year: int = Query(default=date.today().year, ge=2000, le=2100), db: Session = Depends(get_db), employee: Employee = Depends(current_employee)):
    seed_employee_leave_balances(db, employee.id, year)
    rows=db.query(LeaveBalance,LeaveType).join(LeaveType,LeaveType.id==LeaveBalance.leave_type_id).filter(LeaveBalance.employee_id==employee.id,LeaveBalance.year==year).all()
    return [{"leave_type_id":t.id,"leave_type":t.name,"annual_allowance":t.annual_allowance,"year":b.year,"remaining_days":str(b.remaining_days)} for b,t in rows]

def payroll_day_totals(db: Session, employee_id: int, year: int, month: int) -> tuple[Decimal, Decimal]:
    month_start = date(year, month, 1)
    month_end = date(year + (month == 12), 1 if month == 12 else month + 1, 1) - timedelta(days=1)
    year_start = date(year, 1, 1)
    employee = db.query(Employee).filter_by(id=employee_id).first()
    holidays = applicable_holiday_dates(
        db, year_start, month_end, employee.department_id if employee else None
    )
    work_dates: set[date] = set()
    current = year_start
    while current <= month_end:
        if current.weekday() < 5 and current not in holidays:
            work_dates.add(current)
        current += timedelta(days=1)

    approved = (
        db.query(LeaveRequest, LeaveType)
        .join(LeaveType, LeaveType.id == LeaveRequest.leave_type_id)
        .filter(
            LeaveRequest.employee_id == employee_id,
            LeaveRequest.status == "approved",
            LeaveRequest.start_date <= month_end,
            LeaveRequest.end_date >= year_start,
        )
        .order_by(LeaveRequest.start_date, LeaveRequest.id)
        .all()
    )
    paid_leave_dates: set[date] = set()
    unpaid_leave_dates: set[date] = set()
    used_by_type: dict[int, int] = {}
    for leave, leave_type in approved:
        current = max(leave.start_date, year_start)
        end_date = min(leave.end_date, month_end)
        is_unpaid = leave_type.name.strip().lower() in {"loss of pay", "lop", "unpaid"}
        while current <= end_date:
            if current in work_dates:
                if is_unpaid:
                    unpaid_leave_dates.add(current)
                elif used_by_type.get(leave_type.id, 0) < leave_type.annual_allowance:
                    paid_leave_dates.add(current)
                    used_by_type[leave_type.id] = used_by_type.get(leave_type.id, 0) + 1
                else:
                    unpaid_leave_dates.add(current)
            current += timedelta(days=1)

    attendance_rows = db.query(Attendance).filter(
        Attendance.employee_id == employee_id,
        Attendance.work_date >= month_start,
        Attendance.work_date <= month_end,
    ).all()
    attendance_by_date = {row.work_date: row for row in attendance_rows}
    payable_days = Decimal("0")
    working_days = Decimal(sum(month_start <= work_date <= month_end for work_date in work_dates))
    for work_date in work_dates:
        if not month_start <= work_date <= month_end:
            continue
        attendance = attendance_by_date.get(work_date)
        if attendance and attendance.status == "present":
            payable_days += Decimal("1")
            continue
        if work_date in paid_leave_dates:
            payable_days += Decimal("1")
        elif attendance and attendance.status == "half_day":
            payable_days += Decimal("0.5")
        elif work_date not in unpaid_leave_dates:
            continue
    return working_days, min(working_days, payable_days)


@app.post("/api/payroll/generate")
def generate_payroll(payload: PayrollGenerate, db: Session = Depends(get_db), actor: User = Depends(require_roles("admin","hr"))):
    year = payload.year
    month = payload.month
    period_end = date(year + (month == 12), 1 if month == 12 else month + 1, 1) - timedelta(days=1)
    if period_end >= date.today():
        raise HTTPException(422, "Payroll can only be generated for a completed month")
    employees=db.query(Employee).join(User, User.id == Employee.user_id).filter(Employee.is_active.is_(True), User.is_active.is_(True)).all()
    existing_ids = {
        row[0] for row in db.query(Payroll.employee_id).filter_by(year=year, month=month).all()
    }
    results=[]
    for employee in employees:
        if employee.id in existing_ids:
            continue
        working_days, payable_days = payroll_day_totals(db, employee.id, year, month)
        lop_days = working_days - payable_days
        period_start = date(year, month, 1)
        base_compensation = db.query(EmployeeCompensation).filter(
            EmployeeCompensation.employee_id == employee.id,
            EmployeeCompensation.effective_from <= period_end,
            (EmployeeCompensation.effective_to.is_(None))
            | (EmployeeCompensation.effective_to >= period_start),
        ).order_by(EmployeeCompensation.effective_from.desc()).first()
        salary_source = base_compensation or employee
        basic_salary = Decimal(salary_source.basic_salary)
        hra = Decimal(salary_source.hra)
        special_allowance = Decimal(salary_source.special_allowance)
        base_earnings = {
            "Basic salary": basic_salary,
            "House rent allowance": hra,
            "Special allowance": special_allowance,
        }
        base_earnings = {name: amount for name, amount in base_earnings.items() if amount}
        custom_assignments = db.query(EmployeeSalaryComponent, SalaryComponent).join(
            SalaryComponent, SalaryComponent.id == EmployeeSalaryComponent.component_id
        ).filter(
            EmployeeSalaryComponent.employee_id == employee.id,
            EmployeeSalaryComponent.effective_from <= period_end,
            (EmployeeSalaryComponent.effective_to.is_(None))
            | (EmployeeSalaryComponent.effective_to >= date(year, month, 1)),
            SalaryComponent.is_active.is_(True),
        ).all()
        custom_earnings: dict[str, Decimal] = {}
        custom_deductions: dict[str, Decimal] = {}
        for assignment, component in custom_assignments:
            amount = Decimal(assignment.monthly_amount)
            target = custom_earnings if component.component_type == "earning" else custom_deductions
            target[component.name] = target.get(component.name, Decimal("0")) + amount
        attendance_month_start = period_start
        attendance_month_end = date(year + (month == 12), month % 12 + 1, 1)
        overtime_minutes = db.query(func.coalesce(func.sum(Attendance.overtime_minutes), 0)).filter(
            Attendance.employee_id == employee.id,
            Attendance.work_date >= attendance_month_start,
            Attendance.work_date < attendance_month_end,
        ).scalar() or 0
        overtime_rate = (
            basic_salary / (Decimal(max(working_days, 1)) * Decimal(480))
        )
        overtime_pay = (overtime_rate * Decimal(overtime_minutes) * Decimal("1.5")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        earnings_breakdown = {**base_earnings, **custom_earnings}
        if overtime_pay:
            earnings_breakdown["Overtime pay"] = overtime_pay
        gross = sum(earnings_breakdown.values(), Decimal("0"))
        per_day = (
            ((gross - overtime_pay) / working_days).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if working_days
            else Decimal("0")
        )
        lop_deduction = min(
            gross,
            (per_day * lop_days).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        )
        pf_percentage = Decimal(salary_source.pf_percentage)
        pf_deduction = (basic_salary * pf_percentage / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        professional_tax = Decimal(salary_source.professional_tax)
        tds_deduction = Decimal(salary_source.tds)
        deductions_breakdown = {
            "Provident fund": pf_deduction,
            "Professional tax": professional_tax,
            "TDS": tds_deduction,
            **custom_deductions,
        }
        other_deductions = sum(deductions_breakdown.values(), Decimal("0"))
        net = max(Decimal("0"), gross - lop_deduction - other_deductions)
        payroll=Payroll(
            employee_id=employee.id,year=year,month=month,gross_salary=gross,
            basic_salary=basic_salary,hra=hra,special_allowance=special_allowance,
            pf_percentage=pf_percentage,pf_deduction=pf_deduction,
            professional_tax=professional_tax,tds_deduction=tds_deduction,
            working_days=working_days,payable_days=payable_days,
            lop_days=lop_days,lop_deduction=lop_deduction,
            other_deductions=other_deductions,net_salary=net,locked=True,
            overtime_minutes=overtime_minutes,overtime_pay=overtime_pay,
            earnings_breakdown={name: str(amount) for name, amount in earnings_breakdown.items()},
            deductions_breakdown={name: str(amount) for name, amount in deductions_breakdown.items()},
        )
        db.add(payroll)
        db.flush()
        results.append(payroll_dict(payroll, employee))
        log_notification(db, employee.user.email, "payroll_generated", {
            "period": f"{year}-{month:02d}",
            "net_salary": str(net),
        })
    audit(db,actor,"payroll.generated","payroll",None,f"month={year}-{month:02d}; count={len(results)}")
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Payroll for this month was generated by another request; reload payroll history")
    return {"year": year, "month": month, "generated_count":len(results),"skipped_existing":len(existing_ids),"payroll":results}

@app.get("/api/payroll/me")
def my_payroll(db: Session = Depends(get_db), employee: Employee = Depends(current_employee)):
    rows=db.query(Payroll).options(selectinload(Payroll.adjustments)).filter_by(employee_id=employee.id).order_by(Payroll.year.desc(),Payroll.month.desc()).all()
    return [payroll_dict(p, employee) for p in rows]

def payroll_dict(p, employee=None):
    adjustments = sorted(p.adjustments, key=lambda adjustment: adjustment.created_at)
    return {
        "id": p.id,
        "employee_id": p.employee_id,
        "employee_name": employee.full_name if employee else None,
        "employee_code": employee.employee_code if employee else None,
        "year": p.year,
        "month": p.month,
        "gross_salary": str(p.gross_salary),
        "basic_salary": str(p.basic_salary),
        "hra": str(p.hra),
        "special_allowance": str(p.special_allowance),
        "pf_percentage": str(p.pf_percentage),
        "pf_deduction": str(p.pf_deduction),
        "professional_tax": str(p.professional_tax),
        "tds_deduction": str(p.tds_deduction),
        "working_days": str(p.working_days),
        "payable_days": str(p.payable_days),
        "lop_days": str(p.lop_days),
        "lop_deduction": str(p.lop_deduction),
        "other_deductions": str(p.other_deductions),
        "overtime_minutes": p.overtime_minutes,
        "overtime_pay": str(p.overtime_pay),
        "earnings_breakdown": p.earnings_breakdown or {},
        "deductions_breakdown": p.deductions_breakdown or {},
        "net_salary": str(p.net_salary),
        "credit_reference": p.credit_reference,
        "manual_adjustment_total": str(sum((adjustment.amount for adjustment in adjustments), Decimal("0"))),
        "adjustments": [
            {
                "id": adjustment.id,
                "amount": str(adjustment.amount),
                "reason": adjustment.reason,
                "actor_user_id": adjustment.actor_user_id,
                "created_at": adjustment.created_at,
            }
            for adjustment in adjustments
        ],
        "locked": p.locked,
        "simulated_credited": p.simulated_credited,
        "generated_at": p.generated_at,
    }

@app.get("/api/payroll")
def all_payroll(year: int | None = None, month: int | None = None, department_id: int | None = None, employee_id: int | None = None, db: Session = Depends(get_db), actor: User = Depends(require_roles("admin","hr"))):
    q=db.query(Payroll, Employee).options(selectinload(Payroll.adjustments)).join(Employee, Employee.id == Payroll.employee_id)
    if year is not None: q=q.filter(Payroll.year==year)
    if month is not None: q=q.filter(Payroll.month==month)
    if department_id is not None: q=q.filter(Employee.department_id==department_id)
    if employee_id is not None: q=q.filter(Employee.id == employee_id)
    return [payroll_dict(payroll, employee) for payroll, employee in q.order_by(Payroll.year.desc(),Payroll.month.desc(),Employee.full_name).all()]

@app.post("/api/payroll/{payroll_id}/adjustments")
def adjust_payroll(payroll_id: int, payload: PayrollAdjustmentCreate, db: Session = Depends(get_db), actor: User = Depends(require_roles("admin"))):
    if payload.amount == 0:
        raise HTTPException(422, "Adjustment amount must be non-zero")
    payroll = db.query(Payroll).filter_by(id=payroll_id).with_for_update().first()
    if payroll is None:
        raise HTTPException(404, "Payroll record not found")
    if payroll.simulated_credited:
        raise HTTPException(409, "A credited payroll record cannot be adjusted")
    updated_net = Decimal(payroll.net_salary) + payload.amount
    if updated_net < 0:
        raise HTTPException(422, "An adjustment cannot make net salary negative")
    payroll.net_salary = updated_net
    db.add(PayrollAdjustment(
        payroll_id=payroll.id,
        actor_user_id=actor.id,
        amount=payload.amount,
        reason=payload.reason,
    ))
    audit(
        db,
        actor,
        "payroll.adjusted",
        "payroll",
        payroll.id,
        f"amount={payload.amount}; reason={payload.reason}",
    )
    db.commit()
    db.refresh(payroll)
    return payroll_dict(payroll, db.query(Employee).filter_by(id=payroll.employee_id).first())

@app.post("/api/payroll/{payroll_id}/simulate-credit")
def simulate_credit(payroll_id: int, db: Session = Depends(get_db), actor: User = Depends(require_roles("admin"))):
    p=db.query(Payroll).filter_by(id=payroll_id).with_for_update().first()
    if not p: raise HTTPException(404,"Payroll record not found")
    if p.simulated_credited: raise HTTPException(409,"Salary credit already simulated")
    p.simulated_credited=True
    p.credit_reference = f"SIM-{secrets.token_hex(12).upper()}"
    employee=db.query(Employee).filter_by(id=p.employee_id).first()
    audit(db,actor,"payroll.credit_simulated","payroll",p.id,"Simulation only; no funds transferred")
    log_notification(db, employee.user.email, "payroll_credit_simulated", {
        "period": f"{p.year}-{p.month:02d}",
    })
    db.commit()
    return payroll_dict(p, employee)

@app.get("/api/payroll/{payroll_id}/salary-slip.pdf")
def salary_slip(payroll_id: int, db: Session = Depends(get_db), actor: User = Depends(current_user)):
    p=db.query(Payroll).filter_by(id=payroll_id).first()
    if not p: raise HTTPException(404,"Salary slip not found")
    e=db.query(Employee).filter_by(id=p.employee_id).first()
    if not e: raise HTTPException(404,"Employee record not found")
    if actor.role == "employee" and e.user_id != actor.id:
        raise HTTPException(403, "You can only download your own salary slip")
    if actor.role not in {"employee", "admin", "hr"}:
        raise HTTPException(403, "You are not allowed to download salary slips")
    month_start = date(p.year, p.month, 1)
    next_month_start = date(p.year + (p.month == 12), p.month % 12 + 1, 1)
    attendance_rows = db.query(Attendance).filter(
        Attendance.employee_id == e.id,
        Attendance.work_date >= month_start,
        Attendance.work_date < next_month_start,
    ).all()
    present_days = sum(
        (
            Decimal("1") if row.status == "present"
            else Decimal("0.5") if row.status == "half_day"
            else Decimal("0")
            for row in attendance_rows
        ),
        Decimal("0"),
    )
    audit(db, actor, "payroll.salary_slip_downloaded", "payroll", p.id, f"employee_id={e.id}; period={p.year}-{p.month:02d}")
    db.commit()
    pdf_content = generate_salary_slip_pdf(e, p, present_days=present_days)
    return Response(
        content=pdf_content,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=salary-slip-{p.year}-{p.month:02d}.pdf"},
    )

@app.get("/api/dashboard/summary")
def dashboard_summary(db: Session = Depends(get_db), actor: User = Depends(require_roles("admin","hr"))):
    today = date.today()
    month_start = date(today.year, today.month, 1)
    month_end = date(today.year + (today.month == 12), 1 if today.month == 12 else today.month + 1, 1) - timedelta(days=1)
    active_employees = db.query(Employee).filter_by(is_active=True).count()
    pending_leave_count = db.query(LeaveRequest).filter_by(status="pending").count()
    approved_leave_month = db.query(LeaveRequest).filter(
        LeaveRequest.status == "approved",
        LeaveRequest.start_date <= month_end,
        LeaveRequest.end_date >= month_start,
    ).count()
    payroll_records = db.query(Payroll).filter_by(year=today.year, month=today.month).all()
    return {
        "employee_count": active_employees,
        "present_today": db.query(Attendance).filter_by(work_date=today, status="present").count(),
        "half_day_today": db.query(Attendance).filter_by(work_date=today, status="half_day").count(),
        "absent_today": db.query(Attendance).filter_by(work_date=today, status="absent").count(),
        "on_leave_today": db.query(LeaveRequest).filter(
            LeaveRequest.status == "approved",
            LeaveRequest.start_date <= today,
            LeaveRequest.end_date >= today,
        ).count(),
        "pending_leaves": pending_leave_count,
        "approved_leave_requests_this_month": approved_leave_month,
        "payroll_records_this_month": len(payroll_records),
        "payroll_net_total_this_month": str(sum((Decimal(row.net_salary) for row in payroll_records), Decimal("0"))),
        "payroll_locked_count_this_month": sum(1 for row in payroll_records if row.locked),
    }

@app.get("/api/reports/attendance.csv")
def attendance_csv(start_date: date, end_date: date, department_id: int | None = None, db: Session = Depends(get_db), actor: User = Depends(require_roles("admin","hr"))):
    return report_export("attendance", "csv", start_date, end_date, department_id, db, actor)

@app.get("/api/reports/{report_name}.{file_format}")
def report_export_route(
    report_name: str,
    file_format: str,
    start_date: date,
    end_date: date,
    department_id: int | None = None,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("admin", "hr")),
):
    return report_export(report_name, file_format, start_date, end_date, department_id, db, actor)

@app.get("/api/reports/{report_name}/data")
def report_data_route(
    report_name: str,
    start_date: date,
    end_date: date,
    department_id: int | None = None,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("admin", "hr")),
):
    rows = report_rows(report_name, start_date, end_date, department_id, db)
    return {"columns": rows[0], "rows": rows[1:]}

def report_rows(report_name: str, start_date: date, end_date: date, department_id: int | None, db: Session):
    if report_name not in {"attendance", "leaves", "payroll"}:
        raise HTTPException(404, "Report type not found")
    if end_date < start_date:
        raise HTTPException(422, "end_date must be on or after start_date")

    if report_name == "attendance":
        query = db.query(Attendance, Employee).join(Employee, Employee.id == Attendance.employee_id).filter(
            Attendance.work_date.between(start_date, end_date),
        )
        if department_id is not None:
            query = query.filter(Employee.department_id == department_id)
        rows = [
            ["Employee code", "Employee name", "Date", "Check in", "Check out", "Working minutes", "Status"],
            *[
                [employee.employee_code, employee.full_name, row.work_date, row.check_in, row.check_out, row.working_minutes, row.status]
                for row, employee in query.order_by(Attendance.work_date, Employee.full_name).all()
            ],
        ]
    elif report_name == "leaves":
        query = db.query(LeaveRequest, Employee, LeaveType).options(joinedload(Employee.department)).join(
            Employee, Employee.id == LeaveRequest.employee_id
        ).join(LeaveType, LeaveType.id == LeaveRequest.leave_type_id).filter(
            LeaveRequest.start_date <= end_date,
            LeaveRequest.end_date >= start_date,
        )
        if department_id is not None:
            query = query.filter(Employee.department_id == department_id)
        rows = [
            ["Employee code", "Employee name", "Department", "Leave type", "Start date", "End date", "Days", "Status", "Reason"],
            *[
                [
                    employee.employee_code, employee.full_name,
                    employee.department.name if employee.department else "",
                    leave_type.name, leave.start_date, leave.end_date, leave.days, leave.status, leave.reason,
                ]
                for leave, employee, leave_type in query.order_by(LeaveRequest.start_date, Employee.full_name).all()
            ],
        ]
    else:
        query = db.query(Payroll, Employee).options(
            selectinload(Payroll.adjustments),
            joinedload(Employee.department),
        ).join(Employee, Employee.id == Payroll.employee_id).filter(
            Payroll.year >= start_date.year,
            Payroll.year <= end_date.year,
        )
        if department_id is not None:
            query = query.filter(Employee.department_id == department_id)
        matched = []
        for payroll, employee in query.order_by(Payroll.year, Payroll.month, Employee.full_name).all():
            period_start = date(payroll.year, payroll.month, 1)
            period_end = date(
                payroll.year + (payroll.month == 12),
                1 if payroll.month == 12 else payroll.month + 1,
                1,
            ) - timedelta(days=1)
            if period_start <= end_date and period_end >= start_date:
                matched.append((payroll, employee))
        rows = [
            ["Period", "Employee code", "Employee name", "Department", "Gross salary", "LOP deduction", "PF", "Professional tax", "TDS", "Adjustments", "Net salary", "Status"],
            *[
                [
                    f"{payroll.year}-{payroll.month:02d}",
                    employee.employee_code,
                    employee.full_name,
                    employee.department.name if employee.department else "",
                    payroll.gross_salary,
                    payroll.lop_deduction,
                    payroll.pf_deduction,
                    payroll.professional_tax,
                    payroll.tds_deduction,
                    sum((adjustment.amount for adjustment in payroll.adjustments), Decimal("0")),
                    payroll.net_salary,
                    "GENERATED" if payroll.locked else "DRAFT",
                ]
                for payroll, employee in matched
            ],
        ]
    return rows

def report_export(report_name: str, file_format: str, start_date: date, end_date: date, department_id: int | None, db: Session, actor: User):
    if file_format not in {"csv", "pdf"}:
        raise HTTPException(404, "Report format not supported")
    rows = report_rows(report_name, start_date, end_date, department_id, db)

    audit(
        db,
        actor,
        "report.exported",
        "report",
        report_name,
        f"format={file_format}; start_date={start_date}; end_date={end_date}; department_id={department_id}",
    )
    db.commit()

    if file_format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerows(rows)
        return Response(
            output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={report_name}-report.csv"},
        )

    output = io.BytesIO()
    pdf = canvas.Canvas(output, pagesize=A4)
    pdf.setTitle(f"{report_name.title()} report {start_date} to {end_date}")
    pdf.setFont("Helvetica-Bold", 15)
    pdf.drawString(40, 805, f"{report_name.title()} report")
    pdf.setFont("Helvetica", 9)
    pdf.drawString(40, 788, f"Period: {start_date} to {end_date}")
    pdf.drawString(40, 774, f"Department ID: {department_id if department_id is not None else 'All'}")
    y = 748
    for index, row in enumerate(rows):
        if y < 45:
            pdf.showPage()
            y = 805
        pdf.setFont("Helvetica-Bold" if index == 0 else "Helvetica", 7 if index == 0 else 6)
        pdf.drawString(35, y, " | ".join(str(value) for value in row)[:170])
        y -= 12
    pdf.save()
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={report_name}-report.pdf"},
    )

@app.get("/api/audit-logs")
def audit_logs(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    actor_user_id: int | None = Query(default=None, ge=1),
    action: str | None = Query(default=None, min_length=1, max_length=120),
    entity_type: str | None = Query(default=None, min_length=1, max_length=80),
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("admin")),
):
    query = db.query(AuditLog)
    if actor_user_id is not None:
        query = query.filter(AuditLog.actor_user_id == actor_user_id)
    if action:
        query = query.filter(AuditLog.action == action)
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if start_date and end_date and end_date < start_date:
        raise HTTPException(422, "end_date must be on or after start_date")
    if start_date:
        query = query.filter(AuditLog.created_at >= datetime.combine(start_date, datetime.min.time()))
    if end_date:
        next_day = end_date + timedelta(days=1)
        query = query.filter(AuditLog.created_at < datetime.combine(next_day, datetime.min.time()))
    rows = query.order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).offset(offset).limit(limit).all()
    return [{"id":r.id,"actor_user_id":r.actor_user_id,"action":r.action,"entity_type":r.entity_type,"entity_id":r.entity_id,"details":r.details,"created_at":r.created_at} for r in rows]

@app.get("/api/notifications/logs")
def notification_logs(limit: int = Query(100,ge=1,le=500), db: Session = Depends(get_db), actor: User = Depends(require_roles("admin","hr"))):
    rows=db.query(NotificationLog).order_by(NotificationLog.created_at.desc()).limit(limit).all()
    return [{"id":r.id,"recipient":r.recipient,"event_type":r.event_type,"subject":r.subject,"status":r.status,"created_at":r.created_at} for r in rows]

app.include_router(phase_two_router, prefix="/api")
