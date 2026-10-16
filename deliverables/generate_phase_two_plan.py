from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as pdf_canvas
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
OUTPUT = ROOT / "deliverables" / "HRMS-Phase-2-Implementation-Plan.pdf"
SCREENSHOTS = ROOT / "deliverables" / "phase-two-screenshots"
REPORT_ASSETS = ROOT / "deliverables" / "hrms-project-report-assets"

INK = colors.HexColor("#172F3D")
TEAL = colors.HexColor("#087F73")
MINT = colors.HexColor("#E9F5F2")
PALE = colors.HexColor("#F2F5F7")
MUTED = colors.HexColor("#61717D")
LINE = colors.HexColor("#D6E0E5")
WHITE = colors.white


class NumberedCanvas(pdf_canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        page_count = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.saveState()
            self.setFont("Helvetica", 8)
            self.setFillColor(MUTED)
            self.drawRightString(
                letter[0] - 0.65 * inch,
                0.36 * inch,
                f"{self._pageNumber} / {page_count}",
            )
            self.restoreState()
            super().showPage()
        super().save()


def make_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="CoverTitle", parent=styles["Title"], fontName="Helvetica-Bold",
        fontSize=26, leading=31, textColor=INK, alignment=TA_CENTER, spaceAfter=10,
    ))
    styles.add(ParagraphStyle(
        name="Lead", parent=styles["Normal"], fontSize=10, leading=14,
        textColor=MUTED, alignment=TA_CENTER, spaceAfter=12,
    ))
    styles.add(ParagraphStyle(
        name="Section", parent=styles["Heading1"], fontName="Helvetica-Bold",
        fontSize=19, leading=23, textColor=INK, spaceBefore=1, spaceAfter=9,
    ))
    styles.add(ParagraphStyle(
        name="Subhead", parent=styles["Heading2"], fontName="Helvetica-Bold",
        fontSize=11, leading=14, textColor=TEAL, spaceBefore=5, spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name="Copy", parent=styles["BodyText"], fontSize=8.8, leading=12.2,
        textColor=INK, spaceAfter=5,
    ))
    styles.add(ParagraphStyle(
        name="Small", parent=styles["BodyText"], fontSize=7.5, leading=10,
        textColor=MUTED, spaceAfter=3,
    ))
    styles.add(ParagraphStyle(
        name="TableHead", parent=styles["BodyText"], fontName="Helvetica-Bold",
        fontSize=7.8, leading=9.5, textColor=WHITE,
    ))
    styles.add(ParagraphStyle(
        name="TableCell", parent=styles["BodyText"], fontSize=7.6, leading=9.8,
        textColor=INK,
    ))
    styles.add(ParagraphStyle(
        name="CoverKicker", parent=styles["Normal"], fontName="Helvetica-Bold",
        fontSize=9, leading=12, textColor=TEAL, alignment=TA_CENTER, spaceAfter=8,
    ))
    return styles


def para(text, styles, name="Copy"):
    return Paragraph(text, styles[name])


def grid(rows, widths):
    table = Table(rows, colWidths=widths, repeatRows=1, hAlign="LEFT")
    commands = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 0.35, LINE),
        ("BACKGROUND", (0, 0), (-1, 0), INK),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, PALE]),
    ]
    table.setStyle(TableStyle(commands))
    return table


def cell(text, styles, header=False):
    return para(text, styles, "TableHead" if header else "TableCell")


def screenshot(path, caption, styles):
    width, height = ImageReader(str(path)).getSize()
    scale = min((4.5 * inch) / width, (1.8 * inch) / height)
    return [
        Spacer(1, 0.08 * inch),
        ReportImage(str(path), width=width * scale, height=height * scale),
        para(caption, styles, "Small"),
    ]


def chrome(canvas, doc):
    canvas.saveState()
    page_width, page_height = letter
    canvas.setFillColor(INK)
    canvas.rect(0, page_height - 0.16 * inch, page_width, 0.16 * inch, fill=1, stroke=0)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(0.65 * inch, 0.36 * inch, "BIG STACK PEOPLE  |  PHASE TWO DELIVERY PLAN")
    canvas.restoreState()


