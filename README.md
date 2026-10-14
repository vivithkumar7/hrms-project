# HRMS API

React + FastAPI + SQLAlchemy (SQLite for local development; MySQL is supported for deployment)

An HR management system with role-aware dashboards, employee onboarding, attendance, leave, payroll, reporting, and audit capabilities. See the [dashboard redesign guide](deliverables/HRMS-Redesign-Guide.pdf) for feature descriptions, screenshots, and run instructions. After backend dependencies are installed, regenerate it from the project root with `.\backend\.venv\Scripts\python.exe deliverables\generate_redesign_guide.py`.

## Environment variables

```env
APP_NAME=HRMS API
DATABASE_URL=sqlite:///./hrms.db
JWT_SECRET_KEY=replace-with-a-random-32-plus-character-secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_MINUTES=30
UPLOAD_DIR=uploads
CORS_ORIGINS=http://localhost:5173
```

For a MySQL deployment, use a MySQL 8+ connection string such as:

```env
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/hrms_db?charset=utf8mb4
```

## 1. Database setup
Local development uses SQLite by default and does not require a separate database server. For a MySQL 8+ deployment, create the database and restricted application account using `database/schema-notes.sql`, then set `DATABASE_URL` in `backend/.env` to `mysql+pymysql://hrms_user:URL_ENCODED_PASSWORD@localhost:3306/hrms_db?charset=utf8mb4`. Replace example credentials with your own, URL-encode reserved characters in the password, and never commit `.env` files or production credentials. The application creates its tables on startup; use Alembic migrations for production schema changes.

## 2. Start backend (Windows PowerShell)
```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
# The default .env uses a SQLite DB for local demo use.
# Set JWT_SECRET_KEY to a unique random value of at least 32 characters.
# For example: [Convert]::ToBase64String((1..48 | ForEach-Object { Get-Random -Maximum 256 }))
# If you want MySQL instead, replace DATABASE_URL as well.
# Choose an unused sample admin email and a unique password of at least 12 characters.
$env:HRMS_ADMIN_EMAIL="admin@example.com"
$env:HRMS_ADMIN_PASSWORD="<set-a-unique-password-of-at-least-12-characters>"
python -m app.seed
uvicorn app.main:app --reload
```

## 3. Start backend (macOS/Linux)
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and set JWT_SECRET_KEY to a unique random value of at least 32 characters.
# For example: openssl rand -base64 48
# Choose an unused sample admin email and a unique password of at least 12 characters.
export HRMS_ADMIN_EMAIL=admin@example.com
export HRMS_ADMIN_PASSWORD='<set-a-unique-password-of-at-least-12-characters>'
python -m app.seed
uvicorn app.main:app --reload
```

API docs: http://localhost:8000/docs

## 4a. Run the complete local verification
From PowerShell in the `backend` directory:
```powershell
.\run_live_checks.ps1
```
This runs the backend workflow tests, builds the frontend, starts a short-lived API using an isolated temporary SQLite database, and verifies `/api/health`, Swagger UI (`/docs`), ReDoc (`/redoc`), and the generated OpenAPI operations. It writes the summary to `deliverables/live-test-results.json`, the rendered report to `deliverables/live-test-results.html`, and the API contract to `deliverables/live-openapi.json`. The current run's report and Swagger screenshots are in `deliverables/live-test-results.png` and `deliverables/swagger-ui.png`. It never seeds or mutates the configured HRMS database.

## 5. Start frontend
In a second terminal:
```bash
cd frontend
npm install
npm run dev
```
Open http://localhost:5173. The starter login page uses the seeded admin email by default; type the configured password.
On Windows PowerShell, use `cd frontend; npm install; npm run dev`. Vite defaults to `http://localhost:8000/api`; create `frontend/.env` from `.env.example` only when the API is hosted elsewhere and set `VITE_API_URL` to its `/api` URL.

