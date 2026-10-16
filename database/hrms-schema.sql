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

CREATE TABLE salary_components (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	name VARCHAR(100) NOT NULL, 
	component_type VARCHAR(20) NOT NULL, 
	is_variable BOOL NOT NULL, 
	is_active BOOL NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
);

CREATE TABLE shifts (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	name VARCHAR(100) NOT NULL, 
	shift_type VARCHAR(20) NOT NULL, 
	start_time TIME NOT NULL, 
	end_time TIME NOT NULL, 
	grace_minutes INTEGER NOT NULL, 
	expected_minutes INTEGER NOT NULL, 
	is_active BOOL NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
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
	date_of_birth DATE, 
	address TEXT, 
	emergency_contact_name VARCHAR(160), 
	emergency_contact_relationship VARCHAR(80), 
	emergency_contact_phone VARCHAR(30), 
	is_active BOOL NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (user_id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(department_id) REFERENCES departments (id)
);

CREATE TABLE holidays (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	holiday_date DATE NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	scope VARCHAR(20) NOT NULL, 
	department_id INTEGER, 
	is_optional BOOL NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(department_id) REFERENCES departments (id)
);

CREATE TABLE in_app_notifications (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	user_id INTEGER NOT NULL, 
	event_type VARCHAR(100) NOT NULL, 
	title VARCHAR(255) NOT NULL, 
	message TEXT NOT NULL, 
	is_read BOOL NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE TABLE notification_preferences (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	user_id INTEGER NOT NULL, 
	event_type VARCHAR(100) NOT NULL, 
	enabled BOOL NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_notification_preference_user_event UNIQUE (user_id, event_type), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE TABLE attendance (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	employee_id INTEGER NOT NULL, 
	work_date DATE NOT NULL, 
	check_in DATETIME, 
	check_out DATETIME, 
	working_minutes INTEGER NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	shift_id INTEGER, 
	late_minutes INTEGER NOT NULL, 
	early_checkout_minutes INTEGER NOT NULL, 
	overtime_minutes INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_attendance_employee_date UNIQUE (employee_id, work_date), 
	FOREIGN KEY(employee_id) REFERENCES employees (id), 
	FOREIGN KEY(shift_id) REFERENCES shifts (id)
);

CREATE TABLE employee_compensation (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	employee_id INTEGER NOT NULL, 
	monthly_salary NUMERIC(12, 2) NOT NULL, 
	basic_salary NUMERIC(12, 2) NOT NULL, 
	hra NUMERIC(12, 2) NOT NULL, 
	special_allowance NUMERIC(12, 2) NOT NULL, 
	pf_percentage NUMERIC(5, 2) NOT NULL, 
	professional_tax NUMERIC(12, 2) NOT NULL, 
	tds NUMERIC(12, 2) NOT NULL, 
	effective_from DATE NOT NULL, 
	effective_to DATE, 
	assigned_by INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(employee_id) REFERENCES employees (id), 
	FOREIGN KEY(assigned_by) REFERENCES users (id)
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

CREATE TABLE employee_salary_components (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	employee_id INTEGER NOT NULL, 
	component_id INTEGER NOT NULL, 
	monthly_amount NUMERIC(12, 2) NOT NULL, 
	effective_from DATE NOT NULL, 
	effective_to DATE, 
	assigned_by INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(employee_id) REFERENCES employees (id), 
	FOREIGN KEY(component_id) REFERENCES salary_components (id), 
	FOREIGN KEY(assigned_by) REFERENCES users (id)
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
	overtime_minutes INTEGER NOT NULL, 
	overtime_pay NUMERIC(12, 2) NOT NULL, 
	earnings_breakdown JSON NOT NULL, 
	deductions_breakdown JSON NOT NULL, 
	net_salary NUMERIC(12, 2) NOT NULL, 
	locked BOOL NOT NULL, 
	simulated_credited BOOL NOT NULL, 
	generated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_payroll_employee_month UNIQUE (employee_id, year, month), 
	FOREIGN KEY(employee_id) REFERENCES employees (id)
);

CREATE TABLE shift_assignments (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	shift_id INTEGER NOT NULL, 
	employee_id INTEGER, 
	department_id INTEGER, 
	effective_from DATE NOT NULL, 
	effective_to DATE, 
	assigned_by INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(shift_id) REFERENCES shifts (id), 
	FOREIGN KEY(employee_id) REFERENCES employees (id), 
	FOREIGN KEY(department_id) REFERENCES departments (id), 
	FOREIGN KEY(assigned_by) REFERENCES users (id)
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

CREATE UNIQUE INDEX ix_users_email ON users (email);

CREATE INDEX ix_audit_logs_action ON audit_logs (action);

CREATE INDEX ix_audit_logs_actor_user_id ON audit_logs (actor_user_id);

CREATE INDEX ix_audit_logs_created_at ON audit_logs (created_at);

CREATE INDEX ix_audit_logs_created_at_id ON audit_logs (created_at, id);

CREATE INDEX ix_auth_sessions_expires_at ON auth_sessions (expires_at);

CREATE UNIQUE INDEX ix_auth_sessions_token_jti ON auth_sessions (token_jti);

CREATE INDEX ix_auth_sessions_user_id ON auth_sessions (user_id);

CREATE UNIQUE INDEX ix_employees_employee_code ON employees (employee_code);

CREATE INDEX ix_holidays_department_id ON holidays (department_id);

CREATE INDEX ix_holidays_holiday_date ON holidays (holiday_date);

CREATE INDEX ix_in_app_notifications_event_type ON in_app_notifications (event_type);

CREATE INDEX ix_in_app_notifications_user_created ON in_app_notifications (user_id, created_at);

CREATE INDEX ix_in_app_notifications_user_id ON in_app_notifications (user_id);

CREATE INDEX ix_notification_preferences_user_id ON notification_preferences (user_id);

CREATE INDEX ix_attendance_employee_id ON attendance (employee_id);

CREATE INDEX ix_attendance_shift_id ON attendance (shift_id);

CREATE INDEX ix_employee_compensation_effective ON employee_compensation (employee_id, effective_from, effective_to);

CREATE INDEX ix_employee_compensation_employee_id ON employee_compensation (employee_id);

CREATE INDEX ix_employee_documents_employee_id ON employee_documents (employee_id);

CREATE INDEX ix_employee_salary_components_component_id ON employee_salary_components (component_id);

CREATE INDEX ix_employee_salary_components_effective ON employee_salary_components (employee_id, effective_from, effective_to);

CREATE INDEX ix_employee_salary_components_employee_id ON employee_salary_components (employee_id);

CREATE INDEX ix_leave_balances_employee_id ON leave_balances (employee_id);

CREATE INDEX ix_leave_requests_employee_id ON leave_requests (employee_id);

CREATE INDEX ix_payroll_employee_id ON payroll (employee_id);

CREATE INDEX ix_shift_assignments_department_dates ON shift_assignments (department_id, effective_from, effective_to);

CREATE INDEX ix_shift_assignments_department_id ON shift_assignments (department_id);

CREATE INDEX ix_shift_assignments_employee_dates ON shift_assignments (employee_id, effective_from, effective_to);

CREATE INDEX ix_shift_assignments_employee_id ON shift_assignments (employee_id);

CREATE INDEX ix_shift_assignments_shift_id ON shift_assignments (shift_id);

CREATE INDEX ix_payroll_adjustments_payroll_id ON payroll_adjustments (payroll_id);

SET FOREIGN_KEY_CHECKS=1;
