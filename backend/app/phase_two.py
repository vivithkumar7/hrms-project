from datetime import date, time, timedelta
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .database import get_db
from .dependencies import current_user, require_roles
from .models import (
    Attendance,
    Department,
    Employee,
    EmployeeCompensation,
    EmployeeSalaryComponent,
    Holiday,
    InAppNotification,
    NotificationPreference,
    Payroll,
    SalaryComponent,
    Shift,
    ShiftAssignment,
    User,
    utc_now,
)

router = APIRouter()


def audit(db: Session, actor: User, action: str, entity: str, entity_id: int | None, details: str = "") -> None:
    from .models import AuditLog

    db.add(AuditLog(
        actor_user_id=actor.id,
        action=action,
        entity_type=entity,
        entity_id=str(entity_id) if entity_id is not None else None,
        details=details or None,
    ))


def add_in_app_notification(db: Session, user_id: int, event_type: str, title: str, message: str) -> None:
    preference = db.query(NotificationPreference).filter_by(
        user_id=user_id, event_type=event_type
    ).first()
    if preference is None or preference.enabled:
        db.add(InAppNotification(
            user_id=user_id,
            event_type=event_type,
            title=title,
            message=message,
        ))


class NotificationPreferenceIn(BaseModel):
    event_type: Literal[
        "employee_onboarding", "leave_application", "leave_decision",
        "payroll_generated", "payroll_credit_simulated", "attendance_alert",
        "admin_announcement",
    ]
    enabled: bool


