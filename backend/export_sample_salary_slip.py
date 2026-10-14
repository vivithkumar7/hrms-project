from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
import sys

from app.salary_slip import generate_salary_slip_pdf


def main() -> None:
    output_path = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else Path(__file__).resolve().parent.parent
        / "deliverables"
        / "sample-salary-slip.pdf"
    )
    employee = SimpleNamespace(
        full_name="Aarav Mehta",
        employee_code="DEMO-024",
        department=SimpleNamespace(name="Product & Design"),
        designation="Senior Product Designer",
        user=SimpleNamespace(email="aarav.mehta@example.com"),
        joining_date=date(2023, 6, 12),
    )
    payroll = SimpleNamespace(
        id=24010,
        year=2026,
        month=10,
        gross_salary=Decimal("86500.00"),
        basic_salary=Decimal("50000.00"),
        hra=Decimal("20000.00"),
        special_allowance=Decimal("16500.00"),
        pf_percentage=Decimal("6.40"),
        pf_deduction=Decimal("3200.00"),
        professional_tax=Decimal("200.00"),
        tds_deduction=Decimal("1050.00"),
        working_days=Decimal("22.00"),
        payable_days=Decimal("21.00"),
        lop_days=Decimal("1.00"),
        lop_deduction=Decimal("3931.82"),
        other_deductions=Decimal("4450.00"),
        net_salary=Decimal("79368.18"),
        credit_reference=None,
        simulated_credited=False,
        generated_at=datetime(2026, 10, 13, 10, 30),
        adjustments=[
            SimpleNamespace(
                id=1,
                amount=Decimal("1250.00"),
                reason="Approved client workshop travel reimbursement",
                created_at=datetime(2026, 10, 12, 14, 20),
            )
        ],
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(
        generate_salary_slip_pdf(
            employee,
            payroll,
            present_days=Decimal("20.00"),
            sample=True,
        )
    )
    print(f"Wrote polished fictional salary statement to {output_path}")


if __name__ == "__main__":
    main()
