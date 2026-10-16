import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from './api';

const today = new Date();
const todayKey = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
const currency = (value) => new Intl.NumberFormat('en-IN', {
  style: 'currency', currency: 'INR', maximumFractionDigits: 2,
}).format(Number(value || 0));
const errorText = (error, fallback) => error.response?.data?.detail || fallback;

function PageHeading({ eyebrow, title, description }) {
  return (
    <header className="workspace-page-header">
      <div><span className="eyebrow">{eyebrow}</span><h1>{title}</h1><p>{description}</p></div>
      <Link className="page-home-link" to="/">← Back to overview</Link>
    </header>
  );
}

function PhaseMessage({ error, notice }) {
  return <>{error && <div className="dashboard-error" role="alert">{error}</div>}{notice && <div className="dashboard-notice" role="status">{notice}</div>}</>;
}

export function HolidayCalendar({ role }) {
  const [year, setYear] = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth());
  const [view, setView] = useState('month');
  const [holidays, setHolidays] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [form, setForm] = useState({ holiday_date: todayKey, name: '', scope: 'company', department_id: '' });
  const isHR = role === 'admin' || role === 'hr';

  async function loadCalendar() {
    const { data } = await api.get('/holidays/calendar', { params: { year } });
    setHolidays(data);
  }

  useEffect(() => {
    let active = true;
    Promise.all([
      api.get('/holidays/calendar', { params: { year } }),
      ...(isHR ? [api.get('/departments')] : []),
    ]).then(([holidayResult, departmentResult]) => {
      if (!active) return;
      setHolidays(holidayResult.data);
      if (departmentResult) setDepartments(departmentResult.data);
    }).catch((error) => {
      if (active) setError(errorText(error, 'Calendar data could not be loaded.'));
    });
    return () => { active = false; };
  }, [isHR, year]);

  const holidayMap = useMemo(() => holidays.reduce((map, holiday) => {
    const key = String(holiday.holiday_date).slice(0, 10);
    map.set(key, [...(map.get(key) || []), holiday]);
    return map;
  }, new Map()), [holidays]);
  const displayedMonths = view === 'month' ? [month] : Array.from({ length: 12 }, (_, index) => index);

  async function createHoliday(event) {
    event.preventDefault();
    setError('');
    setNotice('');
    try {
      await api.post('/holidays', {
        holiday_date: form.holiday_date,
        name: form.name.trim(),
        scope: form.scope,
        department_id: form.scope === 'regional' ? Number(form.department_id) : null,
        is_optional: form.scope === 'optional',
      });
      setForm({ ...form, name: '' });
      setNotice('Holiday added to the calendar.');
      await loadCalendar();
    } catch (requestError) {
      setError(errorText(requestError, 'Holiday could not be saved.'));
    }
  }

  async function deleteHoliday(id) {
    setError('');
    try {
      await api.delete(`/holidays/${id}`);
      setHolidays((rows) => rows.filter((row) => row.id !== id));
      setNotice('Holiday removed.');
    } catch (requestError) {
      setError(errorText(requestError, 'Holiday could not be removed.'));
    }
  }

  function monthCalendar(monthIndex) {
    const first = new Date(year, monthIndex, 1);
    const startOffset = (first.getDay() + 6) % 7;
    const days = new Date(year, monthIndex + 1, 0).getDate();
    const cellCount = Math.ceil((startOffset + days) / 7) * 7;
    return (
      <section className="phase-calendar-month" key={monthIndex}>
        <h3>{new Date(year, monthIndex, 1).toLocaleDateString(undefined, { month: 'long' })}</h3>
        <div className="phase-calendar-grid phase-calendar-weekdays">{['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map((day) => <span key={day}>{day}</span>)}</div>
        <div className="phase-calendar-grid">
          {Array.from({ length: cellCount }, (_, index) => {
            const day = index - startOffset + 1;
            if (day < 1 || day > days) return <span className="phase-calendar-empty" key={`empty-${index}`} />;
            const key = `${year}-${String(monthIndex + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
            const events = holidayMap.get(key) || [];
            return (
              <div className={`phase-calendar-day${events.length ? ' has-holiday' : ''}${key === todayKey ? ' is-today' : ''}`} key={key} title={events.map((item) => item.name).join(', ')}>
                <span>{day}</span>
                {events.slice(0, 2).map((item) => <small key={item.id}>{item.name}</small>)}
                {events.length > 2 && <small>+{events.length - 2} more</small>}
              </div>
            );
          })}
        </div>
      </section>
    );
  }

  return (
    <div className="workspace-page phase-workspace">
      <PageHeading eyebrow="WORKFORCE CALENDAR" title="Holidays & calendar" description="Company, regional, and optional holidays in one shared calendar." />
      <PhaseMessage error={error} notice={notice} />
      <section className="phase-panel">
        <div className="phase-toolbar">
          <label>Year <input type="number" min="2000" max="2100" value={year} onChange={(event) => setYear(Number(event.target.value))} /></label>
          {view === 'month' && <label>Month <select value={month} onChange={(event) => setMonth(Number(event.target.value))}>{Array.from({ length: 12 }, (_, index) => <option value={index} key={index}>{new Date(year, index, 1).toLocaleDateString(undefined, { month: 'long' })}</option>)}</select></label>}
          <div className="phase-toggle" aria-label="Calendar view">
            <button type="button" className={view === 'month' ? 'active' : ''} onClick={() => setView('month')}>Month</button>
            <button type="button" className={view === 'year' ? 'active' : ''} onClick={() => setView('year')}>Year</button>
          </div>
        </div>
        <div className={`phase-calendar-list${view === 'year' ? ' yearly' : ''}`}>{displayedMonths.map(monthCalendar)}</div>
        {holidays.length === 0 && <p className="phase-muted">No holidays have been added for {year}.</p>}
        <div className="phase-holiday-list">
          {holidays.map((holiday) => (
            <div className="phase-holiday-row" key={holiday.id}>
              <span className="phase-date-chip">{new Date(`${String(holiday.holiday_date).slice(0, 10)}T00:00:00`).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}</span>
              <strong>{holiday.name}</strong>
              <span className="phase-muted">{holiday.scope}{holiday.is_optional ? ' · optional' : ''}</span>
              {isHR && role === 'admin' && <button className="phase-text-button" type="button" onClick={() => deleteHoliday(holiday.id)}>Remove</button>}
            </div>
          ))}
        </div>
      </section>
      {isHR && role === 'admin' && <section className="phase-panel">
        <div className="phase-panel-heading"><div><span className="eyebrow">ADMINISTRATION</span><h2>Add a holiday</h2></div></div>
        <form className="phase-form phase-holiday-form" onSubmit={createHoliday}>
          <label>Date<input required type="date" value={form.holiday_date} onChange={(event) => setForm({ ...form, holiday_date: event.target.value })} /></label>
          <label>Name<input required minLength={2} maxLength={120} value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} /></label>
          <label>Type<select value={form.scope} onChange={(event) => setForm({ ...form, scope: event.target.value, department_id: '' })}><option value="company">Company-wide</option><option value="regional">Regional</option><option value="optional">Optional</option></select></label>
          {form.scope === 'regional' && <label>Department<select required value={form.department_id} onChange={(event) => setForm({ ...form, department_id: event.target.value })}><option value="">Select department</option>{departments.map((department) => <option value={department.id} key={department.id}>{department.name}</option>)}</select></label>}
          <button className="employee-primary-button" type="submit">Add holiday</button>
        </form>
      </section>}
    </div>
  );
}

export function NotificationsCenter({ role }) {
  const [notifications, setNotifications] = useState([]);
  const [unread, setUnread] = useState(0);
  const [preferences, setPreferences] = useState({});
  const [departments, setDepartments] = useState([]);
  const [selectedDepartments, setSelectedDepartments] = useState([]);
  const [broadcast, setBroadcast] = useState({ title: '', message: '' });
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  async function load() {
    const [notificationResult, preferenceResult] = await Promise.all([
      api.get('/notifications/me'),
      api.get('/notifications/me/preferences'),
    ]);
    setNotifications(notificationResult.data.notifications);
    setUnread(notificationResult.data.unread_count);
    setPreferences(preferenceResult.data.preferences);
  }

  useEffect(() => {
    let active = true;
    Promise.all([
      api.get('/notifications/me'),
      api.get('/notifications/me/preferences'),
      ...(role === 'admin' ? [api.get('/departments')] : []),
    ]).then(([notificationResult, preferenceResult, departmentResult]) => {
      if (!active) return;
      setNotifications(notificationResult.data.notifications);
      setUnread(notificationResult.data.unread_count);
      setPreferences(preferenceResult.data.preferences);
      if (departmentResult) setDepartments(departmentResult.data);
    }).catch((requestError) => {
      if (active) setError(errorText(requestError, 'Notifications could not be loaded.'));
    });
    return () => { active = false; };
  }, [role]);

  async function markRead(id) {
    setError('');
    try {
      await api.post(`/notifications/me/${id}/read`);
      await load();
    } catch (requestError) {
      setError(errorText(requestError, 'Notification status could not be updated.'));
    }
  }

  async function savePreference(eventType, enabled) {
    setError('');
    try {
      await api.patch('/notifications/me/preferences', { event_type: eventType, enabled });
      setPreferences((current) => ({ ...current, [eventType]: enabled }));
    } catch (requestError) {
      setError(errorText(requestError, 'Notification preference could not be saved.'));
    }
  }

  async function sendBroadcast(event) {
    event.preventDefault();
    setError('');
    setNotice('');
    try {
      const { data } = await api.post('/notifications/broadcast', {
        ...broadcast,
        department_ids: selectedDepartments.length ? selectedDepartments.map(Number) : null,
      });
      setNotice(`Announcement sent to ${data.recipient_count} employee${data.recipient_count === 1 ? '' : 's'}.`);
      setBroadcast({ title: '', message: '' });
    } catch (requestError) {
      setError(errorText(requestError, 'Announcement could not be sent.'));
    }
  }

  return (
    <div className="workspace-page phase-workspace">
      <PageHeading eyebrow="YOUR WORKSPACE" title="Notification center" description={`${unread} unread notification${unread === 1 ? '' : 's'} · Leave, payroll, attendance, and announcements.`} />
      <PhaseMessage error={error} notice={notice} />
      <section className="phase-panel">
        <div className="phase-panel-heading"><div><span className="eyebrow">INBOX</span><h2>Recent activity</h2></div><span className="record-count">{notifications.length} messages</span></div>
        {notifications.length ? <div className="phase-notification-list">{notifications.map((item) => (
          <article className={`phase-notification${item.is_read ? '' : ' unread'}`} key={item.id}>
            <span className="phase-notification-dot" />
            <div><h3>{item.title}</h3><p>{item.message}</p><small>{new Date(item.created_at).toLocaleString()}</small></div>
            {!item.is_read && <button type="button" className="phase-text-button" onClick={() => markRead(item.id)}>Mark read</button>}
          </article>
        ))}</div> : <p className="phase-muted">You’re all caught up. New updates will appear here.</p>}
      </section>
      <section className="phase-panel">
        <div className="phase-panel-heading"><div><span className="eyebrow">PREFERENCES</span><h2>Choose what reaches you</h2></div></div>
        <div className="phase-preference-list">
          {[
            ['leave_decision', 'Leave decisions'],
            ['leave_application', 'New leave requests'],
            ['payroll_generated', 'Payroll processed'],
            ['payroll_credit_simulated', 'Payroll credit updates'],
            ['attendance_alert', 'Attendance alerts'],
            ['admin_announcement', 'Organization announcements'],
          ].map(([eventType, title]) => (
            <label className="phase-preference" key={eventType}><span><strong>{title}</strong><small>In-app notification</small></span><input type="checkbox" checked={preferences[eventType] !== false} onChange={(event) => savePreference(eventType, event.target.checked)} /></label>
          ))}
        </div>
      </section>
      {role === 'admin' && <section className="phase-panel">
        <div className="phase-panel-heading"><div><span className="eyebrow">ADMIN TOOLS</span><h2>Organization announcement</h2></div></div>
        <form className="phase-form" onSubmit={sendBroadcast}>
          <label>Title<input required minLength={2} maxLength={255} value={broadcast.title} onChange={(event) => setBroadcast({ ...broadcast, title: event.target.value })} /></label>
          <label>Message<textarea required minLength={2} maxLength={4000} rows="4" value={broadcast.message} onChange={(event) => setBroadcast({ ...broadcast, message: event.target.value })} /></label>
          <label>Departments <select multiple value={selectedDepartments} onChange={(event) => setSelectedDepartments(Array.from(event.target.selectedOptions, (option) => option.value))}><option value="" disabled>Select none for everyone</option>{departments.map((department) => <option value={department.id} key={department.id}>{department.name}</option>)}</select><small>Leave unselected to send to the whole organization. Select multiple departments with Ctrl/Cmd.</small></label>
          <button className="employee-primary-button" type="submit">Send announcement</button>
        </form>
      </section>}
    </div>
  );
}

export function ShiftManagement({ role }) {
  const [shifts, setShifts] = useState([]);
  const [assignments, setAssignments] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [report, setReport] = useState([]);
  const [form, setForm] = useState({ name: '', shift_type: 'general', start_time: '09:00', end_time: '17:00', grace_minutes: 10, expected_minutes: 480 });
  const [assignment, setAssignment] = useState({ shift_id: '', target: 'department', target_id: '', effective_from: todayKey, effective_to: '' });
  const [period, setPeriod] = useState({ start_date: `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-01`, end_date: todayKey, shift_id: '', department_id: '' });
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const isHR = role === 'admin' || role === 'hr';

  async function load() {
    const [shiftResult, assignmentResult, employeeResult, departmentResult] = await Promise.all([
      api.get('/shifts', { params: { include_inactive: true } }),
      api.get('/shifts/assignments', { params: { include_history: true } }),
      ...(isHR ? [api.get('/employees'), api.get('/departments')] : []),
    ]);
    setShifts(shiftResult.data);
    setAssignments(assignmentResult.data);
    if (employeeResult) setEmployees(employeeResult.data);
    if (departmentResult) setDepartments(departmentResult.data);
  }

  useEffect(() => {
    load().catch((requestError) => setError(errorText(requestError, 'Shift data could not be loaded.')));
  }, [isHR]);

  async function createShift(event) {
    event.preventDefault();
    setError('');
    setNotice('');
    try {
      await api.post('/shifts', {
        ...form,
        grace_minutes: Number(form.grace_minutes),
        expected_minutes: Number(form.expected_minutes),
      });
      setForm({ ...form, name: '' });
      setNotice('Shift created.');
      await load();
    } catch (requestError) {
      setError(errorText(requestError, 'Shift could not be created.'));
    }
  }

  async function assignShift(event) {
    event.preventDefault();
    setError('');
    setNotice('');
    try {
      const targetId = Number(assignment.target_id);
      await api.post('/shifts/assignments', {
        shift_id: Number(assignment.shift_id),
        employee_id: assignment.target === 'employee' ? targetId : null,
        department_id: assignment.target === 'department' ? targetId : null,
        effective_from: assignment.effective_from,
        effective_to: assignment.effective_to || null,
      });
      setNotice('Shift assignment recorded in history.');
      await load();
    } catch (requestError) {
      setError(errorText(requestError, 'Shift could not be assigned.'));
    }
  }

  async function toggleShift(shift) {
    setError('');
    setNotice('');
    try {
      await api.patch(`/shifts/${shift.id}`, { is_active: !shift.is_active });
      setNotice(`${shift.name} ${shift.is_active ? 'deactivated' : 'activated'}.`);
      await load();
    } catch (requestError) {
      setError(errorText(requestError, 'Shift status could not be updated.'));
    }
  }

  async function loadReport(event) {
    event.preventDefault();
    setError('');
    try {
      const params = { start_date: period.start_date, end_date: period.end_date };
      if (period.shift_id) params.shift_id = Number(period.shift_id);
      if (period.department_id) params.department_id = Number(period.department_id);
      const { data } = await api.get('/shifts/attendance', { params });
      setReport(data);
    } catch (requestError) {
      setError(errorText(requestError, 'Attendance report could not be loaded.'));
    }
  }

  return (
    <div className="workspace-page phase-workspace">
      <PageHeading eyebrow="WORKFORCE PLANNING" title="Shifts & schedules" description="Assign work patterns to departments or individuals and review shift-aware attendance." />
      <PhaseMessage error={error} notice={notice} />
      {isHR && <section className="phase-panel">
        <div className="phase-panel-heading"><div><span className="eyebrow">SHIFT SETUP</span><h2>Define a shift</h2></div></div>
        {role === 'admin' && <form className="phase-form phase-shift-form" onSubmit={createShift}>
          <label>Name<input required minLength={2} maxLength={100} value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} /></label>
          <label>Type<select value={form.shift_type} onChange={(event) => setForm({ ...form, shift_type: event.target.value })}>{['general', 'night', 'flexible', 'remote'].map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
          <label>Starts<input required type="time" value={form.start_time} onChange={(event) => setForm({ ...form, start_time: event.target.value })} /></label>
          <label>Ends<input required type="time" value={form.end_time} onChange={(event) => setForm({ ...form, end_time: event.target.value })} /></label>
          <label>Grace (min)<input type="number" min="0" max="240" value={form.grace_minutes} onChange={(event) => setForm({ ...form, grace_minutes: event.target.value })} /></label>
          <label>Expected (min)<input type="number" min="1" max="1440" value={form.expected_minutes} onChange={(event) => setForm({ ...form, expected_minutes: event.target.value })} /></label>
          <button className="employee-primary-button" type="submit">Create shift</button>
        </form>}
        {role !== 'admin' && <p className="phase-muted">Shift definitions are maintained by an administrator.</p>}
        <div className="phase-record-grid">{shifts.map((shift) => <article className="phase-record-card" key={shift.id}><div><strong>{shift.name}</strong><span className="phase-tag">{shift.shift_type}</span></div><p>{shift.start_time}–{shift.end_time} · {shift.expected_minutes} min · {shift.grace_minutes} min grace</p><small>{shift.is_active ? 'Active' : 'Inactive'}</small>{role === 'admin' && <button className="phase-text-button" type="button" onClick={() => toggleShift(shift)}>{shift.is_active ? 'Deactivate' : 'Reactivate'}</button>}</article>)}</div>
        {isHR && <form className="phase-form phase-assignment-form" onSubmit={assignShift}>
          <h3>Assign a shift</h3>
          <label>Shift<select required value={assignment.shift_id} onChange={(event) => setAssignment({ ...assignment, shift_id: event.target.value })}><option value="">Choose shift</option>{shifts.filter((shift) => shift.is_active).map((shift) => <option value={shift.id} key={shift.id}>{shift.name}</option>)}</select></label>
          <label>Assign to<select value={assignment.target} onChange={(event) => setAssignment({ ...assignment, target: event.target.value, target_id: '' })}><option value="department">Department</option><option value="employee">Employee</option></select></label>
          <label>{assignment.target === 'employee' ? 'Employee' : 'Department'}<select required value={assignment.target_id} onChange={(event) => setAssignment({ ...assignment, target_id: event.target.value })}><option value="">Choose {assignment.target}</option>{(assignment.target === 'employee' ? employees : departments).map((target) => <option value={target.id} key={target.id}>{target.full_name || target.name}</option>)}</select></label>
          <label>Effective from<input required type="date" value={assignment.effective_from} onChange={(event) => setAssignment({ ...assignment, effective_from: event.target.value })} /></label>
          <label>Effective to (optional)<input type="date" min={assignment.effective_from} value={assignment.effective_to} onChange={(event) => setAssignment({ ...assignment, effective_to: event.target.value })} /></label>
          <button className="employee-primary-button" type="submit" disabled={!shifts.length}>Assign shift</button>
        </form>}
      </section>}
      <section className="phase-panel">
        <div className="phase-panel-heading"><div><span className="eyebrow">SCHEDULE HISTORY</span><h2>Assignments</h2></div><span className="record-count">{assignments.length}</span></div>
        {assignments.length ? <div className="phase-record-grid">{assignments.map((item) => <article className="phase-record-card" key={item.id}><div><strong>{item.shift.name}</strong><span className="phase-tag">{item.employee_id ? 'Employee' : 'Department'}</span></div><p>{item.employee_id ? employees.find((employee) => employee.id === item.employee_id)?.full_name || `Employee #${item.employee_id}` : departments.find((department) => department.id === item.department_id)?.name || `Department #${item.department_id}`}</p><small>{item.effective_from} – {item.effective_to || 'Current'}</small></article>)}</div> : <p className="phase-muted">No shift assignments have been recorded.</p>}
      </section>
      {isHR && <section className="phase-panel">
        <div className="phase-panel-heading"><div><span className="eyebrow">ATTENDANCE INSIGHTS</span><h2>Shift attendance report</h2></div></div>
        <form className="phase-toolbar phase-report-form" onSubmit={loadReport}>
          <label>From<input type="date" required value={period.start_date} onChange={(event) => setPeriod({ ...period, start_date: event.target.value })} /></label>
          <label>To<input type="date" required value={period.end_date} onChange={(event) => setPeriod({ ...period, end_date: event.target.value })} /></label>
          <label>Shift<select value={period.shift_id} onChange={(event) => setPeriod({ ...period, shift_id: event.target.value })}><option value="">All shifts</option>{shifts.map((shift) => <option value={shift.id} key={shift.id}>{shift.name}</option>)}</select></label>
          <label>Department<select value={period.department_id} onChange={(event) => setPeriod({ ...period, department_id: event.target.value })}><option value="">All departments</option>{departments.map((department) => <option value={department.id} key={department.id}>{department.name}</option>)}</select></label>
          <button className="employee-primary-button" type="submit">Run report</button>
        </form>
        {report.length > 0 && <div className="table-responsive custom-table phase-table-wrap"><table className="table"><thead><tr><th>Date</th><th>Employee</th><th>Shift</th><th>Status</th><th>Late</th><th>Early out</th><th>Overtime</th></tr></thead><tbody>{report.map((row) => <tr key={row.attendance_id}><td>{row.work_date}</td><td>{row.employee_name}</td><td>{row.shift_name}</td><td>{row.status}</td><td>{row.late_minutes} min</td><td>{row.early_checkout_minutes} min</td><td>{row.overtime_minutes} min</td></tr>)}</tbody></table></div>}
      </section>}
    </div>
  );
}

export function CompensationWorkspace({ role }) {
  const [employees, setEmployees] = useState([]);
  const [selectedEmployee, setSelectedEmployee] = useState('');
  const [components, setComponents] = useState([]);
  const [employeeComponents, setEmployeeComponents] = useState([]);
  const [baseCompensation, setBaseCompensation] = useState([]);
  const [payroll, setPayroll] = useState([]);
  const [baseForm, setBaseForm] = useState({
    basic_salary: '', hra: '0', special_allowance: '0', pf_percentage: '0',
    professional_tax: '0', tds: '0', effective_from: todayKey,
  });
  const [period, setPeriod] = useState({ year: today.getMonth() === 0 ? today.getFullYear() - 1 : today.getFullYear(), month: today.getMonth() === 0 ? 12 : today.getMonth() });
  const [componentForm, setComponentForm] = useState({ name: '', component_type: 'earning', is_variable: false });
  const [assignment, setAssignment] = useState({ component_id: '', monthly_amount: '', effective_from: todayKey, effective_to: '' });
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const isHR = role === 'admin' || role === 'hr';

  async function loadEmployee(employeeId) {
    if (!employeeId) return;
    const [componentResult, payrollResult, baseResult] = await Promise.all([
      api.get(`/payroll/compensation/${employeeId}/components`, { params: { include_history: true } }),
      isHR ? api.get('/payroll', { params: { employee_id: employeeId } }) : api.get('/payroll/me'),
      api.get(`/payroll/compensation/${employeeId}/base`),
    ]);
    setEmployeeComponents(componentResult.data);
    setBaseCompensation(baseResult.data);
    if (baseResult.data.length) setBaseForm({
      ...baseResult.data[0],
      effective_from: todayKey,
    });
    setPayroll(isHR ? payrollResult.data.filter((row) => row.employee_id === Number(employeeId)) : payrollResult.data);
  }

  useEffect(() => {
    let active = true;
    const requests = isHR
      ? [api.get('/employees'), api.get('/payroll/components')]
      : [api.get('/employees/me'), api.get('/payroll/me')];
    Promise.all(requests).then(async ([employeeResult, componentResult]) => {
      if (!active) return;
      if (isHR) {
        setEmployees(employeeResult.data);
        setComponents(componentResult.data);
        if (employeeResult.data.length) {
          setSelectedEmployee(String(employeeResult.data[0].id));
          setBaseForm({
            basic_salary: employeeResult.data[0].basic_salary,
            hra: employeeResult.data[0].hra,
            special_allowance: employeeResult.data[0].special_allowance,
            pf_percentage: employeeResult.data[0].pf_percentage,
            professional_tax: employeeResult.data[0].professional_tax,
            tds: employeeResult.data[0].tds,
            effective_from: todayKey,
          });
          await loadEmployee(String(employeeResult.data[0].id));
        }
      } else {
        const employee = employeeResult.data;
        setSelectedEmployee(String(employee.id));
        const [assigned, personalPayroll, base] = await Promise.all([
          api.get(`/payroll/compensation/${employee.id}/components`, { params: { include_history: true } }),
          Promise.resolve(componentResult),
          api.get(`/payroll/compensation/${employee.id}/base`),
        ]);
        setEmployeeComponents(assigned.data);
        setBaseCompensation(base.data);
        setPayroll(personalPayroll.data);
      }
    }).catch((requestError) => {
      if (active) setError(errorText(requestError, 'Compensation records could not be loaded.'));
    });
    return () => { active = false; };
  }, [isHR]);

  useEffect(() => {
    if (isHR && selectedEmployee) {
      loadEmployee(selectedEmployee).catch((requestError) => setError(errorText(requestError, 'Employee compensation could not be loaded.')));
    }
  }, [isHR, selectedEmployee]);

  async function createComponent(event) {
    event.preventDefault();
    setError('');
    setNotice('');
    try {
      const { data } = await api.post('/payroll/components', { ...componentForm, name: componentForm.name.trim() });
      setComponents((items) => [...items, data].sort((a, b) => a.name.localeCompare(b.name)));
      setComponentForm({ name: '', component_type: 'earning', is_variable: false });
      setNotice('Salary component created.');
    } catch (requestError) {
      setError(errorText(requestError, 'Salary component could not be created.'));
    }
  }

  async function assignComponent(event) {
    event.preventDefault();
    setError('');
    setNotice('');
    try {
      await api.post(`/payroll/compensation/${selectedEmployee}/components`, {
        component_id: Number(assignment.component_id),
        monthly_amount: Number(assignment.monthly_amount),
        effective_from: assignment.effective_from,
        effective_to: assignment.effective_to || null,
      });
      setNotice('Compensation revision saved with its effective date.');
      await loadEmployee(selectedEmployee);
    } catch (requestError) {
      setError(errorText(requestError, 'Compensation could not be updated.'));
    }
  }

  async function reviseBaseCompensation(event) {
    event.preventDefault();
    setError('');
    setNotice('');
    try {
      await api.post(`/payroll/compensation/${selectedEmployee}/base`, {
        ...baseForm,
        basic_salary: Number(baseForm.basic_salary),
        hra: Number(baseForm.hra),
        special_allowance: Number(baseForm.special_allowance),
        pf_percentage: Number(baseForm.pf_percentage),
        professional_tax: Number(baseForm.professional_tax),
        tds: Number(baseForm.tds),
      });
      setNotice('Base compensation and statutory deductions have been revised.');
      await loadEmployee(selectedEmployee);
    } catch (requestError) {
      setError(errorText(requestError, 'Base compensation could not be revised.'));
    }
  }

  async function generatePayroll(event) {
    event.preventDefault();
    setError('');
    setNotice('');
    try {
      const { data } = await api.post('/payroll/generate', { year: Number(period.year), month: Number(period.month) });
      setNotice(`Payroll generated for ${data.generated_count} employees; ${data.skipped_existing} existing records were kept.`);
      await loadEmployee(selectedEmployee);
    } catch (requestError) {
      setError(errorText(requestError, 'Payroll could not be generated.'));
    }
  }

  async function downloadSlip(payrollId) {
    setError('');
    try {
      const { data } = await api.get(`/payroll/${payrollId}/salary-slip.pdf`, { responseType: 'blob' });
      const url = URL.createObjectURL(data);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `salary-slip-${payrollId}.pdf`;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (requestError) {
      setError(errorText(requestError, 'Salary slip could not be downloaded.'));
    }
  }

  return (
    <div className="workspace-page phase-workspace">
      <PageHeading eyebrow="PAY & BENEFITS" title={isHR ? 'Compensation & payroll' : 'My compensation'} description={isHR ? 'Manage salary components, preserve compensation history, and generate detailed payroll.' : 'Review your active salary components and historical payroll statements.'} />
      <PhaseMessage error={error} notice={notice} />
      {isHR && <section className="phase-panel">
        <div className="phase-panel-heading"><div><span className="eyebrow">COMPENSATION SETUP</span><h2>Salary components</h2></div></div>
        {role === 'admin' && employees.length > 0 && <form className="phase-form phase-base-form" onSubmit={reviseBaseCompensation}>
          <h3>Revise base salary structure</h3>
          <label>Employee<select required value={selectedEmployee} onChange={(event) => setSelectedEmployee(event.target.value)}>{employees.map((employee) => <option value={employee.id} key={employee.id}>{employee.full_name} · {employee.employee_code}</option>)}</select></label>
          <label>Basic pay<input required type="number" min="0" step="0.01" value={baseForm.basic_salary} onChange={(event) => setBaseForm({ ...baseForm, basic_salary: event.target.value })} /></label>
          <label>HRA<input required type="number" min="0" step="0.01" value={baseForm.hra} onChange={(event) => setBaseForm({ ...baseForm, hra: event.target.value })} /></label>
          <label>Special allowance<input required type="number" min="0" step="0.01" value={baseForm.special_allowance} onChange={(event) => setBaseForm({ ...baseForm, special_allowance: event.target.value })} /></label>
          <label>PF (%)<input required type="number" min="0" max="100" step="0.01" value={baseForm.pf_percentage} onChange={(event) => setBaseForm({ ...baseForm, pf_percentage: event.target.value })} /></label>
          <label>Professional tax<input required type="number" min="0" step="0.01" value={baseForm.professional_tax} onChange={(event) => setBaseForm({ ...baseForm, professional_tax: event.target.value })} /></label>
          <label>TDS<input required type="number" min="0" step="0.01" value={baseForm.tds} onChange={(event) => setBaseForm({ ...baseForm, tds: event.target.value })} /></label>
          <label>Effective from<input required type="date" value={baseForm.effective_from} onChange={(event) => setBaseForm({ ...baseForm, effective_from: event.target.value })} /></label>
          <button className="employee-primary-button" type="submit">Save base revision</button>
        </form>}
        {role === 'admin' && <form className="phase-form phase-component-form" onSubmit={createComponent}>
          <label>Component name<input required minLength={2} maxLength={100} value={componentForm.name} onChange={(event) => setComponentForm({ ...componentForm, name: event.target.value })} /></label>
          <label>Category<select value={componentForm.component_type} onChange={(event) => setComponentForm({ ...componentForm, component_type: event.target.value })}><option value="earning">Earning</option><option value="deduction">Deduction</option></select></label>
          <label className="phase-checkbox"><input type="checkbox" checked={componentForm.is_variable} onChange={(event) => setComponentForm({ ...componentForm, is_variable: event.target.checked })} /> Variable / bonus</label>
          <button className="employee-primary-button" type="submit">Add component</button>
        </form>}
        <div className="phase-component-chips">{components.map((component) => <span className="phase-component-chip" key={component.id}>{component.name} · {component.component_type}{component.is_variable ? ' · variable' : ''}</span>)}</div>
        {employees.length > 0 && <><form className="phase-form phase-assignment-form" onSubmit={assignComponent}>
          <h3>Assign or revise compensation</h3>
          <label>Employee<select required value={selectedEmployee} onChange={(event) => setSelectedEmployee(event.target.value)}>{employees.map((employee) => <option value={employee.id} key={employee.id}>{employee.full_name} · {employee.employee_code}</option>)}</select></label>
          <label>Component<select required value={assignment.component_id} onChange={(event) => setAssignment({ ...assignment, component_id: event.target.value })}><option value="">Choose component</option>{components.filter((component) => component.is_active).map((component) => <option value={component.id} key={component.id}>{component.name}</option>)}</select></label>
          <label>Monthly amount<input required type="number" min="0" step="0.01" value={assignment.monthly_amount} onChange={(event) => setAssignment({ ...assignment, monthly_amount: event.target.value })} /></label>
          <label>Effective from<input required type="date" value={assignment.effective_from} onChange={(event) => setAssignment({ ...assignment, effective_from: event.target.value })} /></label>
          <label>Effective through (optional)<input type="date" min={assignment.effective_from} value={assignment.effective_to} onChange={(event) => setAssignment({ ...assignment, effective_to: event.target.value })} /></label>
          <button className="employee-primary-button" type="submit" disabled={!components.length}>Save revision</button>
        </form></>}
      </section>}
      {isHR && <section className="phase-panel">
        <div className="phase-panel-heading"><div><span className="eyebrow">PAY CYCLE</span><h2>Generate monthly payroll</h2></div></div>
        <form className="phase-toolbar phase-report-form" onSubmit={generatePayroll}>
          <label>Year<input required type="number" min="2000" max="2100" value={period.year} onChange={(event) => setPeriod({ ...period, year: event.target.value })} /></label>
          <label>Month<select required value={period.month} onChange={(event) => setPeriod({ ...period, month: Number(event.target.value) })}>{Array.from({ length: 12 }, (_, index) => <option value={index + 1} key={index}>{new Date(2000, index, 1).toLocaleDateString(undefined, { month: 'long' })}</option>)}</select></label>
          <button className="employee-primary-button" type="submit">Calculate payroll</button>
        </form>
        <p className="phase-muted">Payroll uses approved leave, holidays, attendance, assigned salary components, statutory deductions, and recorded overtime. Generated months are retained as historical snapshots.</p>
      </section>}
      <section className="phase-panel">
        <div className="phase-panel-heading"><div><span className="eyebrow">BASE PAY HISTORY</span><h2>Salary structure revisions</h2></div></div>
        {baseCompensation.length ? <div className="phase-table-wrap table-responsive custom-table"><table className="table"><thead><tr><th>Basic</th><th>HRA</th><th>Special allowance</th><th>Gross</th><th>PF</th><th>Professional tax</th><th>TDS</th><th>Effective period</th></tr></thead><tbody>{baseCompensation.map((item, index) => <tr key={`${item.effective_from}-${index}`}><td>{currency(item.basic_salary)}</td><td>{currency(item.hra)}</td><td>{currency(item.special_allowance)}</td><td>{currency(item.monthly_salary)}</td><td>{item.pf_percentage}%</td><td>{currency(item.professional_tax)}</td><td>{currency(item.tds)}</td><td>{item.effective_from} – {item.effective_to || 'Current'}</td></tr>)}</tbody></table></div> : <p className="phase-muted">No base compensation revisions have been recorded.</p>}
      </section>
      <section className="phase-panel">
        <div className="phase-panel-heading"><div><span className="eyebrow">COMPENSATION HISTORY</span><h2>{isHR ? 'Employee components' : 'My salary components'}</h2></div></div>
        {employeeComponents.length ? <div className="phase-table-wrap table-responsive custom-table"><table className="table"><thead><tr><th>Component</th><th>Type</th><th>Monthly value</th><th>Effective from</th><th>Effective to</th></tr></thead><tbody>{employeeComponents.map((item) => <tr key={item.id}><td>{item.component}</td><td>{item.component_type}{item.is_variable ? ' · variable' : ''}</td><td>{currency(item.monthly_amount)}</td><td>{item.effective_from}</td><td>{item.effective_to || 'Current'}</td></tr>)}</tbody></table></div> : <p className="phase-muted">No additional salary components have been assigned.</p>}
      </section>
      <section className="phase-panel">
        <div className="phase-panel-heading"><div><span className="eyebrow">PAYROLL HISTORY</span><h2>Pay statements</h2></div></div>
        {payroll.length ? <div className="phase-table-wrap table-responsive custom-table"><table className="table"><thead><tr>{isHR && <th>Employee</th>}<th>Period</th><th>Working / payable</th><th>Gross</th><th>Overtime</th><th>LOP</th><th>Deductions</th><th>Net pay</th><th /></tr></thead><tbody>{payroll.map((row) => <tr key={row.id}>{isHR && <td>{row.employee_name}</td>}<td>{new Date(row.year, row.month - 1, 1).toLocaleDateString(undefined, { month: 'long', year: 'numeric' })}</td><td>{row.working_days} / {row.payable_days}</td><td>{currency(row.gross_salary)}</td><td>{currency(row.overtime_pay)}</td><td>{currency(row.lop_deduction)}</td><td>{currency(row.other_deductions)}</td><td><strong>{currency(row.net_salary)}</strong></td><td><button type="button" className="phase-text-button" onClick={() => downloadSlip(row.id)}>Payslip</button></td></tr>)}</tbody></table></div> : <p className="phase-muted">No payroll statements are available yet.</p>}
        {payroll.length > 0 && <details className="phase-breakdown"><summary>View latest earnings and deductions breakdown</summary><div className="phase-breakdown-grid"><div><strong>Earnings</strong>{Object.entries(payroll[0].earnings_breakdown || {}).map(([name, amount]) => <p key={name}><span>{name}</span><b>{currency(amount)}</b></p>)}</div><div><strong>Deductions</strong>{Object.entries(payroll[0].deductions_breakdown || {}).map(([name, amount]) => <p key={name}><span>{name}</span><b>{currency(amount)}</b></p>)}<p><span>Loss of pay</span><b>{currency(payroll[0].lop_deduction)}</b></p></div></div></details>}
      </section>
    </div>
  );
}
