from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
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
OUTPUT = ROOT / "deliverables" / "HRMS-Redesign-Guide.pdf"
TOP_CROP = ROOT / "deliverables" / "dashboard-overview-crop.png"
LOWER_CROP = ROOT / "deliverables" / "dashboard-insights-crop.png"

INK = colors.HexColor("#10252d")
TEAL = colors.HexColor("#0b8078")
MINT = colors.HexColor("#e7f5f2")
MIST = colors.HexColor("#f3f6f8")
MUTED = colors.HexColor("#60717d")
WHITE = colors.white


def fitted_image(path: Path, max_width: float, max_height: float) -> ReportImage:
    width, height = ImageReader(str(path)).getSize()
    scale = min(max_width / width, max_height / height)
    return ReportImage(str(path), width=width * scale, height=height * scale)


def page_chrome(canvas, doc) -> None:
    canvas.saveState()
    page_width, page_height = letter
    canvas.setFillColor(INK)
    canvas.rect(0, page_height - 0.17 * inch, page_width, 0.17 * inch, fill=1, stroke=0)
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(0.65 * inch, 0.38 * inch, "HRMS  |  Dashboard redesign guide")
    canvas.drawRightString(page_width - 0.65 * inch, 0.38 * inch, f"{doc.page}")
    canvas.restoreState()


