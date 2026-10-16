from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from .config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True, pool_recycle=3600)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase):
    pass


def upgrade_legacy_schema():
    migrations = {
        "employees": {
            "basic_salary": "NUMERIC(12, 2) NOT NULL DEFAULT 0",
            "hra": "NUMERIC(12, 2) NOT NULL DEFAULT 0",
            "special_allowance": "NUMERIC(12, 2) NOT NULL DEFAULT 0",
            "pf_percentage": "NUMERIC(5, 2) NOT NULL DEFAULT 0",
            "professional_tax": "NUMERIC(12, 2) NOT NULL DEFAULT 0",
            "tds": "NUMERIC(12, 2) NOT NULL DEFAULT 0",
            "date_of_birth": "DATE",
            "address": "TEXT",
            "emergency_contact_name": "VARCHAR(160)",
            "emergency_contact_relationship": "VARCHAR(80)",
            "emergency_contact_phone": "VARCHAR(30)",
        },
        "payroll": {
            "basic_salary": "NUMERIC(12, 2) NOT NULL DEFAULT 0",
            "hra": "NUMERIC(12, 2) NOT NULL DEFAULT 0",
            "special_allowance": "NUMERIC(12, 2) NOT NULL DEFAULT 0",
            "pf_percentage": "NUMERIC(5, 2) NOT NULL DEFAULT 0",
            "pf_deduction": "NUMERIC(12, 2) NOT NULL DEFAULT 0",
            "professional_tax": "NUMERIC(12, 2) NOT NULL DEFAULT 0",
            "tds_deduction": "NUMERIC(12, 2) NOT NULL DEFAULT 0",
            "working_days": "NUMERIC(6, 2) NOT NULL DEFAULT 0",
            "payable_days": "NUMERIC(6, 2) NOT NULL DEFAULT 0",
            "credit_reference": "VARCHAR(40)",
            "overtime_minutes": "INTEGER NOT NULL DEFAULT 0",
            "overtime_pay": "NUMERIC(12, 2) NOT NULL DEFAULT 0",
            "earnings_breakdown": "TEXT NOT NULL DEFAULT '{}'",
            "deductions_breakdown": "TEXT NOT NULL DEFAULT '{}'",
        },
        "attendance": {
            "shift_id": "INTEGER",
            "late_minutes": "INTEGER NOT NULL DEFAULT 0",
            "early_checkout_minutes": "INTEGER NOT NULL DEFAULT 0",
            "overtime_minutes": "INTEGER NOT NULL DEFAULT 0",
        },
        "leave_requests": {
            "review_note": "TEXT",
        },
    }
    with engine.begin() as connection:
        holiday_indexes = {index["name"] for index in inspect(connection).get_indexes("holidays")}
        if "ix_holidays_holiday_date" in holiday_indexes:
            if connection.dialect.name == "mysql":
                connection.exec_driver_sql("DROP INDEX ix_holidays_holiday_date ON holidays")
            else:
                connection.exec_driver_sql("DROP INDEX ix_holidays_holiday_date")
            connection.exec_driver_sql(
                "CREATE INDEX ix_holidays_holiday_date ON holidays (holiday_date)"
            )
        for table_name, columns in migrations.items():
            existing = {column["name"] for column in inspect(connection).get_columns(table_name)}
            added_columns = set()
            for column_name, column_definition in columns.items():
                if column_name in existing:
                    continue
                connection.exec_driver_sql(
                    f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"
                )
                added_columns.add(column_name)
            if "basic_salary" in added_columns and table_name == "employees":
                connection.execute(text(
                    "UPDATE employees SET basic_salary = monthly_salary "
                    "WHERE monthly_salary > 0 AND hra = 0 AND special_allowance = 0"
                ))
            if "basic_salary" in added_columns and table_name == "payroll":
                connection.execute(text(
                    "UPDATE payroll SET basic_salary = gross_salary "
                    "WHERE gross_salary > 0 AND hra = 0 AND special_allowance = 0"
                ))
        holiday_columns = {column["name"] for column in inspect(connection).get_columns("holidays")}
        for column_name, column_definition in {
            "scope": "VARCHAR(20) NOT NULL DEFAULT 'company'",
            "department_id": "INTEGER",
            "is_optional": "BOOLEAN NOT NULL DEFAULT FALSE",
        }.items():
            if column_name not in holiday_columns:
                connection.exec_driver_sql(
                    f"ALTER TABLE holidays ADD COLUMN {column_name} {column_definition}"
                )
        for table_name, index_name, column_name in (
            ("holidays", "ix_holidays_department_id", "department_id"),
            ("attendance", "ix_attendance_shift_id", "shift_id"),
        ):
            index_names = {
                index["name"] for index in inspect(connection).get_indexes(table_name)
            }
            if index_name not in index_names:
                connection.exec_driver_sql(
                    f"CREATE INDEX {index_name} ON {table_name} ({column_name})"
                )

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