class BroadcastIn(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    message: str = Field(min_length=2, max_length=4000)
    department_ids: list[int] | None = None

    @model_validator(mode="after")
    def normalize(self):
        self.title = self.title.strip()
        self.message = self.message.strip()
        if len(self.title) < 2 or len(self.message) < 2:
            raise ValueError("Title and message must contain at least 2 non-whitespace characters")
        if self.department_ids is not None and len(set(self.department_ids)) != len(self.department_ids):
            raise ValueError("department_ids cannot contain duplicates")
        if self.department_ids == []:
            raise ValueError("Select at least one department or omit department_ids for an organization-wide announcement")
        return self


class ShiftIn(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    shift_type: str = Field(pattern="^(general|night|flexible|remote)$")
    start_time: time
    end_time: time
    grace_minutes: int = Field(default=0, ge=0, le=240)
    expected_minutes: int = Field(default=480, ge=1, le=1440)

    @model_validator(mode="after")
    def validate_shift(self):
        self.name = self.name.strip()
        if not self.name:
            raise ValueError("Shift name cannot be blank")
        if self.start_time == self.end_time and self.expected_minutes < 1440:
            raise ValueError("Equal start and end times require a 24-hour shift")
        return self


class ShiftAssignmentIn(BaseModel):
    shift_id: int = Field(ge=1)
    employee_id: int | None = Field(default=None, ge=1)
    department_id: int | None = Field(default=None, ge=1)
    effective_from: date
    effective_to: date | None = None

    @model_validator(mode="after")
    def validate_assignment(self):
        if (self.employee_id is None) == (self.department_id is None):
            raise ValueError("Specify exactly one of employee_id or department_id")
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise ValueError("effective_to must be on or after effective_from")
        return self


class ShiftStatusIn(BaseModel):
    is_active: bool


class SalaryComponentIn(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    component_type: str = Field(pattern="^(earning|deduction)$")
    is_variable: bool = False

    @model_validator(mode="after")
    def normalize_name(self):
        self.name = self.name.strip()
        if len(self.name) < 2:
            raise ValueError("Component name must contain at least 2 non-whitespace characters")
        return self


class EmployeeComponentIn(BaseModel):
    component_id: int = Field(ge=1)
    monthly_amount: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    effective_from: date
    effective_to: date | None = None

    @model_validator(mode="after")
    def validate_period(self):
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise ValueError("effective_to must be on or after effective_from")
        return self


class BaseCompensationIn(BaseModel):
    basic_salary: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    hra: Decimal = Field(default=0, ge=0, max_digits=12, decimal_places=2)
    special_allowance: Decimal = Field(default=0, ge=0, max_digits=12, decimal_places=2)
    pf_percentage: Decimal = Field(default=0, ge=0, le=100, max_digits=5, decimal_places=2)
    professional_tax: Decimal = Field(default=0, ge=0, max_digits=12, decimal_places=2)
    tds: Decimal = Field(default=0, ge=0, max_digits=12, decimal_places=2)
    effective_from: date


def employee_compensation_values(employee: Employee) -> dict[str, Decimal]:
    return {
        "monthly_salary": Decimal(employee.basic_salary) + Decimal(employee.hra) + Decimal(employee.special_allowance),
        "basic_salary": Decimal(employee.basic_salary),
        "hra": Decimal(employee.hra),
        "special_allowance": Decimal(employee.special_allowance),
        "pf_percentage": Decimal(employee.pf_percentage),
        "professional_tax": Decimal(employee.professional_tax),
        "tds": Decimal(employee.tds),
    }


def record_compensation_revision(
    db: Session,
    employee: Employee,
    actor: User,
    effective_from: date,
    values: dict[str, Decimal],
    previous_values: dict[str, Decimal] | None = None,
) -> EmployeeCompensation:
    overlapping = db.query(EmployeeCompensation).filter(
        EmployeeCompensation.employee_id == employee.id,
        or_(
            EmployeeCompensation.effective_to.is_(None),
            EmployeeCompensation.effective_to >= effective_from,
        ),
    ).order_by(EmployeeCompensation.effective_from.desc()).first()
    if overlapping and overlapping.effective_from == effective_from:
        for key, value in values.items():
            setattr(overlapping, key, value)
        return overlapping
    if overlapping:
        if overlapping.effective_from > effective_from:
            raise HTTPException(409, "Compensation revisions must be entered in effective-date order")
        overlapping.effective_to = effective_from - timedelta(days=1)
    elif previous_values and effective_from > employee.joining_date:
        db.add(EmployeeCompensation(
            employee_id=employee.id,
            **previous_values,
            effective_from=employee.joining_date,
            effective_to=effective_from - timedelta(days=1),
            assigned_by=actor.id,
        ))
    row = EmployeeCompensation(
        employee_id=employee.id,
        **values,
        effective_from=effective_from,
        assigned_by=actor.id,
    )
    db.add(row)
    return row


@router.get("/holidays/calendar")
def holiday_calendar(
    year: int = Query(ge=2000, le=2100),
    actor: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    holidays = db.query(Holiday).filter(
        Holiday.holiday_date >= date(year, 1, 1),
        Holiday.holiday_date < date(year + 1, 1, 1),
    )
    if actor.role == "employee":
        employee = db.query(Employee).filter_by(user_id=actor.id, is_active=True).first()
        if employee is None:
            raise HTTPException(404, "Employee profile not found")
        holidays = holidays.filter(or_(
            Holiday.department_id.is_(None),
            Holiday.department_id == employee.department_id,
        ))
    rows = holidays.order_by(Holiday.holiday_date, Holiday.name).all()
    return [{
        "id": row.id,
        "holiday_date": row.holiday_date,
        "name": row.name,
        "scope": row.scope,
        "department_id": row.department_id,
        "is_optional": row.is_optional,
    } for row in rows]


@router.get("/notifications/me")
def my_notifications(
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
):
    rows = db.query(InAppNotification).filter_by(user_id=actor.id).order_by(
        InAppNotification.created_at.desc(), InAppNotification.id.desc()
    ).limit(limit).all()
    unread_count = db.query(InAppNotification).filter_by(user_id=actor.id, is_read=False).count()
    return {
        "unread_count": unread_count,
        "notifications": [{
            "id": row.id,
            "event_type": row.event_type,
            "title": row.title,
            "message": row.message,
            "is_read": row.is_read,
            "created_at": row.created_at,
        } for row in rows],
    }


@router.patch("/notifications/me/preferences")
def update_notification_preference(
    payload: NotificationPreferenceIn,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
):
    row = db.query(NotificationPreference).filter_by(
        user_id=actor.id, event_type=payload.event_type
    ).first()
    if row is None:
        row = NotificationPreference(
            user_id=actor.id, event_type=payload.event_type, enabled=payload.enabled
        )
        db.add(row)
    else:
        row.enabled = payload.enabled
    db.commit()
    return {"event_type": row.event_type, "enabled": row.enabled}


@router.get("/notifications/me/preferences")
def list_notification_preferences(
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
):
    rows = db.query(NotificationPreference).filter_by(user_id=actor.id).all()
    values = {row.event_type: row.enabled for row in rows}
    return {
        "preferences": values,
        "default_enabled": True,
    }


@router.post("/notifications/me/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
):
    row = db.query(InAppNotification).filter_by(
        id=notification_id, user_id=actor.id
    ).first()
    if row is None:
        raise HTTPException(404, "Notification not found")
    row.is_read = True
    db.commit()
    return {"id": row.id, "is_read": row.is_read}


@router.post("/notifications/broadcast", status_code=201)
def broadcast_notification(
    payload: BroadcastIn,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("admin")),
):
    query = db.query(Employee).join(User).filter(
        Employee.is_active.is_(True), User.is_active.is_(True)
    )
    if payload.department_ids is not None:
        departments = db.query(Department.id).filter(Department.id.in_(payload.department_ids)).all()
        if len(departments) != len(payload.department_ids):
            raise HTTPException(422, "One or more departments do not exist")
        query = query.filter(Employee.department_id.in_(payload.department_ids))
    recipients = query.all()
    for employee in recipients:
        add_in_app_notification(
            db, employee.user_id, "admin_announcement", payload.title, payload.message
        )
    audit(db, actor, "notification.broadcast", "notification", None,
          f"recipient_count={len(recipients)}; department_ids={payload.department_ids}")
    db.commit()
    return {"recipient_count": len(recipients)}


def shift_dict(shift: Shift) -> dict:
    return {
        "id": shift.id,
        "name": shift.name,
        "shift_type": shift.shift_type,
        "start_time": shift.start_time.strftime("%H:%M"),
        "end_time": shift.end_time.strftime("%H:%M"),
        "grace_minutes": shift.grace_minutes,
        "expected_minutes": shift.expected_minutes,
        "is_active": shift.is_active,
    }


@router.get("/shifts")
def list_shifts(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
):
    query = db.query(Shift)
    if not include_inactive:
        query = query.filter(Shift.is_active.is_(True))
    return [shift_dict(row) for row in query.order_by(Shift.name).all()]


@router.post("/shifts", status_code=201)
def create_shift(
    payload: ShiftIn,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("admin")),
):
    row = Shift(**payload.model_dump())
    db.add(row)
    try:
        db.flush()
        audit(db, actor, "shift.created", "shift", row.id)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "A shift with this name already exists")
    db.refresh(row)
    return shift_dict(row)


@router.patch("/shifts/{shift_id}")
def update_shift_status(
    shift_id: int,
    payload: ShiftStatusIn,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("admin")),
):
    row = db.query(Shift).filter_by(id=shift_id).first()
    if row is None:
        raise HTTPException(404, "Shift not found")
    row.is_active = payload.is_active
    audit(db, actor, "shift.activated" if row.is_active else "shift.deactivated",
          "shift", row.id)
    db.commit()
    db.refresh(row)
    return shift_dict(row)


