import json
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    Image as ReportImage,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
DELIVERABLES = ROOT / "deliverables"
ASSETS = DELIVERABLES / "hrms-project-report-assets"
OUTPUT = DELIVERABLES / "HRMS-Project-Report.pdf"
TEST_RESULTS = DELIVERABLES / "live-test-results.json"

INK = colors.HexColor("#172F3D")
TEAL = colors.HexColor("#087F73")
MINT = colors.HexColor("#E9F5F2")
PALE = colors.HexColor("#F2F5F7")
MUTED = colors.HexColor("#61717D")
LINE = colors.HexColor("#D6E0E5")
WHITE = colors.white


def image(path: Path, max_width: float, max_height: float) -> ReportImage:
    width, height = ImageReader(str(path)).getSize()
    scale = min(max_width / width, max_height / height)
    return ReportImage(str(path), width=width * scale, height=height * scale)


def chrome(canvas, doc) -> None:
    canvas.saveState()
    page_width, page_height = letter
    canvas.setFillColor(INK)
    canvas.rect(0, page_height - 0.16 * inch, page_width, 0.16 * inch, fill=1, stroke=0)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(0.65 * inch, 0.36 * inch, "BIG STACK PEOPLE  |  HRMS PROJECT REPORT")
    canvas.drawRightString(page_width - 0.65 * inch, 0.36 * inch, f"{doc.page} / 10")
    canvas.restoreState()


def make_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="CoverTitle", parent=styles["Title"], fontName="Helvetica-Bold",
        fontSize=27, leading=32, textColor=INK, alignment=TA_CENTER, spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        name="Lead", parent=styles["Normal"], fontSize=10.5, leading=15,
        textColor=MUTED, alignment=TA_CENTER, spaceAfter=12,
    ))
    styles.add(ParagraphStyle(
        name="Section", parent=styles["Heading1"], fontName="Helvetica-Bold",
        fontSize=20, leading=24, textColor=INK, spaceBefore=2, spaceAfter=9,
    ))
    styles.add(ParagraphStyle(
        name="Subhead", parent=styles["Heading2"], fontName="Helvetica-Bold",
        fontSize=11.5, leading=14, textColor=TEAL, spaceBefore=6, spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name="Copy", parent=styles["BodyText"], fontSize=9, leading=13,
        textColor=INK, spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name="Small", parent=styles["BodyText"], fontSize=7.7, leading=10,
        textColor=MUTED, spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name="TableHead", parent=styles["BodyText"], fontName="Helvetica-Bold",
        fontSize=8, leading=10, textColor=WHITE,
    ))
    styles.add(ParagraphStyle(
        name="TableCell", parent=styles["BodyText"], fontSize=8, leading=10.5,
        textColor=INK,
    ))
    styles.add(ParagraphStyle(
        name="CodeBlock", parent=styles["Code"], fontName="Courier",
        fontSize=7.4, leading=10, textColor=INK, backColor=PALE,
        borderPadding=7, spaceAfter=7,
    ))
    return styles


def grid(rows, widths, header=True):
    table = Table(rows, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    commands = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 0.35, LINE),
    ]
    if header:
        commands.extend([
            ("BACKGROUND", (0, 0), (-1, 0), INK),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ])
    if len(rows) > 1:
        commands.append(("ROWBACKGROUNDS", (0, 1 if header else 0), (-1, -1), [WHITE, PALE]))
    table.setStyle(TableStyle(commands))
    return table


def para(text, style):
    return Paragraph(text, style)


def caption(text, styles):
    return Paragraph(text, styles["Small"])


