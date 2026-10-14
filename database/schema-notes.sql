-- Create the database and application user separately using a privileged MySQL account.
CREATE DATABASE IF NOT EXISTS hrms_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- Example only; replace password and restrict host/permissions in real deployments.
CREATE USER IF NOT EXISTS 'hrms_user'@'localhost' IDENTIFIED BY 'CHANGE_ME';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, REFERENCES ON hrms_db.* TO 'hrms_user'@'localhost';
FLUSH PRIVILEGES;
-- Tables are created by SQLAlchemy in this starter. Use Alembic migrations for production.