## Employee onboarding permissions
Authenticated Admin, HR, and Employee accounts can create employee accounts from **Employee Management → Add employee**. New accounts are always assigned the Employee role, and the creator's activity is recorded in the audit log. Employee accounts can still only view the limited employee directory; viewing or managing full employee records and changing roles remains restricted to Admin/HR.

## 6. First-use flow
1. Sign in with the seeded admin or create an Employee account from **Create an account**. Public registration always creates a standard Employee account; Admin/HR must provision department and salary details. Admin/HR employee onboarding remains in **People**.
2. Use **Employee Management** (Admin/HR only) to create, edit, deactivate, or reactivate employee profiles; collect optional date of birth, home address, and emergency contact details; and open **View details** for a separate work, contact, and compensation profile page. Employees can upload and download their own PDF/JPEG/PNG documents (up to 5 MB) from **My Profile**; HR/Admin can manage documents from the employee directory. Document access is authenticated and employees cannot upload to or view another employee's profile. Existing databases receive nullable profile fields automatically on API startup.
3. Employees check in and out from **Attendance**; repeated check-ins/check-outs are rejected. A full day requires 8 hours and a half-day requires at least 4 hours. The month/year selector shows a monthly summary and entries. HR/Admin can review team records; Admin corrections require an audit reason. Admin can maintain the company holiday calendar.
4. Use `POST /api/leave-types` if you need to create leave categories (Annual, Sick, and Casual are seeded).
5. Employees can apply for leave and view their leave and payroll details. HR/Admin reviews leave requests and can generate monthly payroll; Admin can simulate credit.
6. Download salary slips via `GET /api/payroll/{payroll_id}/salary-slip.pdf`.
7. Admins can manage account roles in **Roles & access**. Admin/HR can open **Reports** to export attendance, leave, and payroll reports as CSV or PDF, filtered by dates and department.
8. Admins can inspect immutable-through-the-API activity history in **Audit logs**, filterable by user, action, entity, and date.
9. Import `postman/HRMS.postman_collection.json`; set `adminPassword` to the password chosen during seeding. Employees are provisioned by HR/Admin with a temporary password supplied at creation.