def main() -> None:
    test_results = json.loads(TEST_RESULTS.read_text(encoding="utf-8"))
    styles = make_styles()
    body_width = 6.95 * inch
    story = []

    # Page 1 — title and product overview
    story.extend([
        Spacer(1, 0.24 * inch),
        para("Human Resource<br/>Management System", styles["CoverTitle"]),
        para(
            "Project report · local application walkthrough · feature, API, and test evidence",
            styles["Lead"],
        ),
        grid([[
            para(
                "<b>One role-aware workspace for people operations</b><br/>"
                "Employee onboarding, attendance, leave, payroll, salary slips, reports, "
                "notifications, and audit history.",
                styles["Copy"],
            )
        ]], [body_width], header=False),
        Spacer(1, 0.14 * inch),
        image(ASSETS / "dashboard-evidence.png", body_width, 4.55 * inch),
        caption(
            "Output screenshot 1 — dashboard captured from the locally running app. "
            "This browser session is signed in as Employee; values are local demo data.",
            styles,
        ),
        Spacer(1, 0.05 * inch),
        grid([
            [para("<b>Frontend</b><br/>React · Vite", styles["TableCell"]),
             para("<b>Backend</b><br/>FastAPI · SQLAlchemy", styles["TableCell"]),
             para("<b>Validation</b><br/>16 tests · build PASS", styles["TableCell"])],
        ], [body_width / 3] * 3, header=False),
        PageBreak(),
    ])

    # Page 2 — scope and architecture
    story.extend([
        para("1. Scope and system architecture", styles["Section"]),
        para(
            "The HRMS provides separate experiences for employees and people-operations "
            "staff. The dashboard links to focused modules rather than placing every task "
            "on one screen. Backend permissions remain the authority for protected actions.",
            styles["Copy"],
        ),
        para("Implemented modules", styles["Subhead"]),
        grid([
            [para("Area", styles["TableHead"]), para("Primary capability", styles["TableHead"])],
            [para("Identity", styles["TableCell"]), para("JWT sign-in, role-aware navigation, account and role controls.", styles["TableCell"])],
            [para("People", styles["TableCell"]), para("Employee onboarding, profile fields, directory, document upload and access.", styles["TableCell"])],
            [para("Work time", styles["TableCell"]), para("Check-in/out, history, monthly totals, leave requests and decisions.", styles["TableCell"])],
            [para("Compensation", styles["TableCell"]), para("Payroll generation, deductions/adjustments, PDF salary slips and exports.", styles["TableCell"])],
            [para("Operations", styles["TableCell"]), para("Notifications, audit events, dashboards and filtered reports.", styles["TableCell"])],
        ], [1.25 * inch, body_width - 1.25 * inch]),
        para("Request path", styles["Subhead"]),
        grid([
            [para("Browser", styles["TableHead"]), para("API", styles["TableHead"]), para("Persistence", styles["TableHead"])],
            [para("React routes and forms call the API using the signed-in session.", styles["TableCell"]),
             para("FastAPI validates inputs, JWT identity, role permissions, and workflow rules.", styles["TableCell"]),
             para("SQLAlchemy persists records; local development defaults to SQLite, with MySQL supported.", styles["TableCell"])],
        ], [body_width * .31, body_width * .37, body_width * .32]),
        Spacer(1, 0.1 * inch),
        para(
            "<b>Stack:</b> React 18, React Router, Vite, Bootstrap, Axios, FastAPI, "
            "SQLAlchemy, Pydantic settings, JWT, SQLite for local development, and MySQL 8+ "
            "through PyMySQL.",
            styles["Copy"],
        ),
        para(
            "This report documents the local application only. It does not claim that the "
            "system has been deployed to a public or production environment.",
            styles["Small"],
        ),
        PageBreak(),
    ])

    # Page 3 — authentication and RBAC
    story.extend([
        para("2. Authentication and role permissions", styles["Section"]),
        para(
            "Users authenticate through the login endpoint and receive a signed bearer "
            "token. Protected API routes resolve the current user and check role and ownership "
            "before allowing access. Frontend route hiding improves usability but is not the "
            "security boundary.",
            styles["Copy"],
        ),
        grid([
            [para("Role", styles["TableHead"]), para("Typical access", styles["TableHead"]), para("Restricted actions", styles["TableHead"])],
            [para("Admin", styles["TableCell"]), para("Organization-wide users, employee records, payroll, reports, settings, audit logs.", styles["TableCell"]), para("Sensitive changes are permission-checked and recorded.", styles["TableCell"])],
            [para("HR", styles["TableCell"]), para("Employee operations, attendance review, leave decisions, payroll and reports as authorized.", styles["TableCell"]), para("Admin-only role/configuration and audit surfaces remain restricted.", styles["TableCell"])],
            [para("Employee", styles["TableCell"]), para("Own profile, documents, attendance, leave, pay history, and personal reports.", styles["TableCell"]), para("Cannot approve/reject leave or access another employee's private records.", styles["TableCell"])],
        ], [0.8 * inch, 3.2 * inch, body_width - 4 * inch]),
        para("Security controls", styles["Subhead"]),
        para(
            "• Passwords are stored as hashes; JWT signing uses a configured secret.<br/>"
            "• Protected API operations require bearer authentication; the live OpenAPI "
            "contract lists the protected routes.<br/>"
            "• Employee document access is authenticated and ownership-scoped; accepted "
            "document formats and size are restricted by the app.<br/>"
            "• Leave decisions, sensitive payroll actions, and administrative events are "
            "permission-gated and covered by workflow tests.",
            styles["Copy"],
        ),
        para(
            "Configure a unique JWT secret and local passwords before use. The report and "
            "Postman collection intentionally contain no active passwords or access tokens.",
            styles["Small"],
        ),
        PageBreak(),
    ])

    # Page 4 — employee management
    story.extend([
        para("3. Employee management", styles["Section"]),
        para(
            "Employee Management supports a searchable directory and onboarding/profile "
            "workflows. Authorized HR/Admin users manage full employee records; employee "
            "accounts are restricted to their own private profile and documents.",
            styles["Copy"],
        ),
        para("Workflow", styles["Subhead"]),
        para(
            "1. HR/Admin opens the employee directory and creates an employee account with "
            "work and department information.<br/>"
            "2. Profile details can include contact, address, emergency contact, designation, "
            "employment status, and compensation fields.<br/>"
            "3. The employee signs in to review their own profile and upload permitted PDF, "
            "JPEG, or PNG documents (up to 5 MB).<br/>"
            "4. Document access and employee changes are authenticated; administrative "
            "activity is available in audit history.",
            styles["Copy"],
        ),
        image(ASSETS / "employees-evidence.png", body_width, 3.75 * inch),
        caption(
            "Output screenshot 2 — employee directory view from the current local Employee "
            "session. The full management actions remain HR/Admin-only.",
            styles,
        ),
        PageBreak(),
    ])

    # Page 5 — attendance and leave
    story.extend([
        para("4. Attendance and leave workflows", styles["Section"]),
        para("Attendance", styles["Subhead"]),
        para(
            "Employees check in and check out from the attendance page. The app rejects "
            "duplicate transitions, presents daily history, and summarizes monthly working "
            "days and hours. HR/Admin can review authorized team data; privileged corrections "
            "are audited.",
            styles["Copy"],
        ),
        image(ASSETS / "attendance-evidence.png", body_width, 2.35 * inch),
        para("Leave", styles["Subhead"]),
        para(
            "Employees submit a leave type, date range, and reason, then follow its pending, "
            "approved, or rejected state and balance. HR/Admin reviews the queue and records "
            "the decision. Approved leave affects the available balance and payroll loss-of-pay "
            "calculation where applicable.",
            styles["Copy"],
        ),
        image(ASSETS / "leave-evidence.png", body_width, 2.0 * inch),
        caption(
            "Output screenshots 3–4 — attendance and leave pages. These are employee-view "
            "captures; they do not show the HR/Admin approval queue.",
            styles,
        ),
        PageBreak(),
    ])

    # Page 6 — payroll and salary slips
    story.extend([
        para("5. Payroll and PDF salary slips", styles["Section"]),
        para(
            "Payroll generation calculates period earnings and deductions from configured "
            "salary data, attendance, approved leave, loss-of-pay, and recorded adjustments. "
            "Payroll history is available to the employee for their own records and to "
            "authorized HR/Admin users for team processing.",
            styles["Copy"],
        ),
        grid([
            [para("Slip section", styles["TableHead"]), para("Included information", styles["TableHead"])],
            [para("Identity and period", styles["TableCell"]), para("Employee/payroll reference and the salary month.", styles["TableCell"])],
            [para("Earnings/deductions", styles["TableCell"]), para("Itemized salary components, deductions, LOP, and applicable adjustments.", styles["TableCell"])],
            [para("Net payment", styles["TableCell"]), para("Net amount, amount in words, payment/simulation reference when applicable.", styles["TableCell"])],
            [para("Privacy", styles["TableCell"]), para("Confidentiality footer; PDF download requires the relevant authorization.", styles["TableCell"])],
        ], [1.7 * inch, body_width - 1.7 * inch]),
        Spacer(1, 0.08 * inch),
        image(ASSETS / "payroll-evidence.png", body_width, 2.45 * inch),
        caption(
            "Output screenshot 5 — employee payroll page. The selected month has no generated "
            "records in this session; the fictional sample statement is provided separately.",
            styles,
        ),
        para(
            "<b>Sample statement:</b> deliverables/sample-salary-slip.pdf (fictional demo "
            "record; not a real payroll statement).",
            styles["Copy"],
        ),
        PageBreak(),
    ])

    # Page 7 — notifications and audit
    story.extend([
        para("6. Notifications and audit history", styles["Section"]),
        para(
            "The Notifications page presents leave request status to employees and workflow "
            "notifications/logs to authorized HR/Admin staff. Approve and Reject actions belong "
            "to the HR/Admin review queue; they are not employee self-service actions.",
            styles["Copy"],
        ),
        image(ASSETS / "notifications-evidence.png", body_width, 3.6 * inch),
        caption(
            "Output screenshot 6 — employee-facing leave status view from the local browser. "
            "The visible Approve/Reject buttons are disabled for this Employee account. The "
            "HR/Admin review queue and Admin-only audit records were not captured in this session.",
            styles,
        ),
        para("Audit trail", styles["Subhead"]),
        para(
            "Administrative activity records identify the actor, action, affected entity, and "
            "time. Audit history is Admin-only. Email delivery outcomes can be reviewed in the "
            "authorized notification logs; SMTP must be configured for actual email delivery.",
            styles["Copy"],
        ),
        para(
            "Verification includes allow/deny role checks for leave decisions and checks that "
            "decisions result in the expected request status, notification, and audit event.",
            styles["Small"],
        ),
        PageBreak(),
    ])

    # Page 8 — reports
    story.extend([
        para("7. Reports and analytics", styles["Section"]),
        para(
            "Reports & Analytics groups Attendance, Leave, and Payroll summary views with "
            "date filtering and report/export actions. Employees receive personal data only; "
            "company-wide report access is limited to authorized roles.",
            styles["Copy"],
        ),
        image(ASSETS / "reports-evidence.png", body_width, 3.7 * inch),
        caption(
            "Output screenshot 7 — local Reports & Analytics page, captured in Employee "
            "context. The visible payroll summary is empty for the selected range; it is not "
            "an Admin/HR organization-wide report.",
            styles,
        ),
        para("Report paths", styles["Subhead"]),
        para(
            "The API provides date-filtered report data and downloadable CSV/PDF outputs for "
            "authorized users. Report scope is enforced server-side. Filters support selected "
            "dates and, where authorized, department-level review.",
            styles["Copy"],
        ),
        PageBreak(),
    ])

    # Page 9 — API and validation
    backend = test_results["backend_tests"]
    frontend = test_results["frontend_build"]
    live_api = test_results["live_api"]
    story.extend([
        para("8. API integration and verification", styles["Section"]),
        para(
            "The frontend integrates with the FastAPI backend for authentication, dashboards, "
            "employee data, attendance, leave, payroll, reports, notifications, and audit "
            "operations. OpenAPI provides the machine-readable contract and Swagger/ReDoc "
            "provide local interactive documentation.",
            styles["Copy"],
        ),
        grid([
            [para("Check", styles["TableHead"]), para("Latest local result", styles["TableHead"])],
            [para("Backend tests", styles["TableCell"]), para(backend["summary"], styles["TableCell"])],
            [para("Frontend production build", styles["TableCell"]), para(frontend["summary"], styles["TableCell"])],
            [para("Health endpoint", styles["TableCell"]), para(f'{live_api["health"]} (HTTP {live_api["swagger_ui_http"]} docs UI)', styles["TableCell"])],
            [para("API contract", styles["TableCell"]), para(f'{live_api["documented_api_paths"]} paths; {live_api["documented_api_operations"]} operations; {live_api["bearer_protected_operations"]} bearer-protected operations.', styles["TableCell"])],
        ], [2.05 * inch, body_width - 2.05 * inch]),
        Spacer(1, 0.1 * inch),
        para("Quality notes", styles["Subhead"]),
        para(
            "The complete local check runs backend workflow tests, the frontend production "
            "build, and live health/docs/OpenAPI checks. It uses a disposable SQLite database "
            "and fictional test records; it does not alter the configured HRMS database. "
            "The latest run completed with an overall PASS.",
            styles["Copy"],
        ),
        para(
            f'Run timestamp: {test_results["generated_at"]}. One warning is reported by the '
            "test runner; it did not fail the suite.",
            styles["Small"],
        ),
        PageBreak(),
    ])

    # Page 10 — local run and deliverables
    story.extend([
        para("9. Local setup and handover", styles["Section"]),
        para("Start locally (Windows PowerShell)", styles["Subhead"]),
        para(
            "Use the existing local Python environment and configure a unique JWT secret and "
            "Admin password. Keep `.env` and passwords out of source control.",
            styles["Copy"],
        ),
        para(
            "cd backend<br/>"
            r".\.venv\Scripts\Activate.ps1<br/>"
            "Copy-Item .env.example .env<br/>"
            "# Set a unique JWT_SECRET_KEY and local Admin credentials<br/>"
            "python -m app.seed<br/>"
            "uvicorn app.main:app --reload",
            styles["CodeBlock"],
        ),
        para("In a second terminal:", styles["Copy"]),
        para(
            "cd frontend<br/>"
            "npm install<br/>"
            "npm run dev",
            styles["CodeBlock"],
        ),
        para(
            "Open http://localhost:5173; API docs are available at http://localhost:8000/docs. "
            "For repeatable verification, run `backend\\run_live_checks.ps1` from PowerShell "
            "inside the backend directory.",
            styles["Copy"],
        ),
        para("Project deliverables", styles["Subhead"]),
        para(
            "• Database schema: database/hrms-schema.sql; setup notes: database/schema-notes.sql.<br/>"
            "• API collection: postman/HRMS.postman_collection.json. Set local environment "
            "variables for credentials before running it.<br/>"
            "• Sample salary slip: deliverables/sample-salary-slip.pdf; fictional data only.<br/>"
            "• Safe credential provisioning: deliverables/sample-test-credentials.md "
            "(no active passwords).<br/>"
            "• Test report and machine-readable contract: deliverables/live-test-results.json "
            "and deliverables/live-openapi.json.<br/>"
            "• UI evidence: deliverables/hrms-project-report-assets/.",
            styles["Copy"],
        ),
        para(
            "Admin/HR-only approval/audit views require signing in locally with an appropriately "
            "provisioned role. This report uses Employee-session screenshots and does not "
            "include credentials or claim a public deployment.",
            styles["Small"],
        ),
    ])

    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=letter,
        leftMargin=0.65 * inch,
        rightMargin=0.65 * inch,
        topMargin=0.48 * inch,
        bottomMargin=0.58 * inch,
        title="HRMS Project Report",
        author="Big Stack People",
        subject="Ten-page local HRMS feature, output, and validation report",
    )
    doc.build(story, onFirstPage=chrome, onLaterPages=chrome)
    print(f"Created {OUTPUT} at {datetime.now().isoformat(timespec='seconds')}")


if __name__ == "__main__":
    main()
