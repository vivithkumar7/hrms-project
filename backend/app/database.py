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
        },
        "leave_requests": {
            "review_note": "TEXT",
        },
    }
    with engine.begin() as connection:
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

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
