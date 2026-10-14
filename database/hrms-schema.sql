-- HRMS schema-only MySQL DDL generated from SQLAlchemy models.

-- No employee, account, payroll, or other application data is included.

CREATE DATABASE IF NOT EXISTS hrms_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE hrms_db;

SET FOREIGN_KEY_CHECKS=0;

CREATE TABLE departments (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	name VARCHAR(120) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
);

CREATE TABLE holidays (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	holiday_date DATE NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE leave_types (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	name VARCHAR(60) NOT NULL, 
	annual_allowance INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
);

CREATE TABLE notification_logs (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	recipient VARCHAR(255) NOT NULL, 
	event_type VARCHAR(100) NOT NULL, 
	subject VARCHAR(255) NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE users (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	email VARCHAR(255) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	`role` VARCHAR(20) NOT NULL, 
	is_active BOOL NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE audit_logs (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	actor_user_id INTEGER, 
	action VARCHAR(120) NOT NULL, 
	entity_type VARCHAR(80) NOT NULL, 
	entity_id VARCHAR(80), 
	details TEXT, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(actor_user_id) REFERENCES users (id)
);

CREATE TABLE auth_sessions (
	id VARCHAR(64) NOT NULL, 
	user_id INTEGER NOT NULL, 
	token_jti VARCHAR(64) NOT NULL, 
	expires_at DATETIME NOT NULL, 
	revoked_at DATETIME, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE TABLE employees (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	user_id INTEGER NOT NULL, 
	employee_code VARCHAR(30) NOT NULL, 
	full_name VARCHAR(160) NOT NULL, 
	department_id INTEGER, 
	designation VARCHAR(120) NOT NULL, 
	joining_date DATE NOT NULL, 
	monthly_salary NUMERIC(12, 2) NOT NULL, 
	basic_salary NUMERIC(12, 2) NOT NULL, 
	hra NUMERIC(12, 2) NOT NULL, 
	special_allowance NUMERIC(12, 2) NOT NULL, 
	pf_percentage NUMERIC(5, 2) NOT NULL, 
	professional_tax NUMERIC(12, 2) NOT NULL, 
	tds NUMERIC(12, 2) NOT NULL, 
	phone VARCHAR(30), 
	is_active BOOL NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (user_id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(department_id) REFERENCES departments (id)
);

CREATE TABLE attendance (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	employee_id INTEGER NOT NULL, 
	work_date DATE NOT NULL, 
	check_in DATETIME, 
	check_out DATETIME, 
	working_minutes INTEGER NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_attendance_employee_date UNIQUE (employee_id, work_date), 
	FOREIGN KEY(employee_id) REFERENCES employees (id)
);

CREATE TABLE employee_documents (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	employee_id INTEGER NOT NULL, 
	original_name VARCHAR(255) NOT NULL, 
	stored_name VARCHAR(255) NOT NULL, 
	content_type VARCHAR(120) NOT NULL, 
	uploaded_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(employee_id) REFERENCES employees (id), 
	UNIQUE (stored_name)
);

CREATE TABLE leave_balances (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	employee_id INTEGER NOT NULL, 
	leave_type_id INTEGER NOT NULL, 
	year INTEGER NOT NULL, 
	remaining_days NUMERIC(6, 2) NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_leave_balance_year UNIQUE (employee_id, leave_type_id, year), 
	FOREIGN KEY(employee_id) REFERENCES employees (id), 
	FOREIGN KEY(leave_type_id) REFERENCES leave_types (id)
);

CREATE TABLE leave_requests (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	employee_id INTEGER NOT NULL, 
	leave_type_id INTEGER NOT NULL, 
	start_date DATE NOT NULL, 
	end_date DATE NOT NULL, 
	days NUMERIC(6, 2) NOT NULL, 
	reason TEXT NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	reviewer_id INTEGER, 
	reviewed_at DATETIME, 
	review_note TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(employee_id) REFERENCES employees (id), 
	FOREIGN KEY(leave_type_id) REFERENCES leave_types (id), 
	FOREIGN KEY(reviewer_id) REFERENCES users (id)
);

CREATE TABLE payroll (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	employee_id INTEGER NOT NULL, 
	year INTEGER NOT NULL, 
	month INTEGER NOT NULL, 
	gross_salary NUMERIC(12, 2) NOT NULL, 
	basic_salary NUMERIC(12, 2) NOT NULL, 
	hra NUMERIC(12, 2) NOT NULL, 
	special_allowance NUMERIC(12, 2) NOT NULL, 
	pf_percentage NUMERIC(5, 2) NOT NULL, 
	pf_deduction NUMERIC(12, 2) NOT NULL, 
	professional_tax NUMERIC(12, 2) NOT NULL, 
	tds_deduction NUMERIC(12, 2) NOT NULL, 
	working_days NUMERIC(6, 2) NOT NULL, 
	payable_days NUMERIC(6, 2) NOT NULL, 
	credit_reference VARCHAR(40), 
	lop_days NUMERIC(6, 2) NOT NULL, 
	lop_deduction NUMERIC(12, 2) NOT NULL, 
	other_deductions NUMERIC(12, 2) NOT NULL, 
	net_salary NUMERIC(12, 2) NOT NULL, 
	locked BOOL NOT NULL, 
	simulated_credited BOOL NOT NULL, 
	generated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_payroll_employee_month UNIQUE (employee_id, year, month), 
	FOREIGN KEY(employee_id) REFERENCES employees (id)
);

CREATE TABLE payroll_adjustments (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	payroll_id INTEGER NOT NULL, 
	actor_user_id INTEGER NOT NULL, 
	amount NUMERIC(12, 2) NOT NULL, 
	reason VARCHAR(500) NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(payroll_id) REFERENCES payroll (id), 
	FOREIGN KEY(actor_user_id) REFERENCES users (id)
);

CREATE UNIQUE INDEX ix_holidays_holiday_date ON holidays (holiday_date);

CREATE UNIQUE INDEX ix_users_email ON users (email);

CREATE INDEX ix_audit_logs_action ON audit_logs (action);

CREATE INDEX ix_audit_logs_actor_user_id ON audit_logs (actor_user_id);

CREATE INDEX ix_audit_logs_created_at ON audit_logs (created_at);

CREATE INDEX ix_audit_logs_created_at_id ON audit_logs (created_at, id);

CREATE INDEX ix_auth_sessions_expires_at ON auth_sessions (expires_at);

CREATE UNIQUE INDEX ix_auth_sessions_token_jti ON auth_sessions (token_jti);

CREATE INDEX ix_auth_sessions_user_id ON auth_sessions (user_id);

CREATE UNIQUE INDEX ix_employees_employee_code ON employees (employee_code);

CREATE INDEX ix_attendance_employee_id ON attendance (employee_id);

CREATE INDEX ix_employee_documents_employee_id ON employee_documents (employee_id);

CREATE INDEX ix_leave_balances_employee_id ON leave_balances (employee_id);

CREATE INDEX ix_leave_requests_employee_id ON leave_requests (employee_id);

CREATE INDEX ix_payroll_employee_id ON payroll (employee_id);

CREATE INDEX ix_payroll_adjustments_payroll_id ON payroll_adjustments (payroll_id);

SET FOREIGN_KEY_CHECKS=1;