## Important implementation notes
- Key actions use plain-text email templates for onboarding, leave applications/decisions, and payroll. Configure `SMTP_HOST` and `SMTP_FROM_EMAIL` (plus optional paired credentials) in `backend/.env` to enable delivery. `SMTP_STARTTLS` defaults to true; set it false only for a mail server on a trusted network that does not support STARTTLS. Delivery outcomes (`sent`, `failed`, or `logged` when SMTP is not configured) are available through the admin/HR Notifications page and `GET /api/notifications/logs`.
- Employees can download their own monthly PDF salary slips from Pay history. Admin/HR can download all generated salary slips from Payroll overview; each statement has a branded header, employee and payroll references, itemized salary components, deductions and adjustments, net pay in figures and words, a simulated-credit reference when applicable, and confidentiality footer.
- The Big Stack login page offers public Employee registration with hashed passwords and immediate sign-in. Add production rate limiting, email verification, and organization invite controls before exposing public registration on the internet.
- Admins may add signed, reason-required adjustments to locked payroll records before credit simulation. Positive adjustments increase net pay, negative adjustments reduce it, and the adjustment ledger is included in salary slips and payroll exports. Adjustments are audited; credited records cannot be changed. The Admin **Roles & access** panel assigns the built-in Admin, HR, and Employee permission sets. Fine-grained custom permission editing is not supported.
- Admin/HR report exports are available at `/api/reports/{attendance|leaves|payroll}.{csv|pdf}` with required `start_date` and `end_date` parameters and optional `department_id`. Leave reports include requests overlapping the selected range; payroll reports include pay periods overlapping that range.
- Successful admin/HR logins, employee lifecycle and document actions, attendance check-ins/check-outs/corrections, leave submissions and decisions, payroll generation/adjustments/credit simulation, salary-slip downloads, and report exports are recorded in `audit_logs`. The read-only Admin UI and `GET /api/audit-logs` support actor/action/entity/date filters and pagination. Keep database-level write access restricted to the application service and trusted operators; API read-only access alone is not tamper-proof against database administrators.
- Payroll can only be generated for a completed month. Working days are Monday through Friday excluding the Admin-managed holiday calendar. Payable days are recorded present days, half-days at 0.5, and approved paid leave within the annual leave-type allowance; unrecorded scheduled workdays and unpaid/over-allowance leave count as LOP. The LOP deduction is gross monthly salary divided by working days, multiplied by LOP days. PF is calculated from basic salary using the employee's configured percentage; professional tax and TDS are deducted as configured. Salary components and all deductions are snapshotted on locked payroll records. Configure salary components so basic salary, HRA, and special allowance sum to monthly gross salary. Simulated credit does not transfer funds.
- Access tokens expire after 30 minutes and are held in browser memory. Refresh tokens are stored only in HttpOnly, SameSite cookies, rotated on refresh, and revoked on sign-out. Set a unique `JWT_SECRET_KEY` (at least 32 characters) and set `REFRESH_COOKIE_SECURE=true` when serving over HTTPS. Cookie-based authentication requires explicit CORS origins; do not use `*`.
- File uploads allow PDF/JPEG/PNG up to 5 MB, stored under `backend/uploads`. Production should store uploads outside the web root, scan files, and serve them through authenticated endpoints.
- `Base.metadata.create_all` is convenient for a demo. Use Alembic migrations in production.
- `database/hrms-schema.sql` is a generated MySQL schema-only dump; it deliberately contains no application rows. Regenerate it after model changes with `python export_schema.py` from the `backend` directory. A data dump must be created separately from the intended environment after obtaining appropriate authorization and protecting the resulting sensitive file.
- `deliverables/sample-salary-slip.pdf` is a professionally formatted illustrative sample with fictional values; it is not a real payroll record. Regenerate it from the `backend` directory with `python export_sample_salary_slip.py`.
- `deliverables/admin-dashboard.png` and `deliverables/employee-dashboard.png` are screenshots captured from the running portal using an isolated database populated only with fictional showcase records.
- `deliverables/live-test-results.png` and `deliverables/swagger-ui.png` show the latest automated verification summary and Swagger UI. The repeatable runner is `backend/run_live_checks.ps1`; it also saves JSON/HTML results and the OpenAPI schema.
- Example account identifier: `admin@example.com`; there is no hard-coded sample password. Set `HRMS_ADMIN_PASSWORD` before seeding. Employee credentials are the email and temporary password supplied when HR/Admin creates that employee. Do not reuse development credentials in a deployment.
- Review every API permission and test edge cases before deployment. Use HTTPS, secret management, rate limiting, backups, and proper audit retention in production.
- Leave application, employee leave history and balances, HR/Admin review, payroll generation, payroll history, and Admin-only credit simulation are available in the portal. Leave types are configured through the API; richer department administration remains follow-up work.

## Deliverables checklist
- [x] Backend/frontend source starter
- [x] MySQL schema bootstrap notes
- [x] Postman starter collection
- [x] Run locally and add Admin/Employee dashboard screenshots
- [ ] Export a real salary slip PDF from a generated payroll record
- [ ] Create and verify a database dump after migrations and sample data
- [x] Add refresh-token rotation/revocation and focused authentication tests
- [ ] Configure SMTP delivery, confirm organization-specific payroll/leave policies, and expand edge-case coverage for remaining HR workflows
- [x] Add read-only audit-log viewing and activity tracking for critical workflows
- [x] Add generated schema-only SQL dump and tokenized Postman login variables
- [x] Add a fictional sample salary-slip PDF
- [x] Document safe local Admin, HR, and Employee test-account setup in [sample-test-credentials.md](deliverables/sample-test-credentials.md)
- [ ] Publish repository and attach a real-environment payslip
