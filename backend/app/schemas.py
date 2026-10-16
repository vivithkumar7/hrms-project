from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator
from typing import Literal

class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)

class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    full_name: str = Field(min_length=2, max_length=160)

    @field_validator("email")
    @classmethod
    def normalize_registration_email(cls, value: EmailStr) -> EmailStr:
        return str(value).lower()

    @field_validator("full_name")
    @classmethod
    def trim_registration_name(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Name must contain at least 2 non-whitespace characters")
        return value

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10)
    role: Literal["admin", "hr", "employee"] = "employee"
class UserRoleUpdate(BaseModel):
    role: Literal["admin", "hr", "employee"]

class DepartmentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)

    @field_validator("name")
    @classmethod
    def trim_department_name(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Department name must contain at least 2 non-whitespace characters")
        return value

class EmployeeCreate(BaseModel):
    email: EmailStr
    temporary_password: str = Field(min_length=10)
    employee_code: str = Field(min_length=2, max_length=30)
    full_name: str = Field(min_length=2, max_length=160)
    department_id: int | None = Field(default=None, ge=1)
    designation: str = Field(default="Employee", min_length=2, max_length=120)
    joining_date: date = Field(default_factory=date.today)
    monthly_salary: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    basic_salary: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    hra: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    special_allowance: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    pf_percentage: Decimal = Field(default=0, ge=0, le=100, max_digits=5, decimal_places=2)
    professional_tax: Decimal = Field(default=0, ge=0, max_digits=12, decimal_places=2)
    tds: Decimal = Field(default=0, ge=0, max_digits=12, decimal_places=2)
    phone: str | None = Field(default=None, max_length=30)
    date_of_birth: date | None = None
    address: str | None = Field(default=None, max_length=2000)
    emergency_contact_name: str | None = Field(default=None, max_length=160)
    emergency_contact_relationship: str | None = Field(default=None, max_length=80)
    emergency_contact_phone: str | None = Field(default=None, max_length=30)

    @field_validator("employee_code", "full_name", "designation")
    @classmethod
    def trim_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank")
        return value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> EmailStr:
        return str(value).lower()

    @field_validator("phone")
    @classmethod
    def trim_phone(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None

    @field_validator("address", "emergency_contact_name", "emergency_contact_relationship", "emergency_contact_phone")
    @classmethod
    def trim_optional_details(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None

    @field_validator("date_of_birth")
    @classmethod
    def validate_date_of_birth(cls, value: date | None) -> date | None:
        if value is not None and value > date.today():
            raise ValueError("Date of birth cannot be in the future")
        return value

class EmployeeUpdate(BaseModel):
    email: EmailStr | None = None
    employee_code: str | None = Field(default=None, min_length=2, max_length=30)
    full_name: str | None = Field(default=None, min_length=2, max_length=160)
    department_id: int | None = Field(default=None, ge=1)
    designation: str | None = Field(default=None, min_length=2, max_length=120)
    joining_date: date | None = None
    monthly_salary: Decimal | None = Field(default=None, ge=0)
    basic_salary: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    hra: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    special_allowance: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    pf_percentage: Decimal | None = Field(default=None, ge=0, le=100, max_digits=5, decimal_places=2)
    professional_tax: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    tds: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    phone: str | None = Field(default=None, max_length=30)
    date_of_birth: date | None = None
    address: str | None = Field(default=None, max_length=2000)
    emergency_contact_name: str | None = Field(default=None, max_length=160)
    emergency_contact_relationship: str | None = Field(default=None, max_length=80)
    emergency_contact_phone: str | None = Field(default=None, max_length=30)
    is_active: bool | None = None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr | None) -> EmailStr | None:
        return str(value).lower() if value is not None else None

    @field_validator("employee_code", "full_name", "designation")
    @classmethod
    def trim_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank")
        return value

    @field_validator("phone")
    @classmethod
    def trim_phone(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None

    @field_validator("address", "emergency_contact_name", "emergency_contact_relationship", "emergency_contact_phone")
    @classmethod
    def trim_optional_details(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None

    @field_validator("date_of_birth")
    @classmethod
    def validate_date_of_birth(cls, value: date | None) -> date | None:
        if value is not None and value > date.today():
            raise ValueError("Date of birth cannot be in the future")
        return value

    @model_validator(mode="after")
    def reject_null_required_fields(self):
        for field_name in ("email", "employee_code", "full_name", "designation", "joining_date", "monthly_salary", "is_active"):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self

class EmployeeSelfProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    phone: str | None = Field(default=None, max_length=30)
    date_of_birth: date | None = None
    address: str | None = Field(default=None, max_length=2000)
    emergency_contact_name: str | None = Field(default=None, max_length=160)
    emergency_contact_relationship: str | None = Field(default=None, max_length=80)
    emergency_contact_phone: str | None = Field(default=None, max_length=30)

    @field_validator(
        "phone",
        "address",
        "emergency_contact_name",
        "emergency_contact_relationship",
        "emergency_contact_phone",
    )
    @classmethod
    def trim_optional_profile_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @field_validator("date_of_birth")
    @classmethod
    def validate_profile_date_of_birth(cls, value: date | None) -> date | None:
        if value is not None and value > date.today():
            raise ValueError("Date of birth cannot be in the future")
        return value

    @model_validator(mode="after")
    def require_profile_changes(self):
        if not self.model_fields_set:
            raise ValueError("Provide at least one profile field to update")
        return self

class AttendanceCorrection(BaseModel):
    check_in: datetime | None = None
    check_out: datetime | None = None
    shift_id: int | None = Field(default=None, ge=1)
    status: str | None = Field(default=None, pattern="^(present|absent|half_day|on_leave)$")
    reason: str = Field(min_length=3, max_length=500)

    @model_validator(mode="after")
    def correction_is_valid(self):
        if self.check_in and self.check_out and self.check_in.tzinfo == self.check_out.tzinfo and self.check_out < self.check_in:
            raise ValueError("check_out must be at or after check_in")
        if len(self.reason.strip()) < 3:
            raise ValueError("reason must contain at least 3 non-whitespace characters")
        return self
class LeaveApply(BaseModel):
    leave_type_id: int
    start_date: date
    end_date: date
    reason: str = Field(min_length=3, max_length=2000)

    @field_validator("reason")
    @classmethod
    def trim_reason(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 3:
            raise ValueError("reason must contain at least 3 non-whitespace characters")
        return value

    @model_validator(mode="after")
    def dates_valid(self):
        if self.end_date < self.start_date: raise ValueError("end_date must be on or after start_date")
        return self

class LeaveTypeCreate(BaseModel):
    name: str = Field(min_length=2, max_length=60)
    annual_allowance: int = Field(ge=0, le=366)

    @field_validator("name")
    @classmethod
    def trim_name(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("name must contain at least 2 non-whitespace characters")
        return value

class PayrollGenerate(BaseModel):
    year: int = Field(ge=2000, le=2100)
    month: int = Field(ge=1, le=12)
class PayrollAdjustmentCreate(BaseModel):
    amount: Decimal = Field(gt=-1000000000, lt=1000000000, max_digits=12, decimal_places=2)
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("reason")
    @classmethod
    def trim_adjustment_reason(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 3:
            raise ValueError("reason must contain at least 3 non-whitespace characters")
        return value
class LeaveDecision(BaseModel):
    status: str
    note: str | None = Field(default=None, max_length=1000)
    @model_validator(mode="after")
    def status_valid(self):
        if self.status not in {"approved", "rejected"}: raise ValueError("status must be approved or rejected")
        if self.note is not None:
            self.note = self.note.strip()
        return self

class HolidayCreate(BaseModel):
    holiday_date: date
    name: str = Field(min_length=2, max_length=120)
    scope: Literal["company", "regional", "optional"] = "company"
    department_id: int | None = Field(default=None, ge=1)
    is_optional: bool = False

    @field_validator("name")
    @classmethod
    def trim_holiday_name(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("name must contain at least 2 non-whitespace characters")
        return value

    @model_validator(mode="after")
    def validate_scope(self):
        if self.scope == "regional" and self.department_id is None:
            raise ValueError("Regional holidays must be assigned to a department")
        if self.scope == "company" and self.department_id is not None:
            raise ValueError("Company-wide holidays cannot be assigned to a department")
        if self.scope == "optional":
            self.is_optional = True
        return self
class ConfiguredModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
