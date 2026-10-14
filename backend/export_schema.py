import sys
from pathlib import Path

from sqlalchemy.dialects import mysql
from sqlalchemy.schema import CreateIndex, CreateTable

from app.database import Base
from app import models  # noqa: F401 - imports all mapped tables into Base.metadata


def main() -> None:
    output_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "database" / "hrms-schema.sql"
    dialect = mysql.dialect()
    statements = [
        "-- HRMS schema-only MySQL DDL generated from SQLAlchemy models.",
        "-- No employee, account, payroll, or other application data is included.",
        "CREATE DATABASE IF NOT EXISTS hrms_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;",
        "USE hrms_db;",
        "SET FOREIGN_KEY_CHECKS=0;",
    ]
    for table in Base.metadata.sorted_tables:
        statements.append(str(CreateTable(table).compile(dialect=dialect)).strip() + ";")
    for table in Base.metadata.sorted_tables:
        for index in sorted(table.indexes, key=lambda item: item.name or ""):
            statements.append(str(CreateIndex(index).compile(dialect=dialect)).strip() + ";")
    statements.append("SET FOREIGN_KEY_CHECKS=1;")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n\n".join(statements) + "\n", encoding="utf-8")
    print(f"Wrote schema-only DDL for {len(Base.metadata.sorted_tables)} tables to {output_path}")


if __name__ == "__main__":
    main()
