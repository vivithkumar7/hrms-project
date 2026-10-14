from calendar import month_name
from decimal import Decimal
from html import escape
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


INK = colors.HexColor("#202A27")
MUTED = colors.HexColor("#78837D")
NAVY = colors.HexColor("#203B60")
NAVY_DARK = colors.HexColor("#172F4D")
PAPER = colors.HexColor("#F1F4F8")
LINE = colors.HexColor("#CBD5E1")
WHITE = colors.white


def _money(amount: Decimal) -> str:
    return f"INR {amount:,.2f}"


def _amount_in_words(amount: Decimal) -> str:
    ones = (
        "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
        "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
        "seventeen", "eighteen", "nineteen",
    )
    tens = ("", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety")

    def under_thousand(number: int) -> str:
        parts = []
        if number >= 100:
            parts.extend((ones[number // 100], "hundred"))
            number %= 100
        if number >= 20:
            parts.append(tens[number // 10])
            number %= 10
        if number:
            parts.append(ones[number])
        return " ".join(parts)

    rupees = int(amount)
    paise = int((amount - Decimal(rupees)) * 100)
    groups = []
    for divisor, label in (
        (1_000_000_000, "arab"),
        (10_000_000, "crore"),
        (100_000, "lakh"),
        (1_000, "thousand"),
    ):
        count, rupees = divmod(rupees, divisor)
        if count:
            groups.append(f"{under_thousand(count)} {label}")
    if rupees:
        groups.append(under_thousand(rupees))
    words = " ".join(groups) or "zero"
    if paise:
        words += f" and {under_thousand(paise)} paise"
    return f"{words} rupees only"


def _paragraph_styles():
    styles = getSampleStyleSheet()
    return {
        "label": ParagraphStyle(
            "SlipLabel",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7,
            leading=9,
            textColor=MUTED,
            spaceAfter=3,
        ),
        "value": ParagraphStyle(
            "SlipValue",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            textColor=INK,
            splitLongWords=1,
        ),
        "section": ParagraphStyle(
            "SlipSection",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            textColor=NAVY_DARK,
            spaceBefore=0,
            spaceAfter=5,
        ),
        "table": ParagraphStyle(
            "SlipTable",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=INK,
            splitLongWords=1,
        ),
        "table_right": ParagraphStyle(
            "SlipTableRight",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            alignment=TA_RIGHT,
            textColor=INK,
        ),
        "table_header": ParagraphStyle(
            "SlipTableHeader",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7,
            leading=9,
            textColor=WHITE,
        ),
        "table_header_right": ParagraphStyle(
            "SlipTableHeaderRight",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7,
            leading=9,
            alignment=TA_RIGHT,
            textColor=WHITE,
        ),
        "table_header_center": ParagraphStyle(
            "SlipTableHeaderCenter",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7,
            leading=9,
            alignment=TA_CENTER,
            textColor=WHITE,
        ),
        "company": ParagraphStyle(
            "SlipCompany",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            alignment=TA_CENTER,
            textColor=NAVY_DARK,
        ),
        "company_subtitle": ParagraphStyle(
            "SlipCompanySubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            alignment=TA_CENTER,
            textColor=MUTED,
        ),
        "slip_title": ParagraphStyle(
            "SlipTitle",
            parent=styles["Normal"],
            fontName="Helvetica-BoldOblique",
            fontSize=13,
            leading=16,
            alignment=TA_CENTER,
            textColor=NAVY_DARK,
        ),
        "total": ParagraphStyle(
            "SlipTotal",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=11,
            textColor=NAVY_DARK,
        ),
        "total_right": ParagraphStyle(
            "SlipTotalRight",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=11,
            alignment=TA_RIGHT,
            textColor=NAVY_DARK,
        ),
        "net_label": ParagraphStyle(
            "SlipNetLabel",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=NAVY_DARK,
        ),
        "net_amount": ParagraphStyle(
            "SlipNetAmount",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            alignment=TA_RIGHT,
            textColor=NAVY_DARK,
        ),
        "small_right": ParagraphStyle(
            "SlipSmallRight",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=7,
            leading=10,
            alignment=TA_RIGHT,
            textColor=MUTED,
        ),
        "note": ParagraphStyle(
            "SlipNote",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=7,
            leading=10,
            textColor=MUTED,
        ),
        "words": ParagraphStyle(
            "SlipWords",
            parent=styles["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=8,
            leading=11,
            textColor=MUTED,
        ),
    }


def _text(value: object, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(str(value or "—")), style)


def _header_footer(*, sample: bool):
    def draw_footer(canvas, document):
        page_width, _ = A4
        canvas.saveState()
        canvas.setStrokeColor(LINE)
        canvas.line(16 * mm, 15 * mm, page_width - 16 * mm, 15 * mm)
        canvas.setFillColor(MUTED)
        canvas.setFont("Helvetica", 7)
        footer_text = (
            "Illustrative sample using fictional details; not a real payroll record."
            if sample
            else "Computer-generated salary slip. Credit status is shown for reference."
        )
        canvas.drawString(16 * mm, 10 * mm, footer_text)
        canvas.drawRightString(page_width - 16 * mm, 10 * mm, f"CONFIDENTIAL  ·  {document.page}")
        canvas.restoreState()

    return draw_footer


def generate_salary_slip_pdf(
    employee,
    payroll,
    *,
    present_days: Decimal | None = None,
    sample: bool = False,
) -> bytes:
    output = BytesIO()
    period = f"{payroll.year}-{payroll.month:02d}"
    period_label = f"{month_name[payroll.month]} {payroll.year}"
    styles = _paragraph_styles()
    document = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=13 * mm,
        bottomMargin=21 * mm,
        title=f"Salary Slip {period} - {employee.employee_code}",
        author="Big Stack People",
        subject="Confidential monthly salary slip",
    )
    table_width = A4[0] - 32 * mm
    story = [
        _text("Big Stack People", styles["company"]),
        _text("People Operations & Payroll", styles["company_subtitle"]),
        Spacer(1, 3 * mm),
        _text(f"Salary Slip - {period_label}", styles["slip_title"]),
        Spacer(1, 4 * mm),
        _text("EMPLOYEE DETAILS", styles["section"]),
    ]
    department_name = employee.department.name if employee.department else "Not assigned"
    employee_fields = [
        ("EMPLOYEE NAME", employee.full_name),
        ("EMPLOYEE ID", employee.employee_code),
        ("DEPARTMENT", department_name),
        ("DESIGNATION", employee.designation),
        ("DATE JOINED", employee.joining_date.strftime("%d %b %Y")),
        ("PAY PERIOD", period_label),
        ("WORK EMAIL", employee.user.email),
        ("STATEMENT NO.", f"PAY-{period.replace('-', '')}-{payroll.id:06d}"),
    ]
    detail_rows = []
    for index in range(0, len(employee_fields), 2):
        row = []
        for label, value in employee_fields[index : index + 2]:
            row.extend([_text(label, styles["label"]), _text(value, styles["value"])])
        detail_rows.append(row)
    details = Table(detail_rows, colWidths=[24 * mm, 65 * mm, 24 * mm, 65 * mm])
    details.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PAPER),
                ("BOX", (0, 0), (-1, -1), 0.6, LINE),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, WHITE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.extend([details, Spacer(1, 4 * mm), _text("ATTENDANCE SUMMARY", styles["section"])])

    if present_days is None:
        attendance_values = (
            f"{Decimal(payroll.working_days or 0):g}",
            "—",
            "—",
            f"{Decimal(payroll.lop_days or 0):g}",
        )
    else:
        present_days = Decimal(present_days).quantize(Decimal("0.01"))
        paid_leave_days = max(
            Decimal("0"),
            Decimal(payroll.payable_days or 0) - present_days,
        ).quantize(Decimal("0.01"))
        attendance_values = (
            f"{Decimal(payroll.working_days or 0):g}",
            f"{present_days:g}",
            f"{paid_leave_days:g}",
            f"{Decimal(payroll.lop_days or 0):g}",
        )
    attendance_rows = [[
        _text(label, styles["table_header_center"])
        for label in ("WORKING DAYS", "PRESENT DAYS", "PAID LEAVE", "LOP DAYS")
    ], [
        _text(value, styles["value"])
        for value in attendance_values
    ]]
    attendance = Table(attendance_rows, colWidths=[table_width / 4] * 4)
    attendance.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("BACKGROUND", (0, 1), (-1, 1), PAPER),
        ("BOX", (0, 0), (-1, -1), 0.5, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, WHITE),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, 0), 5),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 5),
        ("TOPPADDING", (0, 1), (-1, 1), 6),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 6),
    ]))
    story.extend([attendance, Spacer(1, 4 * mm), _text("EARNINGS & DEDUCTIONS", styles["section"])])

    adjustments = sorted(payroll.adjustments, key=lambda item: (item.created_at, item.id))
    positive_adjustments = [item for item in adjustments if item.amount > 0]
    negative_adjustments = [item for item in adjustments if item.amount < 0]
    lop_days = payroll.lop_days.normalize()
    lop_day_label = "day" if lop_days == 1 else "days"
    basic_salary = Decimal(payroll.basic_salary or 0)
    hra = Decimal(payroll.hra or 0)
    special_allowance = Decimal(payroll.special_allowance or 0)
    if basic_salary + hra + special_allowance == Decimal(payroll.gross_salary):
        earnings = [
            ("Basic salary", basic_salary),
            ("House rent allowance", hra),
            ("Special allowance", special_allowance),
        ]
    else:
        earnings = [("Monthly gross salary", payroll.gross_salary)]
    earnings.extend(
        (f"Adjustment · {item.reason}", item.amount) for item in positive_adjustments
    )
    deductions = [
        (f"Loss of pay · {lop_days:f} {lop_day_label}", payroll.lop_deduction),
        ("Provident fund", Decimal(payroll.pf_deduction or 0)),
        ("Professional tax", Decimal(payroll.professional_tax or 0)),
        ("TDS", Decimal(payroll.tds_deduction or 0)),
    ]
    other_deduction_balance = (
        Decimal(payroll.other_deductions or 0)
        - Decimal(payroll.pf_deduction or 0)
        - Decimal(payroll.professional_tax or 0)
        - Decimal(payroll.tds_deduction or 0)
    )
    if other_deduction_balance > 0:
        deductions.append(("Other deductions", other_deduction_balance))
    deductions.extend(
        (f"Adjustment · {item.reason}", abs(item.amount)) for item in negative_adjustments
    )
    earnings_total = payroll.gross_salary + sum(
        (item.amount for item in positive_adjustments), Decimal("0")
    )
    deductions_total = (
        payroll.lop_deduction
        + payroll.other_deductions
        + sum((abs(item.amount) for item in negative_adjustments), Decimal("0"))
    )

    summary_rows = [[
        _text("EARNINGS", styles["table_header"]),
        _text("AMOUNT", styles["table_header_right"]),
        _text("DEDUCTIONS", styles["table_header"]),
        _text("AMOUNT", styles["table_header_right"]),
    ]]
    row_count = max(len(earnings), len(deductions))
    for index in range(row_count):
        row = []
        for entries in (earnings, deductions):
            if index < len(entries):
                label, amount = entries[index]
                row.extend([
                    _text(label, styles["table"]),
                    _text(_money(amount), styles["table_right"]),
                ])
            else:
                row.extend([_text("", styles["table"]), _text("", styles["table_right"])])
        summary_rows.append(row)
    summary_rows.append([
        _text("TOTAL EARNINGS", styles["total"]),
        _text(_money(earnings_total), styles["total_right"]),
        _text("TOTAL DEDUCTIONS", styles["total"]),
        _text(_money(deductions_total), styles["total_right"]),
    ])
    amount_width = 34 * mm
    label_width = (table_width - 2 * amount_width) / 2
    summary = Table(
        summary_rows,
        colWidths=[label_width, amount_width, label_width, amount_width],
        repeatRows=1,
        hAlign="LEFT",
    )
    summary.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("BACKGROUND", (0, 1), (-1, -2), WHITE),
                ("BACKGROUND", (0, -1), (-1, -1), PAPER),
                ("LINEBELOW", (0, 0), (-1, 0), 0, NAVY),
                ("LINEBELOW", (0, 1), (-1, -2), 0.4, LINE),
                ("LINEABOVE", (0, -1), (-1, -1), 0.8, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.extend([summary, Spacer(1, 4 * mm)])

    status = (
        "Illustrative sample"
        if sample
        else "Credit simulated"
        if payroll.simulated_credited
        else "Awaiting credit"
    )
    net_card = Table(
        [[
            [_text("NET SALARY", styles["net_label"]), Spacer(1, 1 * mm), _text(f"PAYMENT STATUS: {status.upper()}", styles["note"])],
            _text(_money(payroll.net_salary), styles["net_amount"]),
        ]],
        colWidths=[table_width * 0.48, table_width * 0.52],
    )
    net_card.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PAPER),
                ("BOX", (0, 0), (-1, -1), 0.7, LINE),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    story.extend([
        net_card,
        Spacer(1, 2 * mm),
        _text(f"Net amount in words: {_amount_in_words(Decimal(payroll.net_salary))}", styles["words"]),
        Spacer(1, 2 * mm),
    ])
    prepared_at = payroll.generated_at.strftime("%d %b %Y")
    reference = (
        f"Simulated credit reference: {payroll.credit_reference}"
        if payroll.credit_reference
        else f"Payroll reference: PAY-{period.replace('-', '')}-{payroll.id:06d}"
    )
    story.append(
        Table(
            [[
                _text(reference, styles["note"]),
                _text(f"Generated on {prepared_at}", styles["small_right"]),
            ]],
            colWidths=[table_width * 0.58, table_width * 0.42],
        )
    )
    document.build(
        story,
        onFirstPage=_header_footer(sample=sample),
        onLaterPages=_header_footer(sample=sample),
    )
    return output.getvalue()
