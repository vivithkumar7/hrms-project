import base64
import os
import re
import shutil
import tempfile
import uuid
import zlib
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import smtplib

import pytest
from fastapi.testclient import TestClient
from fastapi.routing import APIRoute

_test_db_path = Path(tempfile.gettempdir()) / f"hrms-auth-{uuid.uuid4().hex}.db"
_test_upload_path = Path(tempfile.gettempdir()) / f"hrms-auth-uploads-{uuid.uuid4().hex}"
os.environ["DATABASE_URL"] = f"sqlite:///{_test_db_path.as_posix()}"
os.environ["JWT_SECRET_KEY"] = f"auth-test-secret-{uuid.uuid4().hex}-not-for-production"
os.environ["REFRESH_COOKIE_SECURE"] = "false"
os.environ["REFRESH_COOKIE_SAMESITE"] = "strict"
os.environ["CORS_ORIGINS"] = "http://testserver,http://localhost:5173,http://127.0.0.1:5173"
os.environ["UPLOAD_DIR"] = str(_test_upload_path)

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import Attendance, AuditLog, AuthSession, Department, Employee, EmployeeDocument, Holiday, LeaveBalance, LeaveRequest, LeaveType, NotificationLog, Payroll, PayrollAdjustment, User
from app.security import hash_password


@pytest.fixture(autouse=True)
def clean_database():
    with SessionLocal() as db:
        db.query(Attendance).delete()
        db.query(Holiday).delete()
        db.query(EmployeeDocument).delete()
        db.query(LeaveRequest).delete()
        db.query(LeaveBalance).delete()
        db.query(PayrollAdjustment).delete()
        db.query(Payroll).delete()
        db.query(NotificationLog).delete()
        db.query(AuditLog).delete()
        db.query(LeaveType).delete()
        db.query(Employee).delete()
        db.query(AuthSession).delete()
        db.query(User).delete()
        db.commit()
    yield


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_database():
    yield
    engine.dispose()
    _test_db_path.unlink(missing_ok=True)
    shutil.rmtree(_test_upload_path, ignore_errors=True)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.mark.parametrize("origin", ["http://localhost:5173", "http://127.0.0.1:5173"])