def overlapping_assignments(
    db: Session,
    employee_id: int | None,
    department_id: int | None,
    start: date,
    end: date | None,
) -> list[ShiftAssignment]:
    query = db.query(ShiftAssignment).filter(
        ShiftAssignment.employee_id == employee_id,
        ShiftAssignment.department_id == department_id,
        ShiftAssignment.effective_from <= (end or date.max),
        or_(ShiftAssignment.effective_to.is_(None), ShiftAssignment.effective_to >= start),
    )
    return query.order_by(ShiftAssignment.effective_from).all()


@router.post("/shifts/assignments", status_code=201)
def assign_shift(
    payload: ShiftAssignmentIn,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("admin", "hr")),
):
    shift = db.query(Shift).filter_by(id=payload.shift_id, is_active=True).first()
    if shift is None:
        raise HTTPException(404, "Active shift not found")
    if payload.employee_id is not None and db.query(Employee).filter_by(
        id=payload.employee_id, is_active=True
    ).first() is None:
        raise HTTPException(404, "Active employee not found")
    if payload.department_id is not None and db.query(Department).filter_by(
        id=payload.department_id
    ).first() is None:
        raise HTTPException(404, "Department not found")
    conflicts = overlapping_assignments(
        db, payload.employee_id, payload.department_id,
        payload.effective_from, payload.effective_to
    )
    for previous in conflicts:
        if previous.effective_from >= payload.effective_from:
            raise HTTPException(
                409,
                "This assignment overlaps a same-day or future assignment for the same target",
            )
        previous.effective_to = payload.effective_from - timedelta(days=1)
    row = ShiftAssignment(**payload.model_dump(), assigned_by=actor.id)
    db.add(row)
    db.flush()
    target = f"employee_id={payload.employee_id}" if payload.employee_id else f"department_id={payload.department_id}"
    audit(
        db,
        actor,
        "shift.assigned",
        "shift_assignment",
        row.id,
        f"shift_id={payload.shift_id}; {target}; effective_from={payload.effective_from}; "
        f"effective_to={payload.effective_to}",
    )
    db.commit()
    return {"id": row.id, **payload.model_dump()}