def build_story(styles, body_width):
    story = []

    # Page 1 — overview and delivery context
    story.extend([
        Spacer(1, 0.38 * inch),
        para("BIG STACK PEOPLE  |  HRMS", styles, "CoverKicker"),
        para("Phase Two<br/>Workforce &amp; Payroll", styles, "CoverTitle"),
        para(
            "Scope definition · implementation priorities · two-day delivery plan · acceptance criteria",
            styles, "Lead",
        ),
        Spacer(1, 0.08 * inch),
        grid([
            [cell("OBJECTIVE", styles, True), cell("DELIVERY PRINCIPLE", styles, True)],
            [cell(
                "Strengthen day-to-day workforce operations with shared holiday calendars, "
                "employee notifications, effective-dated work schedules, and transparent "
                "compensation records.",
                styles,
            ), cell(
                "Keep permissions server-enforced, preserve history, validate every write, "
                "and make employee self-service useful on desktop and mobile.",
                styles,
            )],
        ], [body_width / 2, body_width / 2]),
        Spacer(1, 0.14 * inch),
        para("Four workstreams", styles, "Subhead"),
        grid([
            [cell("01  Calendar", styles, True), cell("02  Notifications", styles, True),
             cell("03  Shifts", styles, True), cell("04  Compensation", styles, True)],
            [cell("Holiday scopes, yearly/month views, attendance calendar rules.", styles),
             cell("Personal inbox, read state, preferences, scoped announcements.", styles),
             cell("Shift catalogue, effective assignments, attendance metrics and reports.", styles),
             cell("Salary components, effective-dated revisions, deductions and payroll history.", styles)],
        ], [body_width / 4] * 4),
        Spacer(1, 0.14 * inch),
        para("Repository baseline and two-day assumption", styles, "Subhead"),
        para(
            "The current repository already contains Phase Two backend routes, React workspaces, "
            "and workflow tests for these four areas. This two-day timebox is therefore planned "
            "as integration, gap closure, regression verification, and handover—not as a promise "
            "to build every capability from scratch. Any missing requirement discovered during "
            "Day 1 review must be raised immediately and prioritized against the deadline.",
            styles,
        ),
        para(
            "Baseline evidence: backend/app/phase_two.py, frontend/src/PhaseTwo.jsx, and "
            "backend/tests/test_auth.py. Production readiness still depends on deployment "
            "configuration, data migration review, and stakeholder acceptance.",
            styles, "Small",
        ),
        PageBreak(),
    ])

    # Page 2 — holiday calendar
    story.extend([
        para("01  Holiday &amp; calendar management", styles, "Section"),
        para(
            "Maintain one authoritative holiday calendar that employees can browse and that "
            "attendance and leave calculations can consult consistently.",
            styles,
        ),
        grid([
            [cell("Capability", styles, True), cell("Expected behavior", styles, True)],
            [cell("Company-wide", styles), cell("A holiday applies across the organization.", styles)],
            [cell("Regional", styles), cell("A department-scoped holiday is visible only to matching employees.", styles)],
            [cell("Optional", styles), cell("Visible as an optional day; excluded from working-day totals only according to configured policy.", styles)],
            [cell("Calendar views", styles), cell("Employee-facing month and year views show dates, names, and scope.", styles)],
            [cell("Attendance summary", styles), cell("Non-optional applicable holidays are surfaced in monthly summaries and excluded from expected working-day counts.", styles)],
        ], [1.45 * inch, body_width - 1.45 * inch]),
        para("Primary workflow", styles, "Subhead"),
        para(
            "Admin creates a dated holiday and selects company, regional, or optional scope. "
            "The system validates the date, scope, and department, prevents conflicting duplicate "
            "entries, and records the change. Employees see only holidays applicable to their "
            "organization or region. Attendance summaries use the same scope rules as the calendar.",
            styles,
        ),
        para("Acceptance checks", styles, "Subhead"),
        para(
            "• Company holidays are visible to all active employees.<br/>"
            "• Regional holidays are restricted to employees in the selected department.<br/>"
            "• Optional holidays are visibly marked and do not silently reduce required workdays.<br/>"
            "• Month and year navigation show the correct dates, including leap years.<br/>"
            "• Monthly attendance totals exclude applicable non-optional holidays and report holiday counts.<br/>"
            "• Only authorized roles can create or remove calendar records.",
            styles,
        ),
        para(
            "Policy note: the organization should confirm whether optional holidays reduce "
            "attendance expectations when individually selected; the default plan does not assume they do.",
            styles, "Small",
        ),
        *screenshot(
            SCREENSHOTS / "holiday-calendar.png",
            "Application output: live Holiday & Calendar screen (October 2026; no holidays configured in this demo database).",
            styles,
        ),
        PageBreak(),
    ])

    # Page 3 — notifications
    story.extend([
        para("02  In-app notification center", styles, "Section"),
        para(
            "Provide a persistent, user-specific inbox for operational events alongside existing "
            "email delivery. In-app notification delivery and email delivery are tracked as separate channels.",
            styles,
        ),
        grid([
            [cell("Event", styles, True), cell("Recipient / intent", styles, True)],
            [cell("Leave status", styles), cell("Notify the employee when a request is approved or rejected.", styles)],
            [cell("Payroll processing", styles), cell("Notify relevant employees when a pay run is generated or credited.", styles)],
            [cell("Attendance alert", styles), cell("Surface configured attendance exceptions to the affected employee or authorized manager.", styles)],
            [cell("Admin announcement", styles), cell("Deliver organization-wide or selected-department messages.", styles)],
        ], [1.55 * inch, body_width - 1.55 * inch]),
        para("Inbox and controls", styles, "Subhead"),
        para(
            "Each notification belongs to one user and includes an event type, title, message, "
            "creation time, and read state. The inbox shows unread count, supports marking an "
            "item read, and exposes per-event preferences. Turning off an event preference suppresses "
            "future in-app notices for that event; it does not alter historical records or silently "
            "change email settings.",
            styles,
        ),
        para("Broadcast safeguards", styles, "Subhead"),
        para(
            "Admin selects one or more departments, or sends to the whole organization. The server "
            "validates department IDs, removes duplicate recipients, and creates each notice only "
            "for an eligible active user. Broadcast actions are auditable and must not reveal the "
            "recipient list to other employees.",
            styles,
        ),
        para("Acceptance checks", styles, "Subhead"),
        para(
            "• Employees can see and update only their own inbox and preferences.<br/>"
            "• Read/unread state and unread count remain consistent after refresh.<br/>"
            "• Disabled event preferences prevent new in-app notices for that event.<br/>"
            "• Broadcast audience matches the selected department(s) or organization scope.<br/>"
            "• Invalid, empty, or unauthorized broadcasts fail with a clear response and no partial delivery.",
            styles,
        ),
        *screenshot(
            SCREENSHOTS / "notification-center.png",
            "Application output: live in-app inbox, notification preferences, and Admin announcement controls.",
            styles,
        ),
        PageBreak(),
    ])

    # Page 4 — shifts
    story.extend([
        para("03  Shift &amp; work schedule management", styles, "Section"),
        para(
            "Model working time as reusable shift definitions plus dated assignments, so schedule "
            "changes remain traceable and attendance metrics use the schedule that applied on the day.",
            styles,
        ),
        grid([
            [cell("Shift type", styles, True), cell("Configuration", styles, True)],
            [cell("General", styles), cell("Defined start/end times, expected duration, and grace period.", styles)],
            [cell("Night", styles), cell("Supports a checkout on the following calendar day.", styles)],
            [cell("Flexible", styles), cell("Uses the configured expected duration and applicable attendance policy.", styles)],
            [cell("Remote", styles), cell("Keeps scheduled work expectations while identifying the work mode.", styles)],
        ], [1.35 * inch, body_width - 1.35 * inch]),
        para("Assignment and calculation rules", styles, "Subhead"),
        para(
            "An administrator assigns a shift to exactly one employee or one department for an "
            "effective date range. Assignment history is retained; a later assignment closes the "
            "preceding period rather than rewriting it. Where both department and employee records "
            "apply, the employee-specific assignment takes precedence. Attendance compares check-in "
            "with scheduled start plus grace, checkout with scheduled end, and actual duration with "
            "expected duration to derive late, early-checkout, and overtime minutes.",
            styles,
        ),
        para("Reporting and overrides", styles, "Subhead"),
        para(
            "Authorized HR/Admin users can filter attendance by date range, department, and shift. "
            "Admin corrections must identify the override, recalculate derived metrics against the "
            "selected shift, and record an audit reason. Ordinary employee check-in/out remains "
            "self-service and cannot modify schedule definitions.",
            styles,
        ),
        para(
            "Acceptance checks: reject invalid time ranges and overlapping/inconsistent assignments; "
            "test overnight shifts, grace boundaries, missing checkout, shift changes, department "
            "precedence, report filters, and audited corrections.",
            styles, "Small",
        ),
        *screenshot(
            SCREENSHOTS / "shift-schedules.png",
            "Application output: live shift setup, assignment history, and shift attendance report screen.",
            styles,
        ),
        PageBreak(),
    ])

    # Page 5 — compensation
    story.extend([
        para("04  Advanced payroll &amp; compensation", styles, "Section"),
        para(
            "Keep compensation configuration, payroll calculation, and the employee-facing payslip "
            "clear and auditable. Every pay period must use the compensation terms effective for that period.",
            styles,
        ),
        grid([
            [cell("Layer", styles, True), cell("Required coverage", styles, True)],
            [cell("Base pay", styles), cell("Basic pay and configured fixed allowances such as HRA and special allowance.", styles)],
            [cell("Components", styles), cell("Earning and deduction components; fixed or variable amounts with effective dates.", styles)],
            [cell("Adjustments", styles), cell("Authorized bonus or other variable earning, and approved deductions, with an audit trail.", styles)],
            [cell("Attendance inputs", styles), cell("Working days, approved leave, loss-of-pay, and shift-derived overtime inputs.", styles)],
            [cell("Output", styles), cell("Period history and a payslip separating earnings, deductions, and net pay.", styles)],
        ], [1.45 * inch, body_width - 1.45 * inch]),
        para("Calculation sequence", styles, "Subhead"),
        para(
            "1. Select the compensation revision and component assignments effective in the payroll period.<br/>"
            "2. Calculate period earnings and approved variable items.<br/>"
            "3. Apply attendance-based proration and approved leave/loss-of-pay rules.<br/>"
            "4. Apply configured deductions and adjustments.<br/>"
            "5. Persist the payroll result and render the same stored breakdown on the payslip.",
            styles,
        ),
        para("Controls and acceptance", styles, "Subhead"),
        para(
            "Use decimal monetary values with explicit precision; reject negative values where not "
            "permitted and invalid effective-date ranges. A compensation revision closes the prior "
            "period and preserves history. Employees can access only their own payroll; team-wide "
            "configuration and payroll operations remain role-restricted. Re-running a period must "
            "not silently duplicate or overwrite an approved payroll result.",
            styles,
        ),
        para(
            "Decision required before monetary overtime is paid: approve the overtime rate, eligible "
            "roles, and rounding rule. Until approved, track overtime minutes and do not invent a pay multiplier.",
            styles, "Small",
        ),
        *screenshot(
            REPORT_ASSETS / "payroll-evidence.png",
            "Related application output: employee payroll and salary-slip workspace. This existing demo capture has no employee salary rows.",
            styles,
        ),
        PageBreak(),
    ])

    # Page 6 — platform controls
    story.extend([
        para("05  Security, data integrity &amp; user experience", styles, "Section"),
        para(
            "Apply consistent controls across API endpoints, database writes, and React workspaces. "
            "UI restrictions improve usability; backend authorization remains the security boundary.",
            styles,
        ),
        grid([
            [cell("Area", styles, True), cell("Implementation requirement", styles, True)],
            [cell("Authorization", styles), cell("Admin/HR manage organization operations; employees read/update only their own permitted records.", styles)],
            [cell("Validation", styles), cell("Validate types, ranges, dates, department/employee ownership, duplicate records, and state transitions.", styles)],
            [cell("Auditability", styles), cell("Record actor, operation, target, timestamp, and reason for sensitive changes and overrides.", styles)],
            [cell("Data model", styles), cell("Keep user ownership explicit; index frequent user/date/status and employee/effective-date lookups.", styles)],
            [cell("Transactions", styles), cell("Commit each multi-record workflow atomically; roll back on constraint or delivery errors.", styles)],
            [cell("Responsive UI", styles), cell("Use accessible labels, visible validation/errors, compact mobile layouts, and keyboard-operable controls.", styles)],
        ], [1.35 * inch, body_width - 1.35 * inch]),
        para("Operational considerations", styles, "Subhead"),
        para(
            "Keep notification history user-scoped. Preserve shift and compensation revisions rather "
            "than overwriting operational history. Review database migrations against the existing "
            "SQLite development database and supported MySQL deployment schema. Use pagination or "
            "bounded date windows for growing inboxes and reports, and verify indexes against real query plans.",
            styles,
        ),
        para("Release guardrails", styles, "Subhead"),
        para(
            "No production credential or employee data belongs in generated documents or test fixtures. "
            "Migrations require a backup and rollback path. Email failures must not create a false "
            "success state for in-app delivery, or vice versa. API errors should be explicit and safe "
            "to display without leaking internal details.",
            styles,
        ),
        *screenshot(
            ROOT / "deliverables" / "swagger-ui.png",
            "API output: local Swagger UI documents the API operations and authorization controls.",
            styles,
        ),
        PageBreak(),
    ])

    # Page 7 — timebox
    story.extend([
        para("06  Two-day implementation schedule", styles, "Section"),
        para(
            "A two-day deadline is achievable as a focused integration and release-readiness window "
            "because the current codebase already contains Phase Two modules. It is not a reliable "
            "estimate for a greenfield build of all four workstreams.",
            styles,
        ),
        grid([
            [cell("Timebox", styles, True), cell("Priority work", styles, True), cell("Exit evidence", styles, True)],
            [cell("Day 1<br/>Hours 0–1", styles), cell("Confirm scope, roles, current API/UI behavior, database state, and unresolved business rules.", styles), cell("Agreed acceptance checklist and risks.", styles)],
            [cell("Day 1<br/>Hours 1–3", styles), cell("Close calendar/notification gaps; verify scope filtering, preference handling, and broadcast audience.", styles), cell("Focused API tests pass; no cross-user access.", styles)],
            [cell("Day 1<br/>Hours 3–6", styles), cell("Verify shift assignment history, overnight calculations, report filters, and admin overrides.", styles), cell("Boundary and workflow tests pass.", styles)],
            [cell("Day 1<br/>Hours 6–8", styles), cell("Verify salary revisions, component effective dates, attendance/leave inputs, payroll persistence, and payslip output.", styles), cell("Payroll reconciliation examples signed off.", styles)],
            [cell("Day 2<br/>Hours 0–3", styles), cell("Integrate UI flows; review validation, responsive behavior, empty/loading/error states, and accessibility.", styles), cell("Role-based UI walkthrough complete.", styles)],
            [cell("Day 2<br/>Hours 3–6", styles), cell("Run backend workflow tests, frontend build, migration checks, and API smoke tests.", styles), cell("Regression evidence and no critical failures.", styles)],
            [cell("Day 2<br/>Hours 6–8", styles), cell("Fix release blockers, document setup/known decisions, confirm backup/rollback, and hand over.", styles), cell("Acceptance sign-off and release notes.", styles)],
        ], [1.05 * inch, body_width * 0.57, body_width * 0.27]),
        para("Critical-path decisions", styles, "Subhead"),
        para(
            "Confirm optional-holiday attendance policy, overtime pay treatment, payroll period "
            "reprocessing rules, and who may broadcast. If these decisions are delayed, deliver "
            "tracking and reporting behavior first; do not infer financial policy.",
            styles,
        ),
        PageBreak(),
    ])

    # Page 8 — acceptance and handover
    story.extend([
        para("07  Verification &amp; completion checklist", styles, "Section"),
        para(
            "Close the phase only when user-visible behavior, API permissions, calculations, and "
            "stored history agree. Evidence should come from repeatable tests and a short role-based walkthrough.",
            styles,
        ),
        grid([
            [cell("Workstream", styles, True), cell("Minimum acceptance evidence", styles, True)],
            [cell("Calendar", styles), cell("Company/regional/optional visibility, month/year navigation, and holiday-aware attendance summary.", styles)],
            [cell("Notifications", styles), cell("Event creation, user isolation, read/unread, preferences, and department/all-company broadcasts.", styles)],
            [cell("Shifts", styles), cell("Assignment history, employee/department scope, late/early/overtime boundaries, overnight shifts, and audited override.", styles)],
            [cell("Compensation", styles), cell("Effective-date revision, component totals, attendance/leave adjustment, payroll history, and payslip reconciliation.", styles)],
            [cell("Security/UI", styles), cell("Unauthorized API tests, cross-user isolation, responsive walkthrough, validation/error states, and production build.", styles)],
        ], [1.2 * inch, body_width - 1.2 * inch]),
        para("Release handover", styles, "Subhead"),
        para(
            "• Record the migration procedure, backup/rollback steps, and environment-specific settings.<br/>"
            "• Publish the test/build results and note any remaining business-policy decisions.<br/>"
            "• Confirm authorized Admin/HR and Employee walkthroughs without including live credentials.<br/>"
            "• Confirm monitoring for API errors, notification delivery, payroll runs, and audit events.<br/>"
            "• Obtain stakeholder sign-off against the acceptance evidence above.",
            styles,
        ),
        Spacer(1, 0.08 * inch),
        grid([
            [cell("DELIVERY OUTCOME", styles, True)],
            [cell(
                "A secure, auditable workforce-management phase with clear holiday rules, "
                "user-specific engagement, shift-aware attendance, and explainable payroll "
                "breakdowns—delivered with verified behavior rather than scope claims alone.",
                styles,
            )],
        ], [body_width]),
        Spacer(1, 0.08 * inch),
        para(
            f"Prepared {datetime.now().strftime('%d %B %Y')} from the supplied requirements and local repository review. "
            "This plan is not a production deployment certification.",
            styles, "Small",
        ),
        *screenshot(
            REPORT_ASSETS / "reports-evidence.png",
            "Related application output: Reports & Analytics page from the local demo workspace.",
            styles,
        ),
    ])

    return story


def main():
    styles = make_styles()
    body_width = 7.2 * inch
    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=letter,
        leftMargin=0.65 * inch,
        rightMargin=0.65 * inch,
        topMargin=0.48 * inch,
        bottomMargin=0.58 * inch,
        title="HRMS Phase Two Implementation Plan",
        author="Big Stack People",
        subject="Eight-page Phase Two scope, delivery plan, and acceptance criteria",
    )
    story = build_story(styles, body_width)
    doc.build(
        story,
        onFirstPage=chrome,
        onLaterPages=chrome,
        canvasmaker=NumberedCanvas,
    )
    print(f"Created {OUTPUT}")


if __name__ == "__main__":
    main()