@pytest.mark.parametrize("path", ["/api/auth/refresh", "/api/auth/register"])
def test_auth_preflight_allows_local_frontend_origins(client, origin, path):
    response = client.options(
        path,
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert response.headers["access-control-allow-credentials"] == "true"


def create_user(role="employee", is_active=True):
    password = "SecureDemoPassword123!"
    with SessionLocal() as db:
        user = User(email=f"{uuid.uuid4().hex}@example.com", password_hash=hash_password(password), role=role, is_active=is_active)
        db.add(user)
        db.commit()
        db.refresh(user)
        email = user.email
    return email, password


def login_as(client, role="admin"):
    email, password = create_user(role=role)
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def salary_slip_content_streams(pdf: bytes) -> bytes:
    streams = re.findall(rb"stream\r?\n(.*?)\s*endstream", pdf, re.DOTALL)
    decoded = []
    for stream in streams:
        stream = stream.strip()
        try:
            decoded.append(zlib.decompress(stream))
        except zlib.error:
            for adobe in (False, True):
                try:
                    decoded.append(zlib.decompress(base64.a85decode(stream, adobe=adobe)))
                    break
                except (ValueError, zlib.error):
                    continue
    return b"\n".join(decoded)


def test_login_stores_only_a_hashed_password_and_sets_http_only_refresh_cookie(client):
    email, password = create_user()

    response = client.post("/api/auth/login", json={"email": email, "password": password})

    assert response.status_code == 200
    assert "refresh_token" not in response.json()
    assert response.json()["role"] == "employee"
    cookie = response.headers["set-cookie"].lower()
    assert "hrms_refresh_token=" in cookie
    assert "httponly" in cookie
    assert "samesite=strict" in cookie
    assert "path=/api/auth" in cookie
    with SessionLocal() as db:
        user = db.query(User).filter_by(email=email).one()
        assert user.password_hash != password


def test_public_registration_creates_employee_only_account_and_starts_session(client):
    response = client.post(
        "/api/auth/register",
        json={
            "full_name": "  Vino New Starter  ",
            "email": "Vino.New.Starter@example.com",
            "password": "A-Secure-Vino-Passphrase-2026",
            "role": "admin",
        },
    )

    assert response.status_code == 201, response.text
    assert response.json()["role"] == "employee"
    assert "access_token" in response.json()
    assert "httponly" in response.headers["set-cookie"].lower()
    with SessionLocal() as db:
        user = db.query(User).filter_by(email="vino.new.starter@example.com").one()
        employee = db.query(Employee).filter_by(user_id=user.id).one()
        assert user.role == "employee"
        assert user.password_hash != "A-Secure-Vino-Passphrase-2026"
        assert employee.full_name == "Vino New Starter"
        assert employee.designation == "Employee"
        assert employee.employee_code.startswith("VINO-SELF-")
        assert employee.monthly_salary == Decimal("0.00")

    headers = {"Authorization": f"Bearer {response.json()['access_token']}"}
    assert client.get("/api/employees/me", headers=headers).status_code == 200
    assert client.get("/api/employees", headers=headers).status_code == 403

    duplicate = client.post(
        "/api/auth/register",
        json={
            "full_name": "Another Person",
            "email": "VINO.NEW.STARTER@example.com",
            "password": "Another-Secure-Passphrase-2026",
        },
    )
    assert duplicate.status_code == 409

    weak_password = client.post(
        "/api/auth/register",
        json={
            "full_name": "Short Password",
            "email": f"{uuid.uuid4().hex}@example.com",
            "password": "too-short",
        },
    )
    assert weak_password.status_code == 422


def test_refresh_rotates_token_and_logout_revokes_access(client):
    email, password = create_user(role="hr")
    login_response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert login_response.status_code == 200
    old_refresh = client.cookies.get("hrms_refresh_token")
    assert old_refresh

    refresh_response = client.post("/api/auth/refresh")
    assert refresh_response.status_code == 200
    assert refresh_response.json()["role"] == "hr"
    access_token = refresh_response.json()["access_token"]
    new_refresh = client.cookies.get("hrms_refresh_token")
    assert new_refresh and new_refresh != old_refresh

    stale_client = TestClient(app)
    stale_client.cookies.set("hrms_refresh_token", old_refresh)
    assert stale_client.post("/api/auth/refresh").status_code == 401

    logout_response = client.post("/api/auth/logout")
    assert logout_response.status_code == 200
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {access_token}"}).status_code == 401
    assert client.post("/api/auth/refresh").status_code == 401
    stale_client.close()


def test_employee_token_cannot_access_hr_employee_directory(client):
    email, password = create_user(role="employee")
    login_response = client.post("/api/auth/login", json={"email": email, "password": password})
    token = login_response.json()["access_token"]

    response = client.get("/api/employees", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403
    directory = client.get("/api/employees/directory", headers={"Authorization": f"Bearer {token}"})
    assert directory.status_code == 200
    assert directory.json() == []


def test_employee_can_create_employee_without_gaining_management_access(client):
    token = login_as(client, role="employee")
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "email": f"{uuid.uuid4().hex}@example.com",
        "temporary_password": "NewEmployeePassword123!",
        "employee_code": f"E-{uuid.uuid4().hex[:8]}",
        "full_name": "New Team Member",
        "designation": "Analyst",
        "joining_date": date.today().isoformat(),
        "monthly_salary": "0.00",
        "basic_salary": "0.00",
        "hra": "0.00",
        "special_allowance": "0.00",
    }

    created = client.post("/api/employees", json=payload, headers=headers)

    assert created.status_code == 201, created.text
    assert created.json()["full_name"] == payload["full_name"]
    assert created.json()["role"] == "employee"
    assert client.get("/api/departments", headers=headers).status_code == 200
    assert client.get("/api/employees", headers=headers).status_code == 403
    assert client.get("/api/employees/directory", headers=headers).json()[0]["full_name"] == payload["full_name"]

    new_employee_login = client.post(
        "/api/auth/login",
        json={"email": payload["email"], "password": payload["temporary_password"]},
    )
    assert new_employee_login.status_code == 200
    assert new_employee_login.json()["role"] == "employee"


def test_inactive_user_cannot_login(client):
    email, password = create_user(is_active=False)

    response = client.post("/api/auth/login", json={"email": email, "password": password})

    assert response.status_code == 401
    assert "hrms_refresh_token" not in response.headers.get("set-cookie", "")


def test_swagger_ui_and_openapi_cover_all_api_routes(client):
    docs = client.get("/docs")
    openapi_response = client.get("/openapi.json")
    redoc = client.get("/redoc")

    assert docs.status_code == 200
    assert "swagger-ui" in docs.text.lower()
    assert openapi_response.status_code == 200
    assert redoc.status_code == 200
    assert "redoc" in redoc.text.lower()

    schema = openapi_response.json()
    documented_operations = {
        (path, method.upper())
        for path, path_item in schema["paths"].items()
        for method in path_item
        if method in {"get", "post", "put", "patch", "delete", "options", "head"}
    }
    registered_operations = {
        (route.path, method)
        for route in app.routes
        if isinstance(route, APIRoute) and route.path.startswith("/api/")
        for method in route.methods
    }
    assert registered_operations
    assert registered_operations <= documented_operations

    auth_scheme = next(iter(schema["components"]["securitySchemes"]))
    assert schema["paths"]["/api/auth/register"]["post"].get("security", []) == []
    assert schema["paths"]["/api/health"]["get"].get("security", []) == []
    assert schema["paths"]["/api/employees"]["get"]["security"] == [{auth_scheme: []}]
    assert schema["paths"]["/api/audit-logs"]["get"]["security"] == [{auth_scheme: []}]


def test_employee_crud_and_document_access(client):
    admin_token = login_as(client, role="admin")
    headers = {"Authorization": f"Bearer {admin_token}"}
    with SessionLocal() as db:
        department = Department(name=f"People-{uuid.uuid4().hex[:8]}")
        db.add(department)
        db.commit()
        department_id = department.id

    payload = {
        "email": f"{uuid.uuid4().hex}@example.com",
        "temporary_password": "EmployeePass123!",
        "employee_code": f"E-{uuid.uuid4().hex[:8]}",
        "full_name": "Morgan Employee",
        "department_id": department_id,
        "designation": "Analyst",
        "joining_date": date.today().isoformat(),
        "monthly_salary": "62000.00",
        "phone": "+1 555 0100",
        "date_of_birth": "1994-05-17",
        "address": "  42 Example Street, Sample City  ",
        "emergency_contact_name": "  Jordan Employee  ",
        "emergency_contact_relationship": "  Partner  ",
        "emergency_contact_phone": "  +1 555 0101  ",
    }
    created = client.post("/api/employees", json=payload, headers=headers)
    assert created.status_code == 201
    employee = created.json()
    assert employee["email"] == payload["email"]
    assert employee["role"] == "employee"
    assert employee["department_id"] == department_id
    assert employee["date_of_birth"] == payload["date_of_birth"]
    assert employee["address"] == "42 Example Street, Sample City"
    assert employee["emergency_contact_name"] == "Jordan Employee"
    assert employee["emergency_contact_relationship"] == "Partner"
    assert employee["emergency_contact_phone"] == "+1 555 0101"
    details = client.get(f"/api/employees/{employee['id']}", headers=headers)
    assert details.status_code == 200
    assert details.json()["emergency_contact_phone"] == "+1 555 0101"

    invalid = client.post("/api/employees", json={**payload, "email": f"{uuid.uuid4().hex}@example.com", "employee_code": f"E-{uuid.uuid4().hex[:8]}", "monthly_salary": "-1"}, headers=headers)
    assert invalid.status_code == 422
    future_birth_date = client.post(
        "/api/employees",
        json={**payload, "email": f"{uuid.uuid4().hex}@example.com", "employee_code": f"E-{uuid.uuid4().hex[:8]}", "date_of_birth": "2999-01-01"},
        headers=headers,
    )
    assert future_birth_date.status_code == 422
    missing_department = client.post("/api/employees", json={**payload, "email": f"{uuid.uuid4().hex}@example.com", "employee_code": f"E-{uuid.uuid4().hex[:8]}", "department_id": 999999}, headers=headers)
    assert missing_department.status_code == 422

    updated = client.patch(
        f"/api/employees/{employee['id']}",
        json={
            "designation": "Senior Analyst",
            "monthly_salary": "70000",
            "email": f"updated-{payload['email']}",
            "address": "  7 New Avenue  ",
            "emergency_contact_phone": None,
        },
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["designation"] == "Senior Analyst"
    assert updated.json()["monthly_salary"] == "70000.00"
    assert updated.json()["email"] == f"updated-{payload['email']}"
    assert updated.json()["address"] == "7 New Avenue"
    assert updated.json()["emergency_contact_phone"] is None

    upload = client.post(
        f"/api/employees/{employee['id']}/documents",
        files={"file": ("identity.pdf", b"%PDF-1.4\nemployee document", "application/pdf")},
        headers=headers,
    )
    assert upload.status_code == 201
    spoofed_upload = client.post(
        f"/api/employees/{employee['id']}/documents",
        files={"file": ("spoofed.pdf", b"not a PDF", "application/pdf")},
        headers=headers,
    )
    assert spoofed_upload.status_code == 415
    docs = client.get(f"/api/employees/{employee['id']}/documents", headers=headers)
    assert docs.status_code == 200
    assert len(docs.json()) == 1
    downloaded = client.get(f"/api/employees/{employee['id']}/documents/{docs.json()[0]['id']}", headers=headers)
    assert downloaded.status_code == 200
    assert downloaded.content.startswith(b"%PDF-")

    employee_login = client.post("/api/auth/login", json={"email": updated.json()["email"], "password": payload["temporary_password"]})
    assert employee_login.status_code == 200
    employee_headers = {"Authorization": f"Bearer {employee_login.json()['access_token']}"}
    own_details = client.get(f"/api/employees/{employee['id']}", headers=employee_headers)
    assert own_details.status_code == 200
    assert own_details.json()["date_of_birth"] == payload["date_of_birth"]
    directory = client.get("/api/employees/directory", headers=employee_headers)
    assert directory.status_code == 200
    directory_employee = next(row for row in directory.json() if row["id"] == employee["id"])
    assert directory_employee == {
        "id": employee["id"],
        "employee_code": employee["employee_code"],
        "full_name": employee["full_name"],
        "department_name": employee["department_name"],
        "designation": "Senior Analyst",
        "role": "employee",
        "is_active": True,
    }
    assert client.get(f"/api/employees/{employee['id']}/documents", headers=employee_headers).status_code == 200
    assert client.get(f"/api/employees/{employee['id']}/documents/{docs.json()[0]['id']}", headers=employee_headers).status_code == 200
    own_upload = client.post(
        f"/api/employees/{employee['id']}/documents",
        files={"file": ("proof.png", b"\x89PNG\r\n\x1a\nemployee proof", "image/png")},
        headers=employee_headers,
    )
    assert own_upload.status_code == 201
    assert own_upload.json()["original_name"] == "proof.png"
    other_employee = client.post(
        "/api/employees",
        json={**payload, "email": f"other-{payload['email']}", "employee_code": f"E-{uuid.uuid4().hex[:8]}"},
        headers=headers,
    )
    assert other_employee.status_code == 201
    other_upload = client.post(
        f"/api/employees/{other_employee.json()['id']}/documents",
        files={"file": ("other.pdf", b"%PDF-1.4\nother employee document", "application/pdf")},
        headers=employee_headers,
    )
    assert other_upload.status_code == 403

    assert client.delete(f"/api/employees/{other_employee.json()['id']}", headers=headers).status_code == 204
    assert client.delete(f"/api/employees/{employee['id']}", headers=headers).status_code == 204
    assert client.get("/api/employees", headers=headers).json() == []
    archived = client.get("/api/employees?include_inactive=true", headers=headers)
    assert archived.status_code == 200
    assert next(row for row in archived.json() if row["id"] == employee["id"])["is_active"] is False
    assert client.get("/api/employees/me", headers=employee_headers).status_code == 401
    assert client.post("/api/auth/login", json={"email": updated.json()["email"], "password": payload["temporary_password"]}).status_code == 401


def test_attendance_check_in_out_summary_and_admin_correction(client):
    employee_email, employee_password = create_user(role="employee")
    with SessionLocal() as db:
        employee_user = db.query(User).filter_by(email=employee_email).one()
        employee = Employee(
            user_id=employee_user.id,
            employee_code=f"A-{uuid.uuid4().hex[:8]}",
            full_name="Attendance Employee",
            designation="Engineer",
            joining_date=date.today(),
            monthly_salary=50000,
        )
        db.add(employee)
        db.commit()
        employee_id = employee.id
    employee_login = client.post("/api/auth/login", json={"email": employee_email, "password": employee_password})
    employee_token = employee_login.json()["access_token"]
    employee_headers = {"Authorization": f"Bearer {employee_token}"}

    assert client.post("/api/attendance/check-out", headers=employee_headers).status_code == 409
    check_in = client.post("/api/attendance/check-in", headers=employee_headers)
    assert check_in.status_code == 200
    assert check_in.json()["employee_id"] == employee_id
    assert client.post("/api/attendance/check-in", headers=employee_headers).status_code == 409
    check_out = client.post("/api/attendance/check-out", headers=employee_headers)
    assert check_out.status_code == 200
    assert check_out.json()["working_minutes"] >= 0
    assert client.post("/api/attendance/check-out", headers=employee_headers).status_code == 409

    month = date.today().month
    year = date.today().year
    summary = client.get(f"/api/attendance/me?month={month}&year={year}", headers=employee_headers)
    assert summary.status_code == 200
    assert 0 <= summary.json()["working_days"] <= date.today().day
    assert summary.json()["days_present"] == 0
    assert summary.json()["days_absent"] == 1
    assert len(summary.json()["records"]) == 1
    future_summary = client.get("/api/attendance/me?month=1&year=2100", headers=employee_headers)
    assert future_summary.status_code == 200
    assert future_summary.json()["working_days"] == 0

    admin_token = login_as(client, role="admin")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    hr_token = login_as(client, role="hr")
    hr_headers = {"Authorization": f"Bearer {hr_token}"}
    check_in_time = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(hours=3)
    check_out_time = check_in_time + timedelta(hours=2)
    correction = client.patch(
        f"/api/attendance/{check_in.json()['id']}/correct",
        json={"check_in": check_in_time.isoformat(), "check_out": check_out_time.isoformat(), "status": "half_day", "reason": "Corrected based on manager timesheet"},
        headers=admin_headers,
    )
    assert correction.status_code == 200, correction.text
    assert correction.json()["status"] == "half_day"
    assert correction.json()["working_minutes"] == 120
    assert client.get(f"/api/attendance/me?month={month}&year={year}", headers=employee_headers).json()["days_present"] == 0.5
    events = client.get("/api/audit-logs?action=attendance.check_in", headers=admin_headers)
    assert events.status_code == 200
    assert events.json()[0]["entity_id"] == str(check_in.json()["id"])
    assert client.get("/api/audit-logs", headers=hr_headers).status_code == 403
    assert client.post("/api/audit-logs", headers=admin_headers).status_code == 405
    assert client.delete("/api/audit-logs", headers=admin_headers).status_code == 405
    assert client.put("/api/audit-logs", headers=admin_headers).status_code == 405
    assert client.patch(
        f"/api/attendance/{check_in.json()['id']}/correct",
        json={"status": "present"},
        headers=hr_headers,
    ).status_code == 403
    assert client.patch(
        f"/api/attendance/{check_in.json()['id']}/correct",
        json={"status": "present"},
        headers=admin_headers,
    ).status_code == 422
    invalid_order = client.patch(
        f"/api/attendance/{check_in.json()['id']}/correct",
        json={"check_in": (check_out_time + timedelta(hours=1)).isoformat(), "check_out": check_out_time.isoformat(), "reason": "Corrected based on manager timesheet"},
        headers=admin_headers,
    )
    assert invalid_order.status_code == 422
    assert client.patch(
        f"/api/attendance/{check_in.json()['id']}/correct",
        json={"status": "present"},
        headers=employee_headers,
    ).status_code == 403


def test_leave_approval_balance_lop_payroll_lock_and_credit_simulation(client):
    admin_token = login_as(client, role="admin")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    employee_email, employee_password = create_user(role="employee")
    with SessionLocal() as db:
        employee_user = db.query(User).filter_by(email=employee_email).one()
        employee = Employee(
            user_id=employee_user.id,
            employee_code=f"L-{uuid.uuid4().hex[:8]}",
            full_name="Leave Payroll Employee",
            designation="Designer",
            joining_date=date.today(),
            monthly_salary=3600,
            basic_salary=3000,
            hra=500,
            special_allowance=100,
            pf_percentage=1,
            professional_tax=20,
            tds=10,
        )
        leave_type = LeaveType(name=f"Annual-{uuid.uuid4().hex[:6]}", annual_allowance=2)
        db.add_all([employee, leave_type])
        db.commit()
        employee_id = employee.id
        leave_type_id = leave_type.id
        leave_type_name = leave_type.name

    employee_login = client.post("/api/auth/login", json={"email": employee_email, "password": employee_password})
    employee_headers = {"Authorization": f"Bearer {employee_login.json()['access_token']}"}
    today = date.today()
    leave_start = today + timedelta(days=1)
    leave_end = leave_start + timedelta(days=2)
    if leave_end.month != today.month:
        leave_end = leave_start

    leave_response = client.post(
        "/api/leaves",
        json={"leave_type_id": leave_type_id, "start_date": leave_start.isoformat(), "end_date": leave_end.isoformat(), "reason": "Family commitment"},
        headers=employee_headers,
    )
    assert leave_response.status_code == 201
    assert leave_response.json()["status"] == "pending"
    assert leave_response.json()["leave_type"] == leave_type_name
    pending_queue = client.get("/api/leaves?status=pending", headers=admin_headers)
    assert pending_queue.status_code == 200
    assert any(row["id"] == leave_response.json()["id"] for row in pending_queue.json())
    overlap = client.post(
        "/api/leaves",
        json={"leave_type_id": leave_type_id, "start_date": leave_start.isoformat(), "end_date": leave_end.isoformat(), "reason": "Duplicate request"},
        headers=employee_headers,
    )
    assert overlap.status_code == 409

    hr_token = login_as(client, role="hr")
    hr_headers = {"Authorization": f"Bearer {hr_token}"}
    decision = client.post(f"/api/leaves/{leave_response.json()['id']}/decision", json={"status": "approved"}, headers=hr_headers)
    assert decision.status_code == 200
    assert decision.json()["status"] == "approved"
    assert not any(
        row["id"] == leave_response.json()["id"]
        for row in client.get("/api/leaves?status=pending", headers=admin_headers).json()
    )
    leave_notifications = client.get("/api/notifications/logs", headers=admin_headers)
    assert any(row["event_type"] == "leave_decision" for row in leave_notifications.json())
    leave_audit = client.get(
        "/api/audit-logs",
        params={"action": "leave.approved", "entity_type": "leave_request"},
        headers=admin_headers,
    )
    assert leave_audit.status_code == 200
    assert any(str(row["entity_id"]) == str(leave_response.json()["id"]) for row in leave_audit.json())
    assert client.get("/api/audit-logs", headers=hr_headers).status_code == 403
    assert client.post(f"/api/leaves/{leave_response.json()['id']}/decision", json={"status": "rejected"}, headers=admin_headers).status_code == 409

    rejected_leave_response = client.post(
        "/api/leaves",
        json={
            "leave_type_id": leave_type_id,
            "start_date": (leave_end + timedelta(days=2)).isoformat(),
            "end_date": (leave_end + timedelta(days=2)).isoformat(),
            "reason": "Reject workflow test",
        },
        headers=employee_headers,
    )
    assert rejected_leave_response.status_code == 201
    rejected_leave_id = rejected_leave_response.json()["id"]
    rejection = client.post(
        f"/api/leaves/{rejected_leave_id}/decision",
        json={"status": "rejected", "note": "Test rejection workflow"},
        headers=hr_headers,
    )
    assert rejection.status_code == 200, rejection.text
    assert rejection.json()["status"] == "rejected"
    rejection_notifications = client.get("/api/notifications/logs", headers=admin_headers)
    assert any(
        row["event_type"] == "leave_decision"
        and row["recipient"] == employee_email
        and "rejected" in row["subject"].lower()
        for row in rejection_notifications.json()
    )
    rejection_audit = client.get(
        "/api/audit-logs",
        params={"action": "leave.rejected", "entity_type": "leave_request"},
        headers=admin_headers,
    )
    assert any(str(row["entity_id"]) == str(rejected_leave_id) for row in rejection_audit.json())
    own_history = client.get("/api/leaves/me", headers=employee_headers)
    assert own_history.status_code == 200
    assert next(row for row in own_history.json() if row["id"] == leave_response.json()["id"])["status"] == "approved"
    assert next(row for row in own_history.json() if row["id"] == rejected_leave_id)["status"] == "rejected"
    balances = client.get(f"/api/leaves/balances/me?year={today.year}", headers=employee_headers)
    assert balances.status_code == 200
    assert balances.json()[0]["remaining_days"] == "0.00"

    payroll_end = today.replace(day=1) - timedelta(days=1)
    payroll_month_start = payroll_end.replace(day=1)
    payroll_workdays = [
        payroll_month_start + timedelta(days=offset)
        for offset in range((payroll_end - payroll_month_start).days + 1)
        if (payroll_month_start + timedelta(days=offset)).weekday() < 5
    ]
    holiday = client.post(
        "/api/holidays",
        json={"holiday_date": payroll_workdays[-1].isoformat(), "name": "Company foundation day"},
        headers=admin_headers,
    )
    assert holiday.status_code == 201
    assert client.post(
        "/api/holidays",
        json={"holiday_date": payroll_workdays[-1].isoformat(), "name": "Duplicate holiday"},
        headers=admin_headers,
    ).status_code == 409
    payroll_workdays.remove(payroll_workdays[-1])
    with SessionLocal() as db:
        db.add_all([
            Attendance(employee_id=employee_id, work_date=payroll_workdays[0], status="absent"),
            Attendance(employee_id=employee_id, work_date=payroll_workdays[1], status="half_day"),
        ])
        db.commit()
    generated = client.post("/api/payroll/generate", json={"year": payroll_end.year, "month": payroll_end.month}, headers=hr_headers)
    assert generated.status_code == 200, generated.text
    assert generated.json()["generated_count"] == 1
    payroll = generated.json()["payroll"][0]
    expected_working_days = len(payroll_workdays)
    expected_lop_days = Decimal(expected_working_days) - Decimal("0.5")
    per_day = (Decimal("3600") / Decimal(expected_working_days)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    expected_net = max(
        Decimal("0"),
        Decimal("3600")
        - (per_day * expected_lop_days).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        - Decimal("60"),
    )
    assert payroll["gross_salary"] == "3600.00"
    assert payroll["basic_salary"] == "3000.00"
    assert payroll["hra"] == "500.00"
    assert payroll["special_allowance"] == "100.00"
    assert payroll["pf_deduction"] == "30.00"
    assert payroll["professional_tax"] == "20.00"
    assert payroll["tds_deduction"] == "10.00"
    assert Decimal(payroll["working_days"]) == Decimal(expected_working_days)
    assert Decimal(payroll["payable_days"]) == Decimal("0.50")
    assert Decimal(payroll["lop_days"]) == expected_lop_days
    assert payroll["locked"] is True
    assert Decimal(payroll["net_salary"]) == expected_net
    assert client.post("/api/payroll/generate", json={"year": today.year, "month": today.month}, headers=hr_headers).status_code == 422
    assert client.post("/api/payroll/generate", json={"year": payroll_end.year, "month": payroll_end.month}, headers=hr_headers).json()["generated_count"] == 0

    employee_history = client.get("/api/payroll/me", headers=employee_headers)
    assert employee_history.status_code == 200
    assert len(employee_history.json()) == 1
    assert employee_history.json()[0]["locked"] is True
    employee_slip = client.get(f"/api/payroll/{payroll['id']}/salary-slip.pdf", headers=employee_headers)
    assert employee_slip.status_code == 200
    assert employee_slip.headers["content-type"] == "application/pdf"
    assert employee_slip.content.startswith(b"%PDF")
    assert employee_slip.content.endswith(b"%%EOF\n")
    assert len(employee_slip.content) > 3000
    assert "salary-slip-" in employee_slip.headers["content-disposition"]
    slip_text = salary_slip_content_streams(employee_slip.content)
    for expected in (
        b"Big Stack People",
        b"EMPLOYEE DETAILS",
        b"ATTENDANCE SUMMARY",
        b"WORKING DAYS",
        b"PRESENT DAYS",
        b"PAID LEAVE",
        b"LOP DAYS",
        b"EARNINGS",
        b"DEDUCTIONS",
        b"NET SALARY",
        b"PAYMENT STATUS: AWAITING CREDIT",
        b"Net amount in words:",
        b"0.5",
    ):
        assert expected in slip_text
    assert client.get(f"/api/payroll/{payroll['id']}/salary-slip.pdf", headers=admin_headers).status_code == 200
    assert client.post(
        f"/api/payroll/{payroll['id']}/adjustments",
        json={"amount": "-99999.00", "reason": "Test negative net guard"},
        headers=admin_headers,
    ).status_code == 422
    assert client.post(
        f"/api/payroll/{payroll['id']}/adjustments",
        json={"amount": "125.50", "reason": "Approved travel reimbursement"},
        headers=hr_headers,
    ).status_code == 403
    adjusted = client.post(
        f"/api/payroll/{payroll['id']}/adjustments",
        json={"amount": "125.50", "reason": "Approved travel reimbursement"},
        headers=admin_headers,
    )
    assert adjusted.status_code == 200
    assert Decimal(adjusted.json()["net_salary"]) == expected_net + Decimal("125.50")
    assert adjusted.json()["adjustments"][0]["reason"] == "Approved travel reimbursement"
    adjusted_slip = client.get(
        f"/api/payroll/{payroll['id']}/salary-slip.pdf",
        headers=employee_headers,
    )
    assert adjusted_slip.status_code == 200
    assert adjusted_slip.content.startswith(b"%PDF")
    other_email, _ = create_user(role="employee")
    other_login = client.post("/api/auth/login", json={"email": other_email, "password": "SecureDemoPassword123!"})
    other_token = other_login.json().get("access_token")
    other_headers = {"Authorization": "Bearer " + other_token}
    assert client.get(f"/api/payroll/{payroll['id']}/salary-slip.pdf", headers=other_headers).status_code == 403
    notification_logs = client.get("/api/notifications/logs", headers=admin_headers)
    assert notification_logs.status_code == 200
    assert any(row["event_type"] == "payroll_generated" and row["status"] == "logged" for row in notification_logs.json())
    assert client.get("/api/notifications/logs", headers=employee_headers).status_code == 403
    assert client.post(f"/api/payroll/{payroll['id']}/simulate-credit", headers=hr_headers).status_code == 403
    credit = client.post(f"/api/payroll/{payroll['id']}/simulate-credit", headers=admin_headers)
    assert credit.status_code == 200
    assert credit.json()["simulated_credited"] is True
    assert credit.json()["credit_reference"].startswith("SIM-")
    assert client.post(f"/api/payroll/{payroll['id']}/simulate-credit", headers=admin_headers).status_code == 409
    assert client.post(
        f"/api/payroll/{payroll['id']}/adjustments",
        json={"amount": "25.00", "reason": "Post credit change"},
        headers=admin_headers,
    ).status_code == 409
    dashboard = client.get("/api/dashboard/summary", headers=admin_headers)
    assert dashboard.status_code == 200
    assert "present_today" in dashboard.json()
    assert "pending_leaves" in dashboard.json()
    assert "payroll_net_total_this_month" in dashboard.json()


def test_admin_role_assignment_and_report_exports(client):
    admin_token = login_as(client, role="admin")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    hr_email, _ = create_user(role="hr")
    employee_email, employee_password = create_user(role="employee")
    with SessionLocal() as db:
        hr_user_id = db.query(User).filter_by(email=hr_email).one().id
        employee_user = db.query(User).filter_by(email=employee_email).one()
        department = Department(name=f"Reports-{uuid.uuid4().hex[:6]}")
        db.add(department)
        db.flush()
        employee = Employee(
            user_id=employee_user.id,
            employee_code=f"R-{uuid.uuid4().hex[:8]}",
            full_name="Report Employee",
            department_id=department.id,
            designation="Analyst",
            joining_date=date.today(),
            monthly_salary=4200,
        )
        leave_type = LeaveType(name=f"ReportLeave-{uuid.uuid4().hex[:6]}", annual_allowance=5)
        db.add_all([employee, leave_type])
        db.flush()
        db.add(Attendance(employee_id=employee.id, work_date=date.today(), status="present", working_minutes=480))
        db.add(LeaveRequest(
            employee_id=employee.id,
            leave_type_id=leave_type.id,
            start_date=date.today(),
            end_date=date.today(),
            days=1,
            reason="Report fixture",
            status="approved",
        ))
        db.add(Payroll(
            employee_id=employee.id,
            year=date.today().year,
            month=date.today().month,
            gross_salary=4200,
            lop_days=0,
            lop_deduction=0,
            other_deductions=100,
            net_salary=4100,
            locked=True,
        ))
        department_id = department.id
        db.commit()

    users = client.get("/api/admin/users", headers=admin_headers)
    assert users.status_code == 200
    target = next(user for user in users.json() if user["id"] == hr_user_id)
    assert target["role"] == "hr"
    changed = client.patch(f"/api/admin/users/{hr_user_id}/role", json={"role": "employee"}, headers=admin_headers)
    assert changed.status_code == 200
    assert changed.json()["role"] == "employee"
    admin_user_id = next(user["id"] for user in users.json() if user["role"] == "admin")
    assert client.patch(f"/api/admin/users/{admin_user_id}/role", json={"role": "hr"}, headers=admin_headers).status_code == 409
    assert client.get("/api/admin/roles", headers=admin_headers).json()["roles"]

    date_params = {"start_date": date.today().isoformat(), "end_date": date.today().isoformat(), "department_id": department_id}
    for report in ("attendance", "leaves", "payroll"):
        data_result = client.get(f"/api/reports/{report}/data", params=date_params, headers=admin_headers)
        assert data_result.status_code == 200, data_result.text
        assert data_result.json()["rows"]
        assert "Employee name" in data_result.json()["columns"]
        if report == "payroll":
            assert data_result.json()["columns"] == [
                "Period", "Employee code", "Employee name", "Department", "Gross salary",
                "LOP deduction", "PF", "Professional tax", "TDS", "Adjustments",
                "Net salary", "Status",
            ]
            assert data_result.json()["rows"][0][-1] == "GENERATED"
        csv_result = client.get(f"/api/reports/{report}.csv", params=date_params, headers=admin_headers)
        pdf_result = client.get(f"/api/reports/{report}.pdf", params=date_params, headers=admin_headers)
        assert csv_result.status_code == 200, csv_result.text
        assert "text/csv" in csv_result.headers["content-type"]
        assert pdf_result.status_code == 200
        assert pdf_result.content.startswith(b"%PDF")
        assert b"Report Employee" in csv_result.content

    employee_login = client.post("/api/auth/login", json={"email": employee_email, "password": employee_password})
    employee_headers = {"Authorization": "Bearer " + employee_login.json()["access_token"]}
    assert client.get("/api/reports/payroll/data", params=date_params, headers=employee_headers).status_code == 403
    assert client.get("/api/reports/attendance.csv", params=date_params, headers=employee_headers).status_code == 403
    audit_rows = client.get("/api/audit-logs?action=report.exported&entity_type=report", headers=admin_headers)
    assert audit_rows.status_code == 200
    assert len(audit_rows.json()) == 6
    assert all("start_date=" in row["details"] for row in audit_rows.json())
    assert client.get("/api/audit-logs?start_date=2026-10-31&end_date=2026-10-01", headers=admin_headers).status_code == 422


def test_notification_templates_record_success_and_failure(monkeypatch):
    from app import notifications

    sent_messages = []

    class WorkingSMTP:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def starttls(self, **kwargs):
            pass

        def send_message(self, message):
            sent_messages.append(message)

    class FailingSMTP(WorkingSMTP):
        def send_message(self, message):
            raise smtplib.SMTPException("mail server unavailable")

    monkeypatch.setattr(notifications.settings, "smtp_host", "smtp.example.test")
    monkeypatch.setattr(notifications.settings, "smtp_from_email", "hr@example.test")
    monkeypatch.setattr(notifications.settings, "smtp_starttls", True)
    monkeypatch.setattr(notifications.smtplib, "SMTP", WorkingSMTP)
    with SessionLocal() as db:
        notifications.send_notification(
            db,
            "employee@example.test",
            "payroll_generated",
            period="2026-10",
            net_salary="2850.00",
        )
        monkeypatch.setattr(notifications.smtplib, "SMTP", FailingSMTP)
        notifications.send_notification(
            db,
            "employee@example.test",
            "payroll_credit_simulated",
            period="2026-10",
        )
        db.commit()

    assert sent_messages[0]["Subject"] == "Your 2026-10 salary slip is ready"
    assert "INR 2850.00" in sent_messages[0].get_content()
    with SessionLocal() as db:
        results = db.query(NotificationLog).order_by(NotificationLog.id).all()
        assert [row.status for row in results] == ["sent", "failed"]