@router.get("/shifts/assignments")
def list_shift_assignments(
    employee_id: int | None = None,
    department_id: int | None = None,
    include_history: bool = False,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
):
    query = db.query(ShiftAssignment, Shift).join(Shift, Shift.id == ShiftAssignment.shift_id)
    if actor.role == "employee":
        employee = db.query(Employee).filter_by(user_id=actor.id).first()
        if employee is None:
            raise HTTPException(404, "Employee profile not found")
        if employee.department_id is None:
            query = query.filter(ShiftAssignment.employee_id == employee.id)
        else:
            query = query.filter(or_(
                ShiftAssignment.employee_id == employee.id,
                ShiftAssignment.department_id == employee.department_id,
            ))
    elif employee_id is not None:
        query = query.filter(ShiftAssignment.employee_id == employee_id)
    elif department_id is not None:
        query = query.filter(ShiftAssignment.department_id == department_id)
    if not include_history:
        today = date.today()
        query = query.filter(
            ShiftAssignment.effective_from <= today,
            or_(ShiftAssignment.effective_to.is_(None), ShiftAssignment.effective_to >= today),
        )
    return [{
        "id": assignment.id,
        "employee_id": assignment.employee_id,
        "department_id": assignment.department_id,
        "effective_from": assignment.effective_from,
        "effective_to": assignment.effective_to,
        "shift": shift_dict(shift),
    } for assignment, shift in query.order_by(ShiftAssignment.effective_from.desc()).limit(500).all()]


@router.get("/shifts/attendance")
def shift_attendance_report(
    start_date: date,
    end_date: date,
    shift_id: int | None = None,
    department_id: int | None = None,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("admin", "hr")),
):
    if end_date < start_date:
        raise HTTPException(422, "end_date must be on or after start_date")
    query = db.query(Attendance, Employee, Shift).join(
        Employee, Employee.id == Attendance.employee_id
    ).outerjoin(Shift, Shift.id == Attendance.shift_id).filter(
        Attendance.work_date.between(start_date, end_date)
    )
    if shift_id is not None:
        if db.query(Shift.id).filter_by(id=shift_id).first() is None:
            raise HTTPException(404, "Shift not found")
        query = query.filter(Attendance.shift_id == shift_id)
    if department_id is not None:
        query = query.filter(Employee.department_id == department_id)
    return [{
        "attendance_id": row.id,
        "employee_id": employee.id,
        "employee_name": employee.full_name,
        "department_id": employee.department_id,
        "work_date": row.work_date,
        "shift_id": shift.id if shift else None,
        "shift_name": shift.name if shift else "Unassigned",
        "status": row.status,
        "working_minutes": row.working_minutes,
        "late_minutes": row.late_minutes,
        "early_checkout_minutes": row.early_checkout_minutes,
        "overtime_minutes": row.overtime_minutes,
    } for row, employee, shift in query.order_by(Attendance.work_date.desc()).limit(2000).all()]


@router.get("/payroll/components")
def list_salary_components(
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("admin", "hr")),
):
    return [{
        "id": row.id,
        "name": row.name,
        "component_type": row.component_type,
        "is_variable": row.is_variable,
        "is_active": row.is_active,
    } for row in db.query(SalaryComponent).order_by(SalaryComponent.name).all()]


@router.post("/payroll/components", status_code=201)
def create_salary_component(
    payload: SalaryComponentIn,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("admin")),
):
    row = SalaryComponent(
        name=payload.name.strip(),
        component_type=payload.component_type,
        is_variable=payload.is_variable,
    )
    if len(row.name) < 2:
        raise HTTPException(422, "Component name must contain at least 2 non-whitespace characters")
    db.add(row)
    try:
        db.flush()
        audit(db, actor, "salary_component.created", "salary_component", row.id)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "A salary component with this name already exists")
    db.refresh(row)
    return {
        "id": row.id, "name": row.name, "component_type": row.component_type,
        "is_variable": row.is_variable, "is_active": row.is_active,
    }