def main() -> None:
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="CoverTitle", parent=styles["Title"], fontName="Helvetica-Bold",
        fontSize=29, leading=34, textColor=INK, alignment=TA_CENTER, spaceAfter=10,
    ))
    styles.add(ParagraphStyle(
        name="Lead", parent=styles["Normal"], fontSize=11, leading=17,
        textColor=MUTED, alignment=TA_CENTER, spaceAfter=16,
    ))
    styles.add(ParagraphStyle(
        name="Section", parent=styles["Heading1"], fontName="Helvetica-Bold",
        fontSize=20, leading=25, textColor=INK, spaceBefore=4, spaceAfter=10,
    ))
    styles.add(ParagraphStyle(
        name="Subhead", parent=styles["Heading2"], fontName="Helvetica-Bold",
        fontSize=12, leading=16, textColor=TEAL, spaceBefore=8, spaceAfter=5,
    ))
    styles.add(ParagraphStyle(
        name="BodyCopy", parent=styles["BodyText"], fontSize=9.5,
        leading=14, textColor=INK, spaceAfter=7,
    ))
    styles.add(ParagraphStyle(
        name="SmallCopy", parent=styles["BodyText"], fontSize=8,
        leading=11, textColor=MUTED, spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name="CodeCopy", parent=styles["Code"], fontName="Courier",
        fontSize=7.5, leading=10, textColor=INK, backColor=MIST,
        borderPadding=7, spaceAfter=8,
    ))

    doc = SimpleDocTemplate(
        str(OUTPUT), pagesize=letter,
        rightMargin=0.7 * inch, leftMargin=0.7 * inch,
        topMargin=0.52 * inch, bottomMargin=0.65 * inch,
        title="HRMS Dashboard Redesign Guide",
        author="HRMS project",
    )
    story = [
        Spacer(1, 0.36 * inch),
        Paragraph("HRMS Dashboard<br/>Redesign Guide", styles["CoverTitle"]),
        Paragraph(
            "A practical overview of the role-aware workspace, employee self-service, "
            "technology stack, and local setup.",
            styles["Lead"],
        ),
        Table(
            [[Paragraph(
                "<b>One workspace for people operations</b><br/>"
                "Role-aware navigation keeps each task in its own page while the dashboard "
                "summarizes the most useful live information.",
                styles["BodyCopy"],
            )]],
            colWidths=[6.9 * inch],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), MINT),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#c8e6e1")),
                ("LEFTPADDING", (0, 0), (-1, -1), 14),
                ("RIGHTPADDING", (0, 0), (-1, -1), 14),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]),
        ),
        Spacer(1, 0.18 * inch),
        Paragraph("Role-based workspace", styles["Subhead"]),
        Paragraph(
            "<b>Admin</b> manages people, departments, attendance, leave, payroll, reports, "
            "roles, audit history, and organization settings. <b>HR</b> has the assigned people "
            "operations, payroll, and reporting functions. <b>Employee</b> can view their own "
            "profile, attendance, time off, and salary slips.",
            styles["BodyCopy"],
        ),
        Paragraph("Technology", styles["Subhead"]),
        Paragraph(
            "React 18, React Router, Vite, Bootstrap, Axios, FastAPI, SQLAlchemy, "
            "Pydantic Settings, JWT authentication, SQLite for local development, and "
            "MySQL 8+ through the PyMySQL SQLAlchemy driver.",
            styles["BodyCopy"],
        ),
        Paragraph(
            "The screenshots in this guide are genuine captures of the authenticated "
            "Employee workspace. Admin/HR-only screens are described below but are not "
            "shown because an authorized Admin/HR browser session was not available.",
            styles["SmallCopy"],
        ),
        PageBreak(),
        Paragraph("Dashboard at a glance", styles["Section"]),
        Paragraph(
            "The dashboard brings daily attendance, the monthly snapshot, a seven-day "
            "attendance chart, leave balances, and quick links into one responsive page. "
            "Values are loaded from the authenticated API rather than fixed dashboard copy.",
            styles["BodyCopy"],
        ),
        fitted_image(TOP_CROP, 6.8 * inch, 6.1 * inch),
        Spacer(1, 5),
        Paragraph(
            "Screenshot excerpt: employee dashboard header, attendance status, and monthly summary.",
            styles["SmallCopy"],
        ),
        PageBreak(),
        Paragraph("Insights and separate modules", styles["Section"]),
        Paragraph(
            "The dashboard's lower section keeps the attendance chart, leave balance, and "
            "quick actions together without embedding the full management modules in the overview.",
            styles["BodyCopy"],
        ),
        fitted_image(LOWER_CROP, 6.8 * inch, 5.6 * inch),
        Spacer(1, 7),
        Paragraph(
            "<b>Dedicated pages:</b> Employee Management supports directory search, department "
            "filtering, pagination, add/edit forms, and detailed work/contact/compensation "
            "profiles with optional date of birth, address, and emergency-contact fields; "
            "Attendance provides month/year filtering and records; "
            "Leave shows balances and request history; Payroll presents personal salary-slip "
            "history or authorized team payroll. Departments, Reports, Notifications, User "
            "Management, Audit Logs, Settings, and My Profile each have separate routes.",
            styles["BodyCopy"],
        ),
        Paragraph(
            "HR/Admin page access is additionally enforced by the FastAPI API permissions. "
            "Frontend role-based navigation and route guards are a usability layer, not the "
            "security boundary.",
            styles["SmallCopy"],
        ),
        PageBreak(),
        Paragraph("Run locally", styles["Section"]),
        Paragraph("1. Backend (PowerShell)", styles["Subhead"]),
        Paragraph(
            "Run from the project root. Configure a unique JWT secret and admin password "
            "locally; never use the example placeholders as production credentials.",
            styles["BodyCopy"],
        ),
        Paragraph(
            "cd backend<br/>"
            "py -m venv .venv<br/>"
            r".\.venv\Scripts\Activate.ps1<br/>"
            "pip install -r requirements.txt<br/>"
            "Copy-Item .env.example .env<br/>"
            "# Edit backend/.env: set a unique JWT_SECRET_KEY (32+ characters)<br/>"
            '$env:HRMS_ADMIN_EMAIL="admin@example.com"<br/>'
            '$env:HRMS_ADMIN_PASSWORD="&lt;your-unique-password&gt;"<br/>'
            "python -m app.seed<br/>"
            "uvicorn app.main:app --reload",
            styles["CodeCopy"],
        ),
        Paragraph("2. Frontend (second PowerShell terminal)", styles["Subhead"]),
        Paragraph(
            "cd frontend<br/>"
            "npm install<br/>"
            "npm run dev",
            styles["CodeCopy"],
        ),
        Paragraph(
            "Open http://localhost:5173. The API defaults to http://localhost:8000/api. "
            "For MySQL 8+, create the database/user with database/schema-notes.sql and set "
            "DATABASE_URL in backend/.env to a mysql+pymysql:// connection URL. URL-encode "
            "reserved password characters. SQLite remains the default for a quick local start.",
            styles["BodyCopy"],
        ),
        Paragraph("Validation", styles["Subhead"]),
        Paragraph(
            "From frontend, run npm run build. From backend, run .\\run_live_checks.ps1 "
            "in PowerShell for the repository's isolated live API checks and workflow tests.",
            styles["BodyCopy"],
        ),
        Paragraph(
            "More detail: see README.md, backend/.env.example, frontend/.env.example, "
            "and database/schema-notes.sql.",
            styles["SmallCopy"],
        ),
    ]
    doc.build(story, onFirstPage=page_chrome, onLaterPages=page_chrome)
    print(f"Created {OUTPUT}")
    print(f"Screenshot crops: {TOP_CROP.name}, {LOWER_CROP.name}")


if __name__ == "__main__":
    main()