@router.post("/payroll/compensation/{employee_id}/components", status_code=201)
def assign_employee_component(
    employee_id: int,
    payload: EmployeeComponentIn,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("admin")),
):
    employee = db.query(Employee).filter_by(id=employee_id, is_active=True).first()
    if employee is None:
        raise HTTPException(404, "Active employee not found")
    component = db.query(SalaryComponent).filter_by(id=payload.component_id, is_active=True).first()
    if component is None:
        raise HTTPException(404, "Active salary component not found")
    active = db.query(EmployeeSalaryComponent).filter(
        EmployeeSalaryComponent.employee_id == employee_id,
        EmployeeSalaryComponent.component_id == component.id,
        or_(EmployeeSalaryComponent.effective_to.is_(None),
            EmployeeSalaryComponent.effective_to >= payload.effective_from),
    ).order_by(EmployeeSalaryComponent.effective_from.desc()).first()
    if active:
        if active.effective_from >= payload.effective_from:
            raise HTTPException(409, "Compensation changes must start after the current effective date")
        active.effective_to = payload.effective_from - timedelta(days=1)
    row = EmployeeSalaryComponent(
        employee_id=employee_id,
        component_id=component.id,
        monthly_amount=payload.monthly_amount,
        effective_from=payload.effective_from,
        effective_to=payload.effective_to,
        assigned_by=actor.id,
    )
    db.add(row)
    db.flush()
    audit(db, actor, "employee.compensation_revised", "employee", employee_id,
          f"component={component.name}; effective_from={payload.effective_from}")
    db.commit()
    return {
        "id": row.id, "employee_id": row.employee_id, "component_id": row.component_id,
        "component": component.name, "component_type": component.component_type,
        "monthly_amount": str(row.monthly_amount), "effective_from": row.effective_from,
        "effective_to": row.effective_to,
    }


@router.get("/payroll/compensation/{employee_id}/components")
def list_employee_components(
    employee_id: int,
    include_history: bool = False,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
):
    employee = db.query(Employee).filter_by(id=employee_id).first()
    if employee is None:
        raise HTTPException(404, "Employee not found")
    if actor.role == "employee" and employee.user_id != actor.id:
        raise HTTPException(403, "You can only view your own compensation")
    query = db.query(EmployeeSalaryComponent, SalaryComponent).join(
        SalaryComponent, SalaryComponent.id == EmployeeSalaryComponent.component_id
    ).filter(EmployeeSalaryComponent.employee_id == employee_id)
    if not include_history:
        today = date.today()
        query = query.filter(
            EmployeeSalaryComponent.effective_from <= today,
            or_(EmployeeSalaryComponent.effective_to.is_(None),
                EmployeeSalaryComponent.effective_to >= today),
        )
    return [{
        "id": assignment.id, "component_id": component.id,
        "component": component.name, "component_type": component.component_type,
        "is_variable": component.is_variable,
        "monthly_amount": str(assignment.monthly_amount),
        "effective_from": assignment.effective_from,
        "effective_to": assignment.effective_to,
    } for assignment, component in query.order_by(
        EmployeeSalaryComponent.effective_from.desc()
    ).limit(500).all()]


@router.get("/payroll/compensation/{employee_id}/base")
def list_base_compensation(
    employee_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
):
    employee = db.query(Employee).filter_by(id=employee_id).first()
    if employee is None:
        raise HTTPException(404, "Employee not found")
    if actor.role == "employee" and employee.user_id != actor.id:
        raise HTTPException(403, "You can only view your own compensation")
    rows = db.query(EmployeeCompensation).filter_by(employee_id=employee_id).order_by(
        EmployeeCompensation.effective_from.desc()
    ).limit(200).all()
    if not rows:
        return [{
            **{key: str(value) for key, value in employee_compensation_values(employee).items()},
            "effective_from": employee.joining_date,
            "effective_to": None,
        }]
    return [{
        **{key: str(getattr(row, key)) for key in (
            "monthly_salary", "basic_salary", "hra", "special_allowance",
            "pf_percentage", "professional_tax", "tds",
        )},
        "effective_from": row.effective_from,
        "effective_to": row.effective_to,
    } for row in rows]


@router.post("/payroll/compensation/{employee_id}/base", status_code=201)
def revise_base_compensation(
    employee_id: int,
    payload: BaseCompensationIn,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("admin")),
):
    employee = db.query(Employee).filter_by(id=employee_id, is_active=True).first()
    if employee is None:
        raise HTTPException(404, "Active employee not found")
    values = payload.model_dump(exclude={"effective_from"})
    values["monthly_salary"] = (
        payload.basic_salary + payload.hra + payload.special_allowance
    )
    previous_values = employee_compensation_values(employee)
    row = record_compensation_revision(
        db, employee, actor, payload.effective_from, values, previous_values
    )
    if payload.effective_from <= date.today():
        for key, value in values.items():
            setattr(employee, key, value)
    audit(db, actor, "employee.compensation_revised", "employee", employee.id,
          f"base_salary_effective_from={payload.effective_from}")
    db.commit()
    return {
        **{key: str(getattr(row, key)) for key in (
            "monthly_salary", "basic_salary", "hra", "special_allowance",
            "pf_percentage", "professional_tax", "tds",
        )},
        "effective_from": row.effective_from,
        "effective_to": row.effective_to,
    }
