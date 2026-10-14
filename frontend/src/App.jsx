import React, { useEffect, useState } from 'react';
import { Routes, Route, Link, NavLink, Navigate, useLocation, useNavigate, useParams } from 'react-router-dom';
import { api, restoreSession, setAccessToken } from './api';

const currency = (value) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(Number(value || 0));

const dateKey = (date) => {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
};

function Login({ onLogin, sessionExpired, authError }) {
  const location = useLocation();
  const navigate = useNavigate();
  const isRegister = location.pathname === '/register';
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setError('');
    setBusy(true);
    try {
      if (isRegister && password !== confirmPassword) {
        setError('Your passwords do not match.');
        return;
      }
      const { data } = await api.post(isRegister ? '/auth/register' : '/auth/login', isRegister
        ? { full_name: fullName.trim(), email: email.trim(), password }
        : { email: email.trim(), password });
      if (!data.access_token || !['admin', 'hr', 'employee'].includes(data.role)) {
        throw new Error('The server returned an invalid session');
      }
      setAccessToken(data.access_token);
      onLogin(data);
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (Array.isArray(detail)) {
        setError(detail.map((issue) => issue.msg).join(' '));
      } else if (typeof detail === 'string') {
        setError(detail);
      } else {
        setError('Login failed. Check your API connection and credentials.');
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-page">
      <section className="login-story">
        <Link className="login-brand" to="/">
          <span className="brand-mark">BK</span>
          <span>Big Stack<span className="brand-light"> / people</span></span>
        </Link>
        <div className="story-copy">
          <span className="eyebrow">A BRIGHTER WAY TO WORK.</span>
          <h1>Make work<br />feel more<br /><span>human.</span></h1>
          <p>Big Stack brings people, work, and everyday HR tasks together in one welcoming workspace.</p>
        </div>
        <div className="story-footer">
          <div className="avatar-stack" aria-hidden="true"><span>AM</span><span>JR</span><span>SK</span><span>+</span></div>
          <span>Good people. Good energy. Better workdays.</span>
        </div>
        <div className="story-orb story-orb-one" />
        <div className="story-orb story-orb-two" />
      </section>

      <section className="login-form-side">
        <div className="login-form-wrap">
          <div className="mobile-login-brand">
            <span className="brand-mark">BK</span>
            <span>Big Stack<span className="brand-light"> / people</span></span>
          </div>
          <div className="login-heading">
            <span className="eyebrow">{isRegister ? 'YOUR NEXT CHAPTER' : 'YOUR WORKSPACE'}</span>
            <h2>{isRegister ? 'Join Big Stack' : 'Welcome back'}</h2>
            <p>{isRegister ? 'Create your employee account and make yourself at home.' : 'Sign in to pick up where you left off.'}</p>
          </div>
          {sessionExpired && <div className="login-error" role="status">Your session expired. Please sign in again.</div>}
          {authError && <div className="login-error" role="alert">{authError}</div>}
          {error && <div className="login-error" role="alert">{error}</div>}
          <form onSubmit={submit}>
            {isRegister && <>
              <label className="login-label" htmlFor="register-name">Full name</label>
              <div className="login-input-wrap">
                <span aria-hidden="true">✳</span>
                <input id="register-name" type="text" autoComplete="name" placeholder="Your name" minLength={2} maxLength={160} required value={fullName} onChange={(e) => setFullName(e.target.value)} />
              </div>
            </>}
            <label className="login-label" htmlFor="login-email">Work email</label>
            <div className="login-input-wrap">
              <span aria-hidden="true">✉</span>
              <input id="login-email" type="email" autoComplete="username" placeholder="you@company.com" required value={email} onChange={(e) => setEmail(e.target.value)} />
            </div>
            <div className="password-label-row">
              <label className="login-label" htmlFor="login-password">{isRegister ? 'Create password' : 'Password'}</label>
            </div>
            <div className="login-input-wrap">
              <span aria-hidden="true">⌑</span>
              <input id="login-password" type={showPassword ? 'text' : 'password'} autoComplete={isRegister ? 'new-password' : 'current-password'} placeholder={isRegister ? 'At least 12 characters' : 'Enter your password'} minLength={isRegister ? 12 : 8} maxLength={128} required value={password} onChange={(e) => setPassword(e.target.value)} />
              <button className="password-toggle" type="button" onClick={() => setShowPassword((shown) => !shown)} aria-label={showPassword ? 'Hide password' : 'Show password'}>{showPassword ? 'Hide' : 'Show'}</button>
            </div>
            {isRegister && <>
              <label className="login-label" htmlFor="confirm-password">Confirm password</label>
              <div className="login-input-wrap">
                <span aria-hidden="true">⌑</span>
                <input id="confirm-password" type={showPassword ? 'text' : 'password'} autoComplete="new-password" placeholder="Enter your password again" minLength={12} maxLength={128} required value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} />
              </div>
            </>}
            <button className="login-submit" disabled={busy}>{busy ? <><span className="button-spinner" /> {isRegister ? 'Creating your account…' : 'Signing you in…'}</> : <>{isRegister ? 'Create employee account' : 'Sign in'} <span aria-hidden="true">→</span></>}</button>
          </form>
          <div className="auth-switch">{isRegister ? 'Already part of Big Stack?' : 'New to Big Stack?'} <Link to={isRegister ? '/' : '/register'}>{isRegister ? 'Sign in' : 'Create an account'}</Link></div>
          <div className="login-security"><span>♧</span> {isRegister ? 'Your account starts with secure employee access' : 'Secure, encrypted access to your workspace'}</div>
          {isRegister && <p className="registration-note">Your account is created with the Employee role. Your organization can add your department and payroll details.</p>}
        </div>
        <div className="login-copyright">© {new Date().getFullYear()} Big Stack People <span>·</span> Good energy for your workday.</div>
      </section>
    </div>
  );
}

function MetricCard({ label, value, tone, helper, icon, context }) {
  return (
    <div className={`metric-card metric-${tone}`}>
      <div className="metric-topline">
        <span className="metric-icon" aria-hidden="true">{icon}</span>
        <span className="metric-period">{context}</span>
      </div>
      <div className="metric-label">{label}</div>
      <div className="metric-value">{value}</div>
      <div className="metric-helper"><span className="metric-spark" />{helper}</div>
    </div>
  );
}

function AdminDashboardView({ summary, employees, departments, attendance, loading, error }) {
  const today = new Date();
  const activeEmployees = employees.filter((person) => person.is_active);
  const checkedIn = Number(summary?.present_today || 0) + Number(summary?.half_day_today || 0);
  const presentCount = checkedIn;
  const yetToCheckIn = Math.max(0, activeEmployees.length - checkedIn - Number(summary?.absent_today || 0) - Number(summary?.on_leave_today || 0));
  const attendanceDenominator = Math.max(0, Number(summary?.employee_count || 0) - Number(summary?.on_leave_today || 0));
  const attendanceRate = attendanceDenominator
    ? Math.min(100, Math.round(((Number(summary?.present_today || 0) + Number(summary?.half_day_today || 0) * 0.5) / attendanceDenominator) * 100))
    : 0;
  const week = Array.from({ length: 7 }, (_, index) => {
    const date = new Date(today);
    date.setDate(today.getDate() - (6 - index));
    const key = dateKey(date);
    return {
      key,
      label: new Intl.DateTimeFormat('en', { weekday: 'short' }).format(date),
      count: attendance.filter((row) => row.work_date === key && ['present', 'half_day'].includes(row.status)).length,
    };
  });
  const maxAttendance = Math.max(...week.map((day) => day.count), 1);
  const departmentCounts = departments
    .map((department) => ({
      name: department.name,
      count: activeEmployees.filter((person) => person.department_id === department.id).length,
    }))
    .filter((department) => department.count > 0)
    .sort((left, right) => right.count - left.count || left.name.localeCompare(right.name));
  const unassignedCount = activeEmployees.filter((person) => !person.department_id).length;
  if (unassignedCount) departmentCounts.push({ name: 'Unassigned', count: unassignedCount });
  const maxDepartmentCount = Math.max(...departmentCounts.map((department) => department.count), 1);
  const formattedDate = new Intl.DateTimeFormat('en-US', {
    weekday: 'long', day: 'numeric', month: 'long',
  }).format(today);
  const recentAttendance = [...attendance]
    .sort((left, right) => right.work_date.localeCompare(left.work_date) || right.id - left.id)
    .slice(0, 5);
  const quickActions = [
    { title: 'Add a teammate', detail: 'Grow your people directory', to: '/employees', icon: '＋', tone: 'action-blue' },
    { title: 'Review time off', detail: `${summary?.pending_leaves || 0} requests waiting`, to: '/leaves', icon: '◷', tone: 'action-amber' },
    { title: 'See attendance', detail: 'Check your team’s pulse', to: '/attendance', icon: '↗', tone: 'action-green' },
  ];

  return (
    <div className="dashboard-page admin-dashboard redesigned-admin-dashboard">
      <header className="redesigned-dashboard-header">
        <div><span className="redesigned-dashboard-date">{formattedDate}</span><h1>Good morning, team.</h1><p>Here’s what’s happening across your people today.</p></div>
        <div className="redesigned-workspace-state"><i /><span>Workspace live</span><b>HR</b></div>
      </header>

      <section className="redesigned-dashboard-hero">
        <div className="redesigned-hero-copy">
          <span>YOUR PEOPLE, AT A GLANCE</span>
          <h2>Great teams don’t happen<br />by accident.</h2>
          <p>Make space for the work that helps your people thrive.</p>
          <Link to="/employees">Explore your team <b aria-hidden="true">→</b></Link>
        </div>
        <div className="redesigned-attendance-ring" style={{ '--attendance-rate': `${loading ? 0 : attendanceRate}%` }} aria-label={`${loading ? 'Loading' : attendanceRate}% attendance today`}>
          <div><strong>{loading ? '—' : `${attendanceRate}%`}</strong><small>HERE TODAY</small></div>
        </div>
      </section>

      {error && <div className="dashboard-error" role="alert">{error}</div>}

      <section className="redesigned-metrics-grid" aria-label="People metrics">
        <article className="redesigned-metric-card metric-accent-blue">
          <div className="redesigned-metric-top"><span>♙</span><small>ACTIVE</small></div>
          <p>People on the team</p><strong>{loading ? '—' : activeEmployees.length}</strong>
          <small className="redesigned-metric-note">{loading ? 'Loading team details' : 'Active team members'}</small>
        </article>
        <article className="redesigned-metric-card metric-accent-green">
          <div className="redesigned-metric-top"><span>◉</span><small>TODAY</small></div>
          <p>Here today</p><strong>{loading ? '—' : presentCount}</strong>
          <small className="redesigned-metric-note">{loading ? 'Loading attendance' : 'Checked in today'}</small>
        </article>
        <article className="redesigned-metric-card metric-accent-amber">
          <div className="redesigned-metric-top"><span>◷</span><small>PENDING</small></div>
          <p>Time off to review</p><strong>{loading ? '—' : summary?.pending_leaves ?? 0}</strong>
          <small className="redesigned-metric-note">Waiting for a decision</small>
        </article>
        <article className="redesigned-metric-card metric-accent-violet">
          <div className="redesigned-metric-top"><span>₹</span><small>MONTHLY</small></div>
          <p>Payroll this month</p><strong>{loading ? '—' : currency(summary?.payroll_net_total_this_month)}</strong>
          <small className="redesigned-metric-note">{loading ? 'Loading payroll' : `${summary?.payroll_records_this_month ?? 0} payslips prepared`}</small>
        </article>
      </section>

      <div className="redesigned-dashboard-panels">
        <section className="admin-dashboard-panel redesigned-actions-panel">
          <div className="redesigned-section-kicker">A GOOD PLACE TO START</div>
          <div className="redesigned-section-title"><h2>Quick actions</h2><span aria-hidden="true">✳</span></div>
          <div className="redesigned-quick-actions">
            {quickActions.map((action) => <Link to={action.to} key={action.title} className={action.tone}><span>{action.icon}</span><span><strong>{action.title}</strong><small>{action.detail}</small></span><b aria-hidden="true">↗</b></Link>)}
          </div>
        </section>
        <section className="admin-dashboard-panel redesigned-today-panel">
          <div className="redesigned-section-kicker">THE DAILY EDIT</div>
          <div className="redesigned-section-title"><h2>Today, together</h2></div>
          <div className="redesigned-today-list">
            <Link to="/employees"><span className="metric-accent-blue">♙</span><span><strong>Team members</strong><small>Active in your workspace</small></span><b>{loading ? '—' : activeEmployees.length}</b></Link>
            <Link to="/attendance"><span className="metric-accent-green">◉</span><span><strong>Attendance today</strong><small>{summary?.half_day_today ?? 0} half day · {summary?.absent_today ?? 0} absent · {summary?.on_leave_today ?? 0} on leave</small></span><b>{loading ? '—' : presentCount}</b></Link>
            <Link to="/leaves"><span className="metric-accent-amber">◷</span><span><strong>Time off requests</strong><small>Waiting for your review</small></span><b>{loading ? '—' : summary?.pending_leaves ?? 0}</b></Link>
            <Link to="/leaves"><span className="metric-accent-amber">✳</span><span><strong>Approved leave</strong><small>Requests overlapping this month</small></span><b>{loading ? '—' : summary?.approved_leave_requests_this_month ?? 0}</b></Link>
            <Link to="/payroll"><span className="metric-accent-violet">₹</span><span><strong>Payroll prepared</strong><small>Current month payslips</small></span><b>{loading ? '—' : summary?.payroll_records_this_month ?? 0}</b></Link>
          </div>
        </section>
      </div>

      <div className="admin-dashboard-chart-grid redesigned-charts-grid">
        <section className="admin-dashboard-panel attendance-panel">
          <div className="admin-panel-heading"><h2>Attendance, last 7 days</h2><Link to="/attendance">See attendance →</Link></div>
          <div className="attendance-chart" role="img" aria-label="Daily employee attendance for the last seven days">
            {week.map((day) => (
              <div className="attendance-chart-day" key={day.key} title={`${day.count} present`}>
                <span className="attendance-chart-value">{loading ? '—' : day.count}</span>
                <div className="attendance-chart-track"><i style={{ height: `${day.count ? Math.max(7, (day.count / maxAttendance) * 100) : 3}%` }} /></div>
                <span className="attendance-chart-label">{day.label}</span>
              </div>
            ))}
          </div>
        </section>
        <section className="admin-dashboard-panel department-panel" id="department-panel">
          <div className="admin-panel-heading"><h2>Headcount by department</h2><Link to="/departments">Departments →</Link></div>
          <div className="department-chart">
            {loading ? <p className="admin-panel-empty">Loading departments…</p> : departmentCounts.length ? departmentCounts.map((department) => (
              <div className="department-chart-row" key={department.name}>
                <span>{department.name}</span>
                <div className="department-chart-track"><i style={{ width: `${(department.count / maxDepartmentCount) * 100}%` }} /></div>
                <strong>{department.count}</strong>
              </div>
            )) : <p className="admin-panel-empty">No department headcount to display.</p>}
          </div>
        </section>
      </div>

      <section className="admin-dashboard-panel admin-activity-panel redesigned-recent-panel">
        <div className="admin-panel-heading"><h2>Recent attendance</h2><Link to="/attendance">View attendance <span aria-hidden="true">→</span></Link></div>
        {loading ? <p className="admin-panel-empty">Loading recent attendance…</p> : recentAttendance.length ? (
          <div className="admin-recent-activity">
            {recentAttendance.map((row) => (
              <div className="admin-recent-activity-row" key={row.id}>
                <span className="admin-activity-avatar">{row.employee_name?.split(' ').map((part) => part[0]).join('').slice(0, 2) || 'HR'}</span>
                <span className="admin-activity-copy"><strong>{row.employee_name || `Employee #${row.employee_id}`}</strong><small>{row.work_date} · {row.check_in ? new Date(row.check_in).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'No check-in'}</small></span>
                <span className={`status-pill status-${row.status}`}>{row.status.replaceAll('_', ' ')}</span>
              </div>
            ))}
          </div>
        ) : <p className="admin-panel-empty">No attendance activity to show yet.</p>}
      </section>
      <FeatureOverview role="admin" />
    </div>
  );
}

function FeatureOverview({ role }) {
  const isAdmin = role === 'admin';
  const isHRStaff = isAdmin || role === 'hr';
  const features = [
    {
      title: 'Users, roles & permissions',
      description: isAdmin ? 'Manage accounts, roles, and access permissions.' : 'Your account and role-secured workspace.',
      href: isAdmin ? '/access' : '/profile',
      icon: '🔐',
      tone: 'feature-blue',
    },
    {
      title: 'Employee Management',
      description: isHRStaff ? 'Onboard teammates and manage profiles and documents.' : 'View your profile and manage your own documents.',
      href: '/employees',
      icon: '♙',
      tone: 'feature-violet',
    },
    {
      title: 'Attendance Management',
      description: isHRStaff ? 'Review team attendance and working hours.' : 'Check in, check out, and review your hours.',
      href: '/attendance',
      icon: '◷',
      tone: 'feature-green',
    },
    {
      title: 'Leave Management',
      description: isHRStaff ? 'Review requests, decisions, balances, and leave impact.' : 'Apply for leave and follow balances and request status.',
      href: '/leaves',
      icon: '▣',
      tone: 'feature-amber',
    },
    {
      title: 'Payroll Management',
      description: isHRStaff ? 'Prepare payroll and review salary calculations and deductions.' : 'Review your pay history and salary details.',
      href: '/payroll',
      icon: '₹',
      tone: 'feature-green',
    },
    {
      title: 'PDF Salary Slips & Reports',
      description: isHRStaff ? 'Download salary slips and export workforce reports.' : 'Download your available salary statements.',
      href: isHRStaff ? '/reports' : '/payroll',
      icon: '▤',
      tone: 'feature-blue',
    },
    {
      title: 'Notifications & Audit Logs',
      description: isAdmin ? 'Review administrative activity and audit history.' : role === 'hr' ? 'Check delivery outcomes for HR workflow notifications.' : 'Follow the status of your leave requests.',
      href: '/notifications',
      icon: '✉',
      tone: 'feature-amber',
    },
    {
      title: 'Reports & Analytics',
      description: isHRStaff ? 'Explore workforce insights, statistics, and reports.' : 'See your attendance, leave, and personal workday summary.',
      href: '/reports',
      icon: '▥',
      tone: 'feature-violet',
    },
  ];

  return (
    <section className="feature-overview" aria-labelledby="feature-overview-title">
      <header className="feature-overview-heading">
        <div><span className="eyebrow">YOUR HRMS WORKSPACE</span><h2 id="feature-overview-title">Everything for better people operations</h2></div>
        <p>Explore the tools available to your role.</p>
      </header>
      <div className="feature-overview-grid">
        {features.map((feature) => {
          const content = (
            <>
              <span className={`feature-overview-icon ${feature.tone}`} aria-hidden="true">{feature.icon}</span>
              <span className="feature-overview-copy"><strong>{feature.title}</strong><small>{feature.description}</small></span>
              {feature.href && <span className="feature-overview-arrow" aria-hidden="true">→</span>}
            </>
          );
          return feature.href
            ? <Link className="feature-overview-card" to={feature.href} key={feature.title}>{content}</Link>
            : <article className="feature-overview-card feature-overview-static" key={feature.title}>{content}</article>;
        })}
      </div>
    </section>
  );
}

function EmployeeDashboardView({ employee, attendance, leaveBalances, loading, error, notice, personalWeek, maxPersonalMinutes }) {
  const today = new Date();
  const firstName = employee?.full_name?.split(' ')[0] || 'there';
  const greeting = today.getHours() < 12 ? 'Good morning' : today.getHours() < 18 ? 'Good afternoon' : 'Good evening';
  const formattedDate = new Intl.DateTimeFormat('en-US', {
    weekday: 'long', day: 'numeric', month: 'long',
  }).format(today);
  const totalRemaining = leaveBalances.reduce((total, balance) => total + Number(balance.remaining_days || 0), 0);
  const totalAllowance = leaveBalances.reduce((total, balance) => total + Number(balance.annual_allowance || 0), 0);
  const leavePercentage = totalAllowance ? Math.round((totalRemaining / totalAllowance) * 100) : 0;
  const quickActions = [
    { title: 'View my profile', detail: 'Keep your details close', to: '/profile', icon: '♙', tone: 'action-blue' },
    { title: 'Manage time off', detail: 'Apply and track requests', to: '/leaves', icon: '◷', tone: 'action-amber' },
    { title: 'See pay history', detail: 'Open your salary slips', to: '/payroll', icon: '₹', tone: 'action-green' },
  ];

  return (
    <div className="dashboard-page admin-dashboard redesigned-admin-dashboard employee-redesigned-dashboard">
      <header className="redesigned-dashboard-header">
        <div><span className="redesigned-dashboard-date">{formattedDate}</span><h1>{greeting}, {firstName}.</h1><p>Here’s your workday and people space at a glance.</p></div>
        <div className="redesigned-workspace-state"><i /><span>Workspace live</span><b>{firstName.slice(0, 2).toUpperCase()}</b></div>
      </header>

      {error && <div className="dashboard-error" role="alert">{error}</div>}
      {notice && <div className="dashboard-success" role="status">{notice}</div>}

      <section className="redesigned-dashboard-hero">
        <div className="redesigned-hero-copy">
          <span>YOUR PEOPLE SPACE</span>
          <h2>A little progress<br />goes a long way.</h2>
          <p>Your workday, your people space. Everything in one place.</p>
          <Link to="/profile">View your profile <b aria-hidden="true">→</b></Link>
        </div>
        <div className="redesigned-attendance-ring" style={{ '--attendance-rate': `${loading ? 0 : leavePercentage}%` }} aria-label={`${loading ? 'Loading' : leavePercentage}% of leave allowance remains`}>
          <div><strong>{loading ? '—' : `${leavePercentage}%`}</strong><small>LEAVE LEFT</small></div>
        </div>
      </section>

      <section className="redesigned-metrics-grid" aria-label="Your people metrics">
        <article className="redesigned-metric-card metric-accent-amber">
          <div className="redesigned-metric-top"><span>▣</span><small>AVAILABLE</small></div>
          <p>Leave balance</p><strong>{loading ? '—' : `${totalRemaining} days`}</strong>
          <small className="redesigned-metric-note">{loading ? 'Loading leave balance' : `${leaveBalances.length} leave types`}</small>
        </article>
        <article className="redesigned-metric-card metric-accent-violet">
          <div className="redesigned-metric-top"><span>₹</span><small>MONTHLY</small></div>
          <p>Gross salary</p><strong>{loading ? '—' : currency(employee?.monthly_salary)}</strong>
          <small className="redesigned-metric-note">Before deductions</small>
        </article>
      </section>

      <div className="redesigned-dashboard-panels">
        <section className="admin-dashboard-panel redesigned-actions-panel">
          <div className="redesigned-section-kicker">A GOOD PLACE TO START</div>
          <div className="redesigned-section-title"><h2>Quick actions</h2><span aria-hidden="true">✳</span></div>
          <div className="redesigned-quick-actions">
            {quickActions.map((action) => <Link to={action.to} key={action.title} className={action.tone}><span>{action.icon}</span><span><strong>{action.title}</strong><small>{action.detail}</small></span><b aria-hidden="true">↗</b></Link>)}
          </div>
        </section>
        <section className="admin-dashboard-panel redesigned-today-panel">
          <div className="redesigned-section-kicker">YOUR DAY</div>
          <div className="redesigned-section-title"><h2>A few useful links</h2></div>
          <div className="redesigned-today-list">
            <Link to="/profile"><span className="metric-accent-blue">♙</span><span><strong>My profile</strong><small>{employee?.designation || 'Your work details'}</small></span><b>→</b></Link>
            <Link to="/attendance"><span className="metric-accent-green">◉</span><span><strong>Attendance history</strong><small>Check in, check out, and review hours</small></span><b>→</b></Link>
            <Link to="/leaves"><span className="metric-accent-amber">◷</span><span><strong>Time off</strong><small>Apply for leave and follow requests</small></span><b>{loading ? '—' : `${totalRemaining} days`}</b></Link>
            <Link to="/payroll"><span className="metric-accent-violet">₹</span><span><strong>Pay history</strong><small>Statements and salary details</small></span><b>→</b></Link>
          </div>
        </section>
      </div>

      <div className="admin-dashboard-chart-grid redesigned-charts-grid">
        <section className="admin-dashboard-panel attendance-panel">
          <div className="admin-panel-heading"><h2>My attendance, last 7 days</h2><Link to="/attendance">See attendance →</Link></div>
          <div className="attendance-chart" role="img" aria-label="Your working hours for the last seven days">
            {personalWeek.map((day) => (
              <div className="attendance-chart-day" key={day.key} title={`${day.status ? `${day.status.replaceAll('_', ' ')} · ` : ''}${(day.minutes / 60).toFixed(1)} hours`}>
                <span className="attendance-chart-value">{loading ? '—' : `${(day.minutes / 60).toFixed(1)}h`}</span>
                <div className="attendance-chart-track"><i style={{ height: `${day.minutes ? Math.max(7, (day.minutes / maxPersonalMinutes) * 100) : 3}%` }} /></div>
                <span className="attendance-chart-label">{day.label}</span>
              </div>
            ))}
          </div>
        </section>
        <section className="admin-dashboard-panel department-panel">
          <div className="admin-panel-heading"><h2>Leave balance</h2><Link to="/leaves">Manage leave →</Link></div>
          <div className="department-chart">
            {loading ? <p className="admin-panel-empty">Loading leave balances…</p> : leaveBalances.length ? leaveBalances.map((balance) => {
              const remaining = Number(balance.remaining_days || 0);
              const allowance = Number(balance.annual_allowance || 0);
              const percentRemaining = allowance ? Math.min(100, (remaining / allowance) * 100) : 0;
              return (
                <div className="department-chart-row" key={balance.leave_type_id}>
                  <span>{balance.leave_type}</span>
                  <div className="department-chart-track"><i style={{ width: `${percentRemaining}%` }} /></div>
                  <strong>{remaining}/{allowance}</strong>
                </div>
              );
            }) : <p className="admin-panel-empty">No leave balances are available yet.</p>}
          </div>
        </section>
      </div>
      <FeatureOverview role="employee" />
    </div>
  );
}

function Dashboard({ role, clockFormat = '24h' }) {
  const [summary, setSummary] = useState(null);
  const [employee, setEmployee] = useState(null);
  const [attendance, setAttendance] = useState(null);
  const [dashboardLeaveBalances, setDashboardLeaveBalances] = useState([]);
  const [dashboardLeaveTypes, setDashboardLeaveTypes] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [weeklyAttendance, setWeeklyAttendance] = useState([]);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [leaveModalOpen, setLeaveModalOpen] = useState(false);
  const [leaveBusy, setLeaveBusy] = useState(false);
  const [leaveForm, setLeaveForm] = useState({ leave_type_id: '', start_date: '', end_date: '', reason: '' });
  const [loading, setLoading] = useState(true);
  const isAdmin = role === 'admin' || role === 'hr';
  const today = new Date();
  const greeting = today.getHours() < 12 ? 'Good morning' : today.getHours() < 18 ? 'Good afternoon' : 'Good evening';
  const formattedDate = new Intl.DateTimeFormat('en', { weekday: 'long', month: 'long', day: 'numeric' }).format(today);

  useEffect(() => {
    let active = true;
    async function loadDashboard() {
      setLoading(true);
      setError('');
      try {
        if (isAdmin) {
          const endDate = new Date();
          const startDate = new Date(endDate);
          startDate.setDate(endDate.getDate() - 6);
          const [summaryResult, employeeResult, departmentResult, attendanceResult] = await Promise.all([
            api.get('/dashboard/summary'),
            api.get('/employees', { params: { include_inactive: true } }),
            api.get('/departments'),
            api.get('/attendance', { params: { start_date: dateKey(startDate), end_date: dateKey(endDate) } }),
          ]);
          if (active) {
            setSummary(summaryResult.data);
            setEmployees(employeeResult.data);
            setDepartments(departmentResult.data);
            setWeeklyAttendance(attendanceResult.data);
          }
        } else {
          const [profile, attendanceResult, balancesResult, leaveTypesResult] = await Promise.all([
            api.get('/employees/me'),
            api.get('/attendance/me'),
            api.get('/leaves/balances/me'),
            api.get('/leave-types'),
          ]);
          if (active) {
            setEmployee(profile.data);
            setAttendance(attendanceResult.data);
            setDashboardLeaveBalances(balancesResult.data);
            setDashboardLeaveTypes(leaveTypesResult.data);
            setLeaveForm((current) => ({
              ...current,
              leave_type_id: current.leave_type_id || String(leaveTypesResult.data[0]?.id || ''),
            }));
          }
        }
      } catch (e) {
        if (active) setError(e.response?.data?.detail || 'We could not load your dashboard. Please try again.');
      } finally {
        if (active) setLoading(false);
      }
    }
    loadDashboard();
    return () => { active = false; };
  }, [isAdmin]);

  const quickActions = isAdmin
    ? [
        { title: 'Add a teammate', detail: 'Grow your people directory', link: '/employees', icon: '＋', tone: 'action-blue' },
        { title: 'Review time off', detail: `${summary?.pending_leaves || 0} requests waiting`, link: '/leaves', icon: '◷', tone: 'action-amber' },
        { title: 'See attendance', detail: 'Check your team’s pulse', link: '/attendance', icon: '↗', tone: 'action-green' },
      ]
    : [
        { title: 'My profile', detail: 'Your details and role', link: '/profile', icon: '◎', tone: 'action-blue' },
        { title: 'Time off', detail: 'See requests and balances', link: '/leaves', icon: '◷', tone: 'action-amber' },
        { title: 'Pay history', detail: 'Your salary information', link: '/payroll', icon: '↗', tone: 'action-green' },
      ];

  const metrics = isAdmin
    ? [
        { label: 'People on the team', value: summary?.employee_count ?? '—', tone: 'blue', helper: 'Active team members', icon: '♙', context: 'ACTIVE' },
        { label: 'Here today', value: summary?.present_today ?? '—', tone: 'green', helper: 'Checked in today', icon: '◉', context: 'TODAY' },
        { label: 'Time off to review', value: summary?.pending_leaves ?? '—', tone: 'amber', helper: 'Waiting for a decision', icon: '◷', context: 'PENDING' },
        { label: 'Payroll this month', value: summary ? currency(summary.payroll_net_total_this_month) : '—', tone: 'violet', helper: `${summary?.payroll_records_this_month ?? 0} payslips prepared`, icon: '₹', context: 'MONTHLY' },
      ]
    : [
        { label: 'Attendance this month', value: attendance?.days_present ?? '—', tone: 'blue', helper: 'Days recorded', icon: '◉', context: 'MONTHLY' },
        { label: 'Hours worked', value: attendance ? `${Math.floor(attendance.total_working_minutes / 60)}h` : '—', tone: 'green', helper: 'Recorded this month', icon: '◷', context: 'MONTHLY' },
        { label: 'My requests', value: '→', tone: 'amber', helper: 'View your time off', icon: '↗', context: 'PERSONAL', link: '/leaves' },
        { label: 'Pay information', value: '→', tone: 'violet', helper: 'View salary history', icon: '₹', context: 'PERSONAL', link: '/payroll' },
      ];

  const attendancePercent = summary?.employee_count
    ? Math.min(100, Math.round((summary.present_today / summary.employee_count) * 100))
    : 0;
  const personalWeek = Array.from({ length: 7 }, (_, index) => {
    const date = new Date(today);
    date.setDate(today.getDate() - (6 - index));
    const key = dateKey(date);
    const record = attendance?.records?.find((row) => row.work_date === key);
    return {
      key,
      label: new Intl.DateTimeFormat('en', { weekday: 'short' }).format(date),
      minutes: record?.working_minutes || 0,
      status: record?.status || '',
    };
  });
  const maxPersonalMinutes = Math.max(...personalWeek.map((day) => day.minutes), 1);

  async function submitDashboardLeave(event) {
    event.preventDefault();
    setLeaveBusy(true);
    setError('');
    setNotice('');
    try {
      await api.post('/leaves', {
        ...leaveForm,
        leave_type_id: Number(leaveForm.leave_type_id),
      });
      setLeaveForm((current) => ({ ...current, start_date: '', end_date: '', reason: '' }));
      setLeaveModalOpen(false);
      setNotice('Your leave request was submitted for review.');
    } catch (e) {
      setError(e.response?.data?.detail || 'Leave request could not be submitted.');
    } finally {
      setLeaveBusy(false);
    }
  }

  if (isAdmin) {
    return <AdminDashboardView summary={summary} employees={employees} departments={departments} attendance={weeklyAttendance} loading={loading} error={error} />;
  }

  return (
    <>
    <EmployeeDashboardView
      employee={employee}
      attendance={attendance}
      leaveBalances={dashboardLeaveBalances}
      loading={loading}
      error={error}
      notice={notice}
      personalWeek={personalWeek}
      maxPersonalMinutes={maxPersonalMinutes}
    />
    {leaveModalOpen && (
      <div className="employee-dialog-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget && !leaveBusy) setLeaveModalOpen(false); }}>
        <section className="employee-dialog" role="dialog" aria-modal="true" aria-labelledby="dashboard-leave-title">
          <div className="employee-dialog-heading"><h2 id="dashboard-leave-title">Apply for leave</h2><button type="button" onClick={() => setLeaveModalOpen(false)} disabled={leaveBusy} aria-label="Close">×</button></div>
          {error && <div className="dashboard-error employee-dialog-error" role="alert">{error}</div>}
          <form className="employee-dashboard-leave-form" onSubmit={submitDashboardLeave}>
            <label>Leave type
              <select required value={leaveForm.leave_type_id} onChange={(event) => setLeaveForm({ ...leaveForm, leave_type_id: event.target.value })}>
                <option value="">Choose a leave type</option>
                {dashboardLeaveTypes.map((type) => <option key={type.id} value={type.id}>{type.name}</option>)}
              </select>
            </label>
            <div className="employee-leave-date-fields">
              <label>From<input required type="date" min={dateKey(today)} value={leaveForm.start_date} onChange={(event) => setLeaveForm({ ...leaveForm, start_date: event.target.value })} /></label>
              <label>To<input required type="date" min={leaveForm.start_date || dateKey(today)} value={leaveForm.end_date} onChange={(event) => setLeaveForm({ ...leaveForm, end_date: event.target.value })} /></label>
            </div>
            <label>Reason<textarea required minLength={3} maxLength={2000} rows="3" value={leaveForm.reason} onChange={(event) => setLeaveForm({ ...leaveForm, reason: event.target.value })} /></label>
            <p>Weekends and company holidays are not counted. Days beyond your balance may be treated as loss of pay.</p>
            <div className="employee-dialog-actions"><button className="employee-secondary-button" type="button" disabled={leaveBusy} onClick={() => setLeaveModalOpen(false)}>Cancel</button><button className="employee-primary-button" disabled={leaveBusy || !dashboardLeaveTypes.length}>{leaveBusy ? 'Submitting…' : 'Submit request'}</button></div>
          </form>
        </section>
      </div>
    )}
    </>
  );

  /*
   * Admin/HR use the management dashboard above. Employee accounts render the
   * same dashboard structure with their own profile and attendance data.
   */
  return (
    <div className="employee-dashboard">
      <header className="employee-dashboard-heading">
        <div>
          <h1>Hello, {employee?.full_name?.split(' ')[0] || 'there'}</h1>
          <p>{new Intl.DateTimeFormat('en-GB', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }).format(today)}</p>
        </div>
      </header>

      {error && <div className="dashboard-error" role="alert">{error}</div>}
      {notice && <div className="dashboard-success" role="status">{notice}</div>}
      {attendanceNotice && <div className="dashboard-success" role="status">{attendanceNotice}</div>}

      <section className="employee-reference-card">
        <div className="employee-reference-card-heading"><h2>Today’s attendance</h2></div>
        <div className="employee-clock-content">
          <strong className="employee-digital-clock">{loading ? '--:--:--' : digitalClock}</strong>
          <span className={`employee-attendance-state ${todayAttendance?.check_out ? 'is-complete' : todayAttendance?.check_in ? 'is-checked-in' : ''}`}>
            {todayAttendance?.check_out ? 'Day complete' : todayAttendance?.check_in ? 'Checked In' : loading ? 'Loading attendance' : 'Not Checked In'}
          </span>
          <div className="employee-attendance-actions">
            <button className="employee-primary-button" type="button" disabled={loading || attendanceBusy || Boolean(todayAttendance?.check_in)} onClick={() => updateTodayAttendance('check-in')}>
              {attendanceBusy && !todayAttendance?.check_in ? 'Updating…' : 'Check in'}
            </button>
            <button className="employee-secondary-button" type="button" disabled={loading || attendanceBusy || !todayAttendance?.check_in || Boolean(todayAttendance?.check_out)} onClick={() => updateTodayAttendance('check-out')}>
              {attendanceBusy && todayAttendance?.check_in && !todayAttendance?.check_out ? 'Updating…' : 'Check out'}
            </button>
          </div>
          {todayAttendance?.check_in && <p className="employee-clock-detail">Checked in at {new Date(todayAttendance.check_in).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}{todayAttendance.check_out ? ` · Checked out at ${new Date(todayAttendance.check_out).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}` : ''}</p>}
        </div>
      </section>

      <section className="employee-reference-card employee-month-card">
        <div className="employee-reference-card-heading"><h2>This month</h2><span>{currentMonthName} {today.getFullYear()}</span></div>
        <dl className="employee-month-stats">
          <div><dt>Working days</dt><dd>{loading ? '—' : monthWorkingDays}</dd></div>
          <div><dt>Present</dt><dd>{loading ? '—' : `${currentPresentDays}${currentHalfDays ? ` (+${currentHalfDays} half)` : ''}`}</dd></div>
          <div><dt>On leave</dt><dd>{loading ? '—' : currentLeaveDays}</dd></div>
          <div><dt>Absent</dt><dd>{loading ? '—' : currentAbsentDays}</dd></div>
          <div><dt>Hours worked</dt><dd>{loading ? '—' : `${Math.floor(workedMinutes / 60)}h ${workedMinutes % 60}m`}</dd></div>
        </dl>
      </section>

      <section className="employee-reference-card employee-attendance-chart-panel">
        <div className="employee-reference-card-heading"><h2>My attendance, last 7 days</h2><Link to="/attendance">Attendance details <span aria-hidden="true">→</span></Link></div>
        <div className="attendance-chart" role="img" aria-label="Your working hours for the last seven days">
          {personalWeek.map((day) => (
            <div className="attendance-chart-day" key={day.key} title={`${day.status ? `${day.status.replaceAll('_', ' ')} · ` : ''}${(day.minutes / 60).toFixed(1)} hours`}>
              <span className="attendance-chart-value">{loading ? '—' : `${(day.minutes / 60).toFixed(1)}h`}</span>
              <div className="attendance-chart-track"><i style={{ height: `${day.minutes ? Math.max(7, (day.minutes / maxPersonalMinutes) * 100) : 3}%` }} /></div>
              <span className="attendance-chart-label">{day.label}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="employee-reference-card employee-balance-card">
        <div className="employee-reference-card-heading">
          <h2>Leave balance ({today.getFullYear()})</h2>
          <button type="button" className="employee-secondary-button employee-apply-button" onClick={() => setLeaveModalOpen(true)}>Apply for leave</button>
        </div>
        {loading ? <p className="employee-balance-empty">Loading leave balances…</p> : dashboardLeaveBalances.length ? (
          <div className="employee-leave-balances">
            {dashboardLeaveBalances.map((balance) => {
              const remaining = Number(balance.remaining_days || 0);
              const allowance = Number(balance.annual_allowance || 0);
              const used = Math.max(0, allowance - remaining);
              const percentUsed = allowance ? Math.min(100, (used / allowance) * 100) : 0;
              return (
                <div className="employee-leave-balance" key={balance.leave_type_id}>
                  <div><span>{balance.leave_type}</span><strong>{remaining} / {allowance} left</strong></div>
                  <div className="employee-leave-balance-track"><i style={{ width: `${percentUsed}%` }} /></div>
                </div>
              );
            })}
          </div>
        ) : <p className="employee-balance-empty">No leave balances are available yet.</p>}
      </section>

      <section className="employee-reference-card employee-dashboard-actions">
        <div className="employee-reference-card-heading"><h2>Quick actions</h2></div>
        <div className="employee-dashboard-action-links">
          <Link to="/profile"><span>♙</span><strong>View profile</strong><b aria-hidden="true">→</b></Link>
          <Link to="/leaves"><span>▣</span><strong>Manage leave</strong><b aria-hidden="true">→</b></Link>
          <Link to="/payroll"><span>₹</span><strong>Salary slips</strong><b aria-hidden="true">→</b></Link>
        </div>
      </section>
      <FeatureOverview role={role} />

      {leaveModalOpen && (
        <div className="employee-dialog-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget && !leaveBusy) setLeaveModalOpen(false); }}>
          <section className="employee-dialog" role="dialog" aria-modal="true" aria-labelledby="dashboard-leave-title">
            <div className="employee-dialog-heading"><h2 id="dashboard-leave-title">Apply for leave</h2><button type="button" onClick={() => setLeaveModalOpen(false)} disabled={leaveBusy} aria-label="Close">×</button></div>
            {error && <div className="dashboard-error employee-dialog-error" role="alert">{error}</div>}
            <form className="employee-dashboard-leave-form" onSubmit={submitDashboardLeave}>
              <label>Leave type
                <select required value={leaveForm.leave_type_id} onChange={(event) => setLeaveForm({ ...leaveForm, leave_type_id: event.target.value })}>
                  <option value="">Choose a leave type</option>
                  {dashboardLeaveTypes.map((type) => <option key={type.id} value={type.id}>{type.name}</option>)}
                </select>
              </label>
              <div className="employee-leave-date-fields">
                <label>From<input required type="date" min={dateKey(today)} value={leaveForm.start_date} onChange={(event) => setLeaveForm({ ...leaveForm, start_date: event.target.value })} /></label>
                <label>To<input required type="date" min={leaveForm.start_date || dateKey(today)} value={leaveForm.end_date} onChange={(event) => setLeaveForm({ ...leaveForm, end_date: event.target.value })} /></label>
              </div>
              <label>Reason<textarea required minLength={3} maxLength={2000} rows="3" value={leaveForm.reason} onChange={(event) => setLeaveForm({ ...leaveForm, reason: event.target.value })} /></label>
              <p>Weekends and company holidays are not counted. Days beyond your balance may be treated as loss of pay.</p>
              <div className="employee-dialog-actions"><button className="employee-secondary-button" type="button" disabled={leaveBusy} onClick={() => setLeaveModalOpen(false)}>Cancel</button><button className="employee-primary-button" disabled={leaveBusy || !dashboardLeaveTypes.length}>{leaveBusy ? 'Submitting…' : 'Submit request'}</button></div>
            </form>
          </section>
        </div>
      )}
    </div>
  );

  return (
    <div className="dashboard-page">
      <header className="dashboard-header">
        <div>
          <span className="eyebrow">{formattedDate}</span>
          <h1>{greeting}{isAdmin ? ', team' : employee?.full_name ? `, ${employee.full_name.split(' ')[0]}` : ''}<span className="greeting-dot">.</span></h1>
          <p>{isAdmin ? 'Here’s what’s happening across your people today.' : 'Your workday, your people space. Everything in one place.'}</p>
        </div>
        <div className="header-tools">
          <span className="live-indicator"><i /> Workspace live</span>
          <span className="header-avatar">{isAdmin ? 'HR' : employee?.full_name?.split(' ').map((part) => part[0]).join('').slice(0, 2) || 'ME'}</span>
        </div>
      </header>

      {error && <div className="dashboard-error" role="alert">{error}</div>}

      {isAdmin ? (
        <section className="welcome-banner">
          <div className="welcome-content">
            <span className="banner-kicker">YOUR PEOPLE, AT A GLANCE</span>
            <h2>Great teams don’t happen<br className="desktop-break" /> by accident.</h2>
            <p>Make space for the work that helps your people thrive.</p>
            <Link className="banner-link" to="/employees">Explore your team <span>→</span></Link>
          </div>
          <div className="attendance-orbit" style={{ '--attendance-progress': `${attendancePercent * 3.6}deg` }}>
            <div className="orbit-center">
              <strong>{loading ? '—' : `${attendancePercent}%`}</strong>
              <span>HERE TODAY</span>
            </div>
            <span className="orbit-spark">✦</span>
          </div>
          <div className="banner-decoration banner-decoration-one" />
          <div className="banner-decoration banner-decoration-two" />
        </section>
      ) : (
        <section className="welcome-banner employee-banner">
          <div className="welcome-content">
            <span className="banner-kicker">YOUR SPACE, YOUR PACE</span>
            <h2>A little progress<br className="desktop-break" /> goes a long way.</h2>
            <p>Take a breath, check in, and make today yours.</p>
            <Link className="banner-link" to="/attendance">View my attendance <span>→</span></Link>
          </div>
          <div className="employee-banner-art"><span>✳</span><i /><b /></div>
          <div className="banner-decoration banner-decoration-one" />
          <div className="banner-decoration banner-decoration-two" />
        </section>
      )}

      {!isAdmin && (
        <>
          {attendanceNotice && <div className="dashboard-attendance-notice" role="status">{attendanceNotice}</div>}
          <section className="attendance-checkin-card">
            <div>
              <span className="eyebrow">TODAY · {today.toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' })}</span>
              <h2>{todayAttendance?.check_out ? 'Your day is complete' : todayAttendance?.check_in ? 'You are checked in' : 'Ready to start your day?'}</h2>
              <p>{todayAttendance?.check_in
                ? `Checked in at ${new Date(todayAttendance.check_in).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}${todayAttendance.check_out ? ` · Checked out at ${new Date(todayAttendance.check_out).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}` : ''}`
                : loading ? 'Loading today’s attendance…' : 'Check in to start recording your work hours.'}</p>
            </div>
            {!todayAttendance?.check_in
              ? <button className="employee-primary-button" type="button" disabled={loading || attendanceBusy} onClick={() => updateTodayAttendance('check-in')}>{attendanceBusy ? 'Updating…' : 'Check in'}</button>
              : !todayAttendance.check_out
                ? <button className="employee-primary-button" type="button" disabled={attendanceBusy} onClick={() => updateTodayAttendance('check-out')}>{attendanceBusy ? 'Updating…' : 'Check out'}</button>
                : <span className="status-pill active">Complete</span>}
          </section>
        </>
      )}

      <section className="metrics-grid" aria-label="People metrics">
        {metrics.map((metric) => {
          const card = <MetricCard key={metric.label} {...metric} />;
          return metric.link ? <Link className="metric-link" key={metric.label} to={metric.link}>{card}</Link> : card;
        })}
      </section>

      <section className="admin-dashboard-panel employee-attendance-panel">
        <div className="admin-panel-heading"><h2>My attendance, last 7 days</h2><Link to="/attendance">View attendance <span aria-hidden="true">→</span></Link></div>
        <div className="attendance-chart" role="img" aria-label="Your working hours for the last seven days">
          {personalWeek.map((day) => (
            <div className="attendance-chart-day" key={day.key} title={`${day.status ? `${day.status.replaceAll('_', ' ')} · ` : ''}${(day.minutes / 60).toFixed(1)} hours`}>
              <span className="attendance-chart-value">{loading ? '—' : day.minutes ? `${(day.minutes / 60).toFixed(1)}h` : '0h'}</span>
              <div className="attendance-chart-track"><i style={{ height: `${day.minutes ? Math.max(7, (day.minutes / maxPersonalMinutes) * 100) : 3}%` }} /></div>
              <span className="attendance-chart-label">{day.label}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="dashboard-lower">
        <div className="dashboard-section quick-section">
          <div className="section-heading">
            <div><span className="eyebrow">A GOOD PLACE TO START</span><h2>Quick actions</h2></div>
            <span className="section-mark">✳</span>
          </div>
          <div className="action-grid">
            {quickActions.map((action) => (
              <Link className={`action-card ${action.tone}`} to={action.link} key={action.title}>
                <span className="action-icon">{action.icon}</span>
                <span className="action-copy"><strong>{action.title}</strong><small>{action.detail}</small></span>
                <span className="action-arrow">↗</span>
              </Link>
            ))}
          </div>
        </div>

        <aside className="dashboard-section today-section">
          <div className="section-heading">
            <div><span className="eyebrow">{isAdmin ? 'THE DAILY EDIT' : 'YOUR DAY'}</span><h2>{isAdmin ? 'Today, together' : 'A few useful links'}</h2></div>
          </div>
          <div className="today-list">
            {isAdmin ? (
              <>
                <div className="today-row"><span className="today-icon today-blue">♙</span><span><strong>Team members</strong><small>Active in your workspace</small></span><b>{loading ? '—' : summary?.employee_count ?? 0}</b></div>
                <div className="today-row"><span className="today-icon today-green">◉</span><span><strong>Attendance today</strong><small>{summary?.half_day_today ?? 0} half day · {summary?.absent_today ?? 0} absent · {summary?.on_leave_today ?? 0} on leave</small></span><b>{loading ? '—' : summary?.present_today ?? 0}</b></div>
                <div className="today-row"><span className="today-icon today-amber">◷</span><span><strong>Time off requests</strong><small>Waiting for your review</small></span><b>{loading ? '—' : summary?.pending_leaves ?? 0}</b></div>
                <div className="today-row"><span className="today-icon today-amber">✳</span><span><strong>Approved leave</strong><small>Requests overlapping this month</small></span><b>{loading ? '—' : summary?.approved_leave_requests_this_month ?? 0}</b></div>
                <div className="today-row"><span className="today-icon today-green">₹</span><span><strong>Payroll prepared</strong><small>Records for this month</small></span><b>{loading ? '—' : summary?.payroll_records_this_month ?? 0}</b></div>
                <div className="today-row"><span className="today-icon today-blue">₹</span><span><strong>Net payroll</strong><small>For generated records</small></span><b>{loading ? '—' : currency(summary?.payroll_net_total_this_month)}</b></div>
              </>
            ) : (
              <>
                <Link className="today-row" to="/profile"><span className="today-icon today-blue">◎</span><span><strong>My profile</strong><small>Keep your details up to date</small></span><b>→</b></Link>
                <Link className="today-row" to="/leaves"><span className="today-icon today-amber">◷</span><span><strong>Time away</strong><small>Check your leave requests</small></span><b>→</b></Link>
                <Link className="today-row" to="/payroll"><span className="today-icon today-green">₹</span><span><strong>Pay history</strong><small>See your salary information</small></span><b>→</b></Link>
              </>
            )}
          </div>
          <div className="today-note"><span>✦</span><p>{isAdmin ? 'Small moments of care add up to a stronger team.' : 'You’re doing better than you think. Keep going.'}</p></div>
        </aside>
      </section>
      <FeatureOverview role={role} />
    </div>
  );
}

function NotificationLogs({ role }) {
  const [rows, setRows] = useState([]);
  const [pendingLeaves, setPendingLeaves] = useState([]);
  const [auditRows, setAuditRows] = useState([]);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [loading, setLoading] = useState(true);
  const [leaveBusy, setLeaveBusy] = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [activeTab, setActiveTab] = useState('leaves');
  const isEmployee = role === 'employee';
  const isAdmin = role === 'admin';
  const canReviewLeaves = role === 'admin' || role === 'hr';

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError('');
    const requests = isEmployee
      ? [api.get('/leaves/me')]
      : [
        api.get('/notifications/logs'),
        api.get('/leaves', { params: { status: 'pending' } }),
        ...(isAdmin ? [api.get('/audit-logs', { params: { limit: 100 } })] : []),
      ];
    Promise.all(requests)
      .then((results) => {
        if (!active) return;
        if (isEmployee) {
          setPendingLeaves(results[0].data);
          setRows([]);
          setAuditRows([]);
          return;
        }
        const [notificationResult, leaveResult, auditResult] = results;
        setRows(notificationResult.data);
        setPendingLeaves(leaveResult.data);
        if (auditResult) setAuditRows(auditResult.data);
      })
      .catch((e) => { if (active) setError(e.response?.data?.detail || 'Workflow activity could not be loaded.'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [isAdmin, isEmployee, refreshKey]);

  async function decideLeave(leaveId, status) {
    if (isEmployee) return;
    setLeaveBusy(leaveId);
    setError('');
    setNotice('');
    try {
      await api.post(`/leaves/${leaveId}/decision`, { status });
      setNotice(`Leave request ${status}.`);
      setRefreshKey((key) => key + 1);
    } catch (e) {
      setError(e.response?.data?.detail || `Leave request could not be ${status}.`);
    } finally {
      setLeaveBusy(null);
    }
  }

  return (
    <div className="workspace-page">
      <header className="workspace-page-header">
        <div><span className="eyebrow">PEOPLE OPERATIONS</span><h1>{isEmployee ? 'Leave notifications' : 'Notifications &amp; Audit Logs'}</h1><p>{isEmployee ? 'Track the status of your leave requests.' : `Review leave requests, workflow notifications${isAdmin ? ', and administrative activity.' : '.'}`}</p></div>
        <Link className="page-home-link" to="/">← Back to overview</Link>
      </header>
      {error && <div className="dashboard-error" role="alert">{error}</div>}
      {notice && <div className="dashboard-notice" role="status">{notice}</div>}
      <section className="workflow-activity">
        <div className="workflow-tabs" role="tablist" aria-label="Workflow activity">
          <button type="button" role="tab" aria-selected={activeTab === 'leaves'} className={activeTab === 'leaves' ? 'active' : ''} onClick={() => setActiveTab('leaves')}>{isEmployee ? 'My leave requests' : 'Leave approvals'} <span>{isEmployee ? pendingLeaves.filter((leave) => leave.status === 'pending').length : pendingLeaves.length}</span></button>
          {!isEmployee && <button type="button" role="tab" aria-selected={activeTab === 'notifications'} className={activeTab === 'notifications' ? 'active' : ''} onClick={() => setActiveTab('notifications')}>Email logs</button>}
          {isAdmin && <button type="button" role="tab" aria-selected={activeTab === 'audit'} className={activeTab === 'audit' ? 'active' : ''} onClick={() => setActiveTab('audit')}>Audit logs</button>}
        </div>
        {activeTab === 'leaves' && <section className="workflow-panel">
          <div className="workflow-panel-heading"><h2>{isEmployee ? 'Your leave requests' : 'Leave requests'}</h2><span className="record-count">{isEmployee ? `${pendingLeaves.length} total` : `${pendingLeaves.length} pending`}</span></div>
          {loading ? <div className="page-loading"><span className="loading-ring" /> Loading leave requests…</div> : pendingLeaves.length ? (
            <div className="workflow-table-scroll"><table className="workflow-table"><thead><tr>{!isEmployee && <><th>Code</th><th>Employee</th></>}<th>Type</th><th>From</th><th>To</th><th>Days</th>{!isEmployee && <th>LOP</th>}<th>Reason</th><th>Status</th><th>Actions</th></tr></thead><tbody>
              {pendingLeaves.map((leave) => <tr key={leave.id}>
                {!isEmployee && <><td>{leave.employee_code || `EMP${String(leave.employee_id).padStart(3, '0')}`}</td><td className="workflow-employee-name">{leave.employee_name || `Employee #${leave.employee_id}`}</td></>}
                <td>{leave.leave_type || 'Leave'}</td>
                <td>{leave.start_date}</td><td>{leave.end_date}</td><td>{Number(leave.days).toFixed(1)}</td>
                {!isEmployee && <td title="Loss of pay is finalized during payroll calculation">—</td>}
                <td className="workflow-reason">{leave.reason}</td>
                <td><span className={`status-pill status-${leave.status}`}>{leave.status.toUpperCase()}</span></td>
                <td><div className="workflow-actions"><button type="button" className="workflow-approve" disabled={!canReviewLeaves || leaveBusy !== null || leave.status !== 'pending'} title={!canReviewLeaves ? 'Only HR or Admin can approve leave requests' : undefined} onClick={() => decideLeave(leave.id, 'approved')}>{leaveBusy === leave.id ? 'Saving…' : 'Approve'}</button><button type="button" className="workflow-reject" disabled={!canReviewLeaves || leaveBusy !== null || leave.status !== 'pending'} title={!canReviewLeaves ? 'Only HR or Admin can reject leave requests' : undefined} onClick={() => decideLeave(leave.id, 'rejected')}>Reject</button></div></td>
              </tr>)}
            </tbody></table></div>
          ) : <div className="empty-state compact-empty"><h3>{isEmployee ? 'No leave requests yet' : 'No pending leave requests'}</h3><p>{isEmployee ? 'Your leave applications and their decision status will appear here.' : 'New employee requests will appear here for review.'}</p></div>}
          {isEmployee && pendingLeaves.length > 0 && <p className="payroll-policy-note">Approve and Reject are disabled for employee accounts. Ask HR or Admin to review your request.</p>}
        </section>}
        {activeTab === 'notifications' && <section className="workflow-panel">
          <div className="workflow-panel-heading"><h2>Email notifications</h2><span className="record-count">{rows.length} events</span></div>
          <p className="payroll-policy-note">“Logged” means SMTP delivery is not configured; “Failed” means the configured mail server rejected or could not deliver the message.</p>
          {loading ? <div className="page-loading"><span className="loading-ring" /> Loading notifications…</div> : rows.length ? (
            <div className="table-responsive custom-table"><table className="table"><thead><tr><th>Recipient</th><th>Event</th><th>Subject</th><th>Status</th><th>Created</th></tr></thead><tbody>
              {rows.map((row) => <tr key={row.id}><td>{row.recipient}</td><td>{row.event_type.replaceAll('_', ' ')}</td><td>{row.subject}</td><td><span className={`status-pill ${row.status === 'sent' ? 'active' : row.status === 'failed' ? 'inactive' : 'status-pending'}`}>{row.status}</span></td><td>{new Date(row.created_at).toLocaleString()}</td></tr>)}
            </tbody></table></div>
          ) : <div className="empty-state compact-empty"><h3>No notification events yet</h3><p>Messages for employee onboarding, leave decisions, and payroll actions will appear here.</p></div>}
        </section>}
        {activeTab === 'audit' && isAdmin && <section className="workflow-panel">
          <div className="workflow-panel-heading"><h2>Audit logs</h2><span className="record-count">{auditRows.length} events</span></div>
          {loading ? <div className="page-loading"><span className="loading-ring" /> Loading audit history…</div> : auditRows.length ? (
            <div className="table-responsive custom-table"><table className="table"><thead><tr><th>Timestamp</th><th>Actor user ID</th><th>Action</th><th>Entity</th><th>Entity ID</th><th>Details</th></tr></thead><tbody>
              {auditRows.map((row) => <tr key={row.id}><td>{new Date(row.created_at).toLocaleString()}</td><td>{row.actor_user_id ?? 'System'}</td><td>{row.action}</td><td>{row.entity_type}</td><td>{row.entity_id || '—'}</td><td>{row.details || '—'}</td></tr>)}
            </tbody></table></div>
          ) : <div className="empty-state compact-empty"><h3>No audit events yet</h3><p>Administrative and critical workflow events will appear here.</p></div>}
          <p className="payroll-policy-note">Audit history is read-only. Leave decisions are recorded automatically when approved or rejected.</p>
        </section>}
      </section>
    </div>
  );
}

function AuditLogs() {
  const [rows, setRows] = useState([]);
  const [filter, setFilter] = useState({ actor_user_id: '', action: '', entity_type: '', start_date: '', end_date: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError('');
    const params = Object.fromEntries(Object.entries(filter).filter(([, value]) => value !== ''));
    api.get('/audit-logs', { params })
      .then(({ data }) => { if (active) setRows(data); })
      .catch((e) => { if (active) setError(e.response?.data?.detail || 'Audit history could not be loaded.'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [filter]);

  return (
    <div className="workspace-page">
      <header className="workspace-page-header"><div><span className="eyebrow">ADMINISTRATION</span><h1>Audit logs</h1><p>Read-only, timestamped history of key HRMS and administrative activity.</p></div><Link className="page-home-link" to="/">← Back to overview</Link></header>
      {error && <div className="dashboard-error" role="alert">{error}</div>}
      <section className="record-section">
        <div className="record-section-heading"><div><span className="eyebrow">ACTIVITY HISTORY</span><h2>Recent events</h2></div><span className="record-count">{rows.length} events</span></div>
        <div className="attendance-period report-filters">
          <label>Actor user ID<input type="number" min="1" value={filter.actor_user_id} onChange={(event) => setFilter({ ...filter, actor_user_id: event.target.value })} /></label>
          <label>Action<input value={filter.action} placeholder="e.g. payroll.generated" onChange={(event) => setFilter({ ...filter, action: event.target.value })} /></label>
          <label>Entity type<input value={filter.entity_type} placeholder="e.g. employee" onChange={(event) => setFilter({ ...filter, entity_type: event.target.value })} /></label>
          <label>From<input type="date" value={filter.start_date} onChange={(event) => setFilter({ ...filter, start_date: event.target.value })} /></label>
          <label>To<input type="date" value={filter.end_date} onChange={(event) => setFilter({ ...filter, end_date: event.target.value })} /></label>
          <button className="employee-secondary-button" type="button" onClick={() => setFilter({ actor_user_id: '', action: '', entity_type: '', start_date: '', end_date: '' })}>Clear filters</button>
        </div>
        {loading ? <div className="page-loading"><span className="loading-ring" /> Loading audit history…</div> : rows.length ? (
          <div className="table-responsive custom-table"><table className="table"><thead><tr><th>Timestamp</th><th>Actor user ID</th><th>Action</th><th>Entity</th><th>Entity ID</th><th>Details</th></tr></thead><tbody>
            {rows.map((row) => <tr key={row.id}><td>{new Date(row.created_at).toLocaleString()}</td><td>{row.actor_user_id ?? 'System'}</td><td>{row.action}</td><td>{row.entity_type}</td><td>{row.entity_id || '—'}</td><td>{row.details || '—'}</td></tr>)}
          </tbody></table></div>
        ) : <div className="empty-state compact-empty"><h3>No matching audit events</h3><p>Administrative and critical workflow events will appear here.</p></div>}
        <p className="payroll-policy-note">Read-only access through this panel and API; no edit or delete operation is exposed.</p>
      </section>
    </div>
  );
}

function AdminAccessPanel() {
  const [users, setUsers] = useState([]);
  const [roles, setRoles] = useState([]);
  const [activeTab, setActiveTab] = useState('users');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [loading, setLoading] = useState(true);
  const [savingUser, setSavingUser] = useState(null);

  useEffect(() => {
    let active = true;
    Promise.all([api.get('/admin/users'), api.get('/admin/roles')])
      .then(([userResult, roleResult]) => {
        if (active) {
          setUsers(userResult.data);
          setRoles(roleResult.data.roles);
        }
      })
      .catch((e) => { if (active) setError(e.response?.data?.detail || 'Access settings could not be loaded.'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  async function changeRole(user, role) {
    setSavingUser(user.id);
    setError('');
    setNotice('');
    try {
      const { data: updated } = await api.patch(`/admin/users/${user.id}/role`, { role });
      setUsers((current) => current.map((row) => row.id === updated.id ? { ...row, ...updated } : row));
      setNotice(`Role updated for ${updated.email}.`);
    } catch (e) {
      setError(e.response?.data?.detail || 'Role could not be updated.');
    } finally {
      setSavingUser(null);
    }
  }

  const permissionDetails = {
    manage_users: 'Create accounts and assign user roles',
    manage_employees: 'Add, update, activate and deactivate employees; upload documents',
    create_employee: 'Create employee accounts',
    correct_attendance: 'Correct attendance records (admin override)',
    review_leave: 'Approve or reject leave requests',
    generate_payroll: 'Prepare payroll records',
    adjust_payroll: 'Update payroll calculations and deductions',
    download_all_salary_slips: 'Download salary slips for all employees',
    view_reports: 'View and export workforce reports',
    view_attendance: 'View attendance of all employees',
    view_own_profile: 'View own profile and documents',
    manage_own_attendance: 'Check in, check out, and view own attendance',
    apply_for_leave: 'Apply for leave and view leave balances',
    view_own_payroll: 'View own payroll history',
    download_own_salary_slips: 'Download own salary slips',
  };
  const permissionNames = Object.keys(permissionDetails);

  return (
    <div className="workspace-page access-management-page">
      <header className="workspace-page-header"><div><h1>Users, roles &amp; permissions</h1><p>Control who can do what</p></div></header>
      {error && <div className="dashboard-error" role="alert">{error}</div>}
      {notice && <div className="dashboard-error" role="status">{notice}</div>}
      <div className="access-management-tabs" role="tablist" aria-label="User and role settings">
        <button type="button" role="tab" id="users-tab" aria-selected={activeTab === 'users'} aria-controls="users-panel" className={activeTab === 'users' ? 'active' : ''} onClick={() => setActiveTab('users')}>Users</button>
        <button type="button" role="tab" id="permissions-tab" aria-selected={activeTab === 'permissions'} aria-controls="permissions-panel" className={activeTab === 'permissions' ? 'active' : ''} onClick={() => setActiveTab('permissions')}>Role permissions</button>
      </div>
      {activeTab === 'users' ? (
        <section className="record-section access-management-panel" id="users-panel" role="tabpanel" aria-labelledby="users-tab">
          <div className="record-section-heading"><div><span className="eyebrow">ACCOUNT ACCESS</span><h2>Users</h2></div><span className="record-count">{users.length} accounts</span></div>
          {loading ? <div className="page-loading"><span className="loading-ring" /> Loading accounts…</div> : (
            <div className="table-responsive custom-table"><table className="table"><thead><tr><th>Account</th><th>Employee</th><th>Status</th><th>Role</th></tr></thead><tbody>
              {users.map((user) => <tr key={user.id}><td>{user.email}</td><td>{user.employee_name || 'No employee profile'}</td><td><span className={`status-pill ${user.is_active ? 'active' : 'inactive'}`}>{user.is_active ? 'Active' : 'Inactive'}</span></td><td><select aria-label={`Role for ${user.email}`} value={user.role} disabled={savingUser === user.id} onChange={(event) => changeRole(user, event.target.value)}><option value="admin">Admin</option><option value="hr">HR</option><option value="employee">Employee</option></select></td></tr>)}
            </tbody></table></div>
          )}
        </section>
      ) : (
        <section className="access-management-panel" id="permissions-panel" role="tabpanel" aria-labelledby="permissions-tab">
          {loading ? <div className="page-loading"><span className="loading-ring" /> Loading role permissions…</div> : (
            <div className="table-responsive custom-table access-permission-table">
              <table className="table">
                <thead><tr><th>Permission</th><th>Admin</th><th>HR</th><th>Employee</th></tr></thead>
                <tbody>
                  {permissionNames.map((permission) => (
                    <tr key={permission}>
                      <td><code>{permission}</code><span>{permissionDetails[permission]}</span></td>
                      {['admin', 'hr', 'employee'].map((role) => {
                        const enabled = roles.find((item) => item.role === role)?.permissions.includes(permission) || false;
                        return <td key={role}>{enabled ? <span className="permission-check" aria-label={`${role} has permission`}>✓</span> : <span className="permission-denied" aria-label={`${role} does not have permission`}>—</span>}</td>;
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <p className="payroll-policy-note">Role permissions are built in and read-only. Change a user’s assigned role from the Users tab.</p>
        </section>
      )}
    </div>
  );
}

function ReportsPanel({ role }) {
  const isHRStaff = role === 'admin' || role === 'hr';
  const today = new Date();
  const todayDate = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
  const previousMonth = new Date(today.getFullYear(), today.getMonth() - 1, 1);
  const [startDate, setStartDate] = useState(`${previousMonth.getFullYear()}-${String(previousMonth.getMonth() + 1).padStart(2, '0')}-01`);
  const [endDate, setEndDate] = useState(todayDate);
  const [departmentId, setDepartmentId] = useState('');
  const [reportName, setReportName] = useState('payroll');
  const [departments, setDepartments] = useState([]);
  const [columns, setColumns] = useState([]);
  const [rows, setRows] = useState([]);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState('');
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    if (!isHRStaff) return undefined;
    api.get('/departments')
      .then(({ data }) => setDepartments(data))
      .catch((e) => setError(e.response?.data?.detail || 'Departments could not be loaded.'));
    return undefined;
  }, [isHRStaff]);

  useEffect(() => {
    let active = true;
    async function loadReport() {
      setBusy('report');
      setError('');
      try {
        let responseData;
        if (isHRStaff) {
          const response = await api.get(`/reports/${reportName}/data`, {
            params: { start_date: startDate, end_date: endDate, ...(departmentId ? { department_id: departmentId } : {}) },
          });
          responseData = response.data;
        } else {
          const [profileResult, result] = await Promise.all([
            api.get('/employees/me'),
            reportName === 'attendance'
              ? Promise.all((() => {
                const months = [];
                const start = new Date(`${startDate}T00:00:00`);
                const end = new Date(`${endDate}T00:00:00`);
                for (let cursor = new Date(start.getFullYear(), start.getMonth(), 1); cursor <= end; cursor.setMonth(cursor.getMonth() + 1)) {
                  months.push(api.get('/attendance/me', { params: { month: cursor.getMonth() + 1, year: cursor.getFullYear() } }));
                }
                return months;
              })())
              : api.get(reportName === 'leaves' ? '/leaves/me' : '/payroll/me'),
          ]);
          const profile = profileResult.data;
          const inRange = (value) => value >= startDate && value <= endDate;
          if (reportName === 'attendance') {
            const records = result.flatMap((response) => response.data.records || [])
              .filter((record) => inRange(String(record.work_date)));
            responseData = {
              columns: ['Employee code', 'Employee name', 'Date', 'Check in', 'Check out', 'Working minutes', 'Status'],
              rows: records.map((record) => [
                profile.employee_code,
                profile.full_name,
                record.work_date,
                record.check_in ? new Date(record.check_in).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '',
                record.check_out ? new Date(record.check_out).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '',
                record.working_minutes,
                record.status,
              ]),
            };
          } else if (reportName === 'leaves') {
            const records = result.data.filter((leave) => String(leave.start_date) <= endDate && String(leave.end_date) >= startDate);
            responseData = {
              columns: ['Employee code', 'Employee name', 'Department', 'Leave type', 'Start date', 'End date', 'Days', 'Status', 'Reason'],
              rows: records.map((leave) => [
                profile.employee_code, profile.full_name, profile.department_name || '',
                leave.leave_type, leave.start_date, leave.end_date, leave.days, leave.status, leave.reason,
              ]),
            };
          } else {
            const records = result.data.filter((payroll) => {
              const period = `${payroll.year}-${String(payroll.month).padStart(2, '0')}`;
              const payrollStart = `${period}-01`;
              const payrollEndDate = new Date(Number(payroll.year), Number(payroll.month), 0).getDate();
              const payrollEnd = `${period}-${String(payrollEndDate).padStart(2, '0')}`;
              return payrollStart <= endDate && payrollEnd >= startDate;
            });
            responseData = {
              columns: ['Period', 'Employee code', 'Employee name', 'Department', 'Gross salary', 'LOP deduction', 'PF', 'Professional tax', 'TDS', 'Adjustments', 'Net salary', 'Status'],
              rows: records.map((payroll) => [
                `${payroll.year}-${String(payroll.month).padStart(2, '0')}`,
                profile.employee_code, profile.full_name, profile.department_name || '',
                payroll.gross_salary, payroll.lop_deduction, payroll.pf_deduction,
                payroll.professional_tax, payroll.tds_deduction, payroll.manual_adjustment_total,
                payroll.net_salary, payroll.locked ? 'GENERATED' : 'DRAFT',
              ]),
            };
          }
        }
        if (active) {
          setColumns(responseData.columns || []);
          setRows(responseData.rows || []);
        }
      } catch (e) {
        if (active) {
          setColumns([]);
          setRows([]);
          setError(e.response?.data?.detail || 'Report could not be loaded.');
        }
      } finally {
        if (active) setBusy('');
      }
    }
    loadReport();
    return () => { active = false; };
  }, [isHRStaff, refreshKey, reportName]);

  function runReport() {
    if (!startDate || !endDate || startDate > endDate) {
      setError('Choose a valid date range.');
      return;
    }
    setRefreshKey((key) => key + 1);
  }

  async function download(format) {
    if (!isHRStaff) return;
    if (!startDate || !endDate || startDate > endDate) {
      setError('Choose a valid date range.');
      return;
    }
    setBusy(format);
    setError('');
    try {
      const response = await api.get(`/reports/${reportName}.${format}`, {
        params: { start_date: startDate, end_date: endDate, ...(departmentId ? { department_id: departmentId } : {}) },
        responseType: 'blob',
      });
      const url = URL.createObjectURL(response.data);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${reportName}-report.${format}`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e.response?.data?.detail || 'Report could not be downloaded.');
    } finally {
      setBusy('');
    }
  }

  const moneyColumns = new Set([
    'Gross salary', 'LOP deduction', 'PF', 'Professional tax', 'TDS', 'Adjustments', 'Net salary',
  ]);
  const reportTitle = reportName === 'payroll' ? 'Payroll Summary' : reportName === 'leaves' ? 'Leave Report' : 'Attendance Report';
  function displayCell(value, column) {
    if (value === null || value === undefined || value === '') return '—';
    if (column === 'Period' && /^\d{4}-\d{2}$/.test(String(value))) {
      const [year, month] = String(value).split('-');
      return `${new Date(Number(year), Number(month) - 1, 1).toLocaleString('en', { month: 'short' })} ${year}`;
    }
    if (moneyColumns.has(column) && Number.isFinite(Number(value))) {
      return Number(value).toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
    }
    if (typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value)) {
      const [year, month, day] = value.split('-');
      return `${day}/${month}/${year}`;
    }
    return String(value);
  }
  const totals = columns.map((column, columnIndex) => (
    moneyColumns.has(column)
      ? rows.reduce((sum, row) => sum + (Number(row[columnIndex]) || 0), 0)
      : null
  ));

  return (
    <div className="workspace-page reports-page">
      <header className="reports-header"><div><h1>Reports &amp; analytics</h1><p>{isHRStaff ? 'Filter by date range and department, then export' : 'Your attendance, leave, and payroll records for the selected dates'}</p></div>{isHRStaff && <div className="reports-export-actions"><button disabled={Boolean(busy)} onClick={() => download('csv')}>{busy === 'csv' ? 'Preparing…' : 'Export CSV'}</button><button disabled={Boolean(busy)} onClick={() => download('pdf')}>{busy === 'pdf' ? 'Preparing…' : 'Export PDF'}</button></div>}</header>
      {error && <div className="dashboard-error" role="alert">{error}</div>}
      <section className="reports-workspace">
        <div className="reports-tabs" role="tablist" aria-label="Report type">
          {[
            ['attendance', 'Attendance'],
            ['leaves', 'Leave'],
            ['payroll', 'Payroll summary'],
          ].map(([value, label]) => <button key={value} type="button" role="tab" aria-selected={reportName === value} className={reportName === value ? 'active' : ''} onClick={() => { setReportName(value); setRefreshKey((key) => key + 1); }}>{label}</button>)}
        </div>
        <div className="reports-filters">
          <label>From<input type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} /></label>
          <label>To<input type="date" value={endDate} onChange={(event) => setEndDate(event.target.value)} /></label>
          {isHRStaff && <label>Department<select value={departmentId} onChange={(event) => setDepartmentId(event.target.value)}><option value="">All departments</option>{departments.map((department) => <option value={department.id} key={department.id}>{department.name}</option>)}</select></label>}
          <button className="reports-run-button" type="button" disabled={Boolean(busy)} onClick={runReport}>{busy === 'report' ? 'Loading…' : 'Run report'}</button>
        </div>
        <section className="reports-table-card" aria-live="polite">
          <div className="reports-table-heading"><h2>{reportTitle} · {rows.length} row{rows.length === 1 ? '' : 's'}</h2></div>
          {busy === 'report' && !columns.length ? <div className="reports-loading">Loading report…</div> : columns.length ? (
            <div className="reports-table-scroll">
              <table className="reports-table">
                <thead><tr>{columns.map((column) => <th key={column} className={moneyColumns.has(column) ? 'numeric' : ''}>{column}</th>)}</tr></thead>
                <tbody>
                  {rows.map((row, rowIndex) => <tr key={`${reportName}-${rowIndex}`}>{columns.map((column, columnIndex) => <td key={column} className={`${moneyColumns.has(column) ? 'numeric ' : ''}${column === 'Status' ? 'report-status' : ''}`}>{displayCell(row[columnIndex], column)}</td>)}</tr>)}
                  {!rows.length && <tr><td className="reports-empty" colSpan={columns.length}>No {reportName === 'payroll' ? 'payroll' : reportName} records found for the selected filters.</td></tr>}
                </tbody>
                {isHRStaff && reportName === 'payroll' && rows.length > 0 && <tfoot><tr>{columns.map((column, columnIndex) => <td key={column} className={moneyColumns.has(column) ? 'numeric' : ''}>{moneyColumns.has(column) ? displayCell(totals[columnIndex], column) : column === 'Employee name' ? 'TOTAL' : ''}</td>)}</tr></tfoot>}
              </table>
            </div>
          ) : null}
        </section>
      </section>
    </div>
  );
}

function EmployeeDirectory() {
  const [employees, setEmployees] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [search, setSearch] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [addEmployeeOpen, setAddEmployeeOpen] = useState(false);
  const blankEmployee = {
    email: '',
    temporary_password: '',
    employee_code: '',
    full_name: '',
    department_id: '',
    designation: '',
    joining_date: new Date().toISOString().slice(0, 10),
    basic_salary: '0',
    hra: '0',
    special_allowance: '0',
    pf_percentage: '0',
    professional_tax: '0',
    tds: '0',
    phone: '',
    date_of_birth: '',
    address: '',
    emergency_contact_name: '',
    emergency_contact_relationship: '',
    emergency_contact_phone: '',
  };
  const [form, setForm] = useState(blankEmployee);

  useEffect(() => {
    let active = true;
    api.get('/employees/directory')
      .then(({ data }) => { if (active) setEmployees(data); })
      .catch((e) => { if (active) setError(e.response?.data?.detail || 'Employee directory could not be loaded.'); })
      .finally(() => { if (active) setLoading(false); });
    api.get('/departments')
      .then(({ data }) => { if (active) setDepartments(data); })
      .catch((e) => { if (active) setError(e.response?.data?.detail || 'Departments could not be loaded.'); });
    return () => { active = false; };
  }, []);

  async function createEmployee(event) {
    event.preventDefault();
    setError('');
    setNotice('');
    setBusy(true);
    const basicSalary = Number(form.basic_salary);
    const hra = Number(form.hra);
    const specialAllowance = Number(form.special_allowance);
    const payload = {
      ...form,
      department_id: form.department_id ? Number(form.department_id) : null,
      basic_salary: basicSalary,
      hra,
      special_allowance: specialAllowance,
      monthly_salary: basicSalary + hra + specialAllowance,
      pf_percentage: Number(form.pf_percentage),
      professional_tax: Number(form.professional_tax),
      tds: Number(form.tds),
      phone: form.phone.trim() || null,
      date_of_birth: form.date_of_birth || null,
      address: form.address.trim() || null,
      emergency_contact_name: form.emergency_contact_name.trim() || null,
      emergency_contact_relationship: form.emergency_contact_relationship.trim() || null,
      emergency_contact_phone: form.emergency_contact_phone.trim() || null,
    };
    try {
      const { data } = await api.post('/employees', payload);
      const department = departments.find((item) => item.id === data.department_id);
      setEmployees((current) => [{
        id: data.id,
        employee_code: data.employee_code,
        full_name: data.full_name,
        department_name: department?.name || null,
        designation: data.designation,
        role: data.role,
        is_active: data.is_active,
      }, ...current]);
      setNotice(`Employee ${data.full_name} was created. Share the temporary password securely.`);
      setForm(blankEmployee);
      setAddEmployeeOpen(false);
    } catch (e) {
      setError(e.response?.data?.detail || 'Employee details could not be saved.');
    } finally {
      setBusy(false);
    }
  }

  function updateForm(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  const filteredEmployees = employees.filter((employee) => [
    employee.employee_code,
    employee.full_name,
    employee.department_name,
    employee.designation,
  ].some((value) => String(value || '').toLowerCase().includes(search.trim().toLowerCase())));
  const departmentNames = [...new Set(employees.map((employee) => employee.department_name).filter(Boolean))];

  return (
    <div className="workspace-page employee-directory-page">
      <header className="workspace-page-header">
        <div><h1>Employees</h1><p>Browse employee names, teams, and roles.</p></div>
        <button
          className="employee-primary-button"
          type="button"
          onClick={() => { setForm(blankEmployee); setError(''); setNotice(''); setAddEmployeeOpen(true); }}
        >
          ＋ Add employee
        </button>
      </header>
      {error && <div className="dashboard-error" role="alert">{error}</div>}
      {notice && <div className="alert alert-success" role="status">{notice}</div>}
      {addEmployeeOpen && (
        <div className="employee-dialog-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget && !busy) setAddEmployeeOpen(false); }}>
          <section className="employee-dialog employee-directory-dialog" role="dialog" aria-modal="true" aria-labelledby="employee-directory-add-title">
            <div className="employee-dialog-heading">
              <div><h2 id="employee-directory-add-title">Add employee</h2></div>
              <button type="button" onClick={() => setAddEmployeeOpen(false)} disabled={busy} aria-label="Close">×</button>
            </div>
            {error && <div className="dashboard-error employee-dialog-error" role="alert">{error}</div>}
            <form className="employee-form" onSubmit={createEmployee}>
              <fieldset className="employee-form-group">
                <legend>Personal</legend>
                <label>Full name<input required minLength={2} value={form.full_name} onChange={(event) => updateForm('full_name', event.target.value)} /></label>
                <label>Work email<input required type="email" value={form.email} onChange={(event) => updateForm('email', event.target.value)} /></label>
                <label>Phone<input maxLength={30} value={form.phone} onChange={(event) => updateForm('phone', event.target.value)} /></label>
                <label>Date of birth<input type="date" max={new Date().toISOString().slice(0, 10)} value={form.date_of_birth} onChange={(event) => updateForm('date_of_birth', event.target.value)} /></label>
                <label className="employee-form-wide">Home address<textarea rows="2" maxLength={2000} value={form.address} onChange={(event) => updateForm('address', event.target.value)} /></label>
                <label>Emergency contact<input maxLength={160} value={form.emergency_contact_name} onChange={(event) => updateForm('emergency_contact_name', event.target.value)} /></label>
                <label>Relationship<input maxLength={80} value={form.emergency_contact_relationship} onChange={(event) => updateForm('emergency_contact_relationship', event.target.value)} /></label>
                <label>Emergency contact phone<input type="tel" maxLength={30} value={form.emergency_contact_phone} onChange={(event) => updateForm('emergency_contact_phone', event.target.value)} /></label>
              </fieldset>
              <fieldset className="employee-form-group">
                <legend>Employment</legend>
                <label>Employee code<input required minLength={2} maxLength={30} value={form.employee_code} onChange={(event) => updateForm('employee_code', event.target.value)} /></label>
                <label>Department<select value={form.department_id} onChange={(event) => updateForm('department_id', event.target.value)}><option value="">Unassigned</option>{departments.map((department) => <option key={department.id} value={department.id}>{department.name}</option>)}</select></label>
                <label>Designation<input required minLength={2} value={form.designation} onChange={(event) => updateForm('designation', event.target.value)} /></label>
                <label>Joining date<input required type="date" value={form.joining_date} onChange={(event) => updateForm('joining_date', event.target.value)} /></label>
                <label>System role<select value="employee" disabled><option value="employee">Employee</option></select></label>
              </fieldset>
              <fieldset className="employee-form-group">
                <legend>Monthly salary details</legend>
                <label>Basic salary<input required type="number" min="0" step="0.01" value={form.basic_salary} onChange={(event) => updateForm('basic_salary', event.target.value)} /></label>
                <label>HRA<input required type="number" min="0" step="0.01" value={form.hra} onChange={(event) => updateForm('hra', event.target.value)} /></label>
                <label>Special allowance<input required type="number" min="0" step="0.01" value={form.special_allowance} onChange={(event) => updateForm('special_allowance', event.target.value)} /></label>
                <label>PF (%)<input required type="number" min="0" max="100" step="0.01" value={form.pf_percentage} onChange={(event) => updateForm('pf_percentage', event.target.value)} /></label>
                <label>Professional tax<input required type="number" min="0" step="0.01" value={form.professional_tax} onChange={(event) => updateForm('professional_tax', event.target.value)} /></label>
                <label>TDS<input required type="number" min="0" step="0.01" value={form.tds} onChange={(event) => updateForm('tds', event.target.value)} /></label>
                <label>Monthly gross salary<input readOnly value={currency((Number(form.basic_salary) || 0) + (Number(form.hra) || 0) + (Number(form.special_allowance) || 0))} /></label>
              </fieldset>
              <fieldset className="employee-form-group">
                <legend>Access</legend>
                <label>Temporary password<input required type="password" minLength={10} autoComplete="new-password" value={form.temporary_password} onChange={(event) => updateForm('temporary_password', event.target.value)} /></label>
                <p>New accounts are created with the Employee role. Share the temporary password securely.</p>
              </fieldset>
              <div className="employee-form-actions">
                <button className="employee-primary-button" disabled={busy}>{busy ? 'Saving…' : 'Create employee'}</button>
                <button className="employee-secondary-button" type="button" disabled={busy} onClick={() => setAddEmployeeOpen(false)}>Cancel</button>
              </div>
            </form>
          </section>
        </div>
      )}
      <section className="directory-filters">
        <label className="directory-search">Search employees
          <input type="search" placeholder="Name, employee code, department, or designation" value={search} onChange={(event) => setSearch(event.target.value)} />
        </label>
        <span className="directory-result-count">{loading ? 'Loading…' : `${filteredEmployees.length} employees`}</span>
      </section>
      <div className="table-responsive custom-table employee-directory-table employee-limited-directory-table">
        <table className="table">
          <thead><tr><th>Code</th><th>Name</th><th>Department</th><th>Designation</th><th>Role</th><th>Status</th></tr></thead>
          <tbody>
            {filteredEmployees.map((employee) => (
              <tr key={employee.id}>
                <td>{employee.employee_code}</td>
                <td><strong className="employee-directory-name">{employee.full_name}</strong></td>
                <td>{employee.department_name || '—'}</td>
                <td>{employee.designation}</td>
                <td><span className="employee-role-badge">{employee.role}</span></td>
                <td><span className={`status-pill ${employee.is_active ? 'active' : 'inactive'}`}>{employee.is_active ? 'Active' : 'Inactive'}</span></td>
              </tr>
            ))}
            {!loading && !error && filteredEmployees.length === 0 && (
              <tr><td className="employee-directory-empty" colSpan="6">{search ? 'No employees match your search.' : 'No employees are available in the directory yet.'}</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Employees() {
  const [rows, setRows] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [statusFilter, setStatusFilter] = useState('active');
  const includeInactive = statusFilter !== 'active';
  const [search, setSearch] = useState('');
  const [departmentFilter, setDepartmentFilter] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(null);
  const [formOpen, setFormOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [documents, setDocuments] = useState({});

  const blankEmployee = {
    email: '',
    role: 'employee',
    temporary_password: '',
    employee_code: '',
    full_name: '',
    department_id: '',
    designation: '',
    joining_date: new Date().toISOString().slice(0, 10),
    basic_salary: '0',
    hra: '0',
    special_allowance: '0',
    pf_percentage: '0',
    professional_tax: '0',
    tds: '0',
    phone: '',
    date_of_birth: '',
    address: '',
    emergency_contact_name: '',
    emergency_contact_relationship: '',
    emergency_contact_phone: '',
  };
  const [form, setForm] = useState(blankEmployee);

  async function loadEmployees() {
    setError('');
    setLoading(true);
    try {
      const [employeeResult, departmentResult] = await Promise.all([
        api.get('/employees', { params: { include_inactive: includeInactive } }),
        api.get('/departments'),
      ]);
      setRows(employeeResult.data);
      setDepartments(departmentResult.data);
    } catch (e) {
      setError(e.response?.data?.detail || 'Unable to load employees and departments.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadEmployees(); }, [includeInactive]);

  function startEdit(employee) {
    setEditing(employee.id);
    setFormOpen(true);
    setForm({
      email: employee.email || '',
      role: employee.role || 'employee',
      employee_code: employee.employee_code,
      full_name: employee.full_name,
      department_id: employee.department_id ?? '',
      designation: employee.designation,
      joining_date: employee.joining_date,
      basic_salary: employee.basic_salary ?? employee.monthly_salary,
      hra: employee.hra ?? '0',
      special_allowance: employee.special_allowance ?? '0',
      pf_percentage: employee.pf_percentage ?? '0',
      professional_tax: employee.professional_tax ?? '0',
      tds: employee.tds ?? '0',
      phone: employee.phone || '',
      date_of_birth: employee.date_of_birth || '',
      address: employee.address || '',
      emergency_contact_name: employee.emergency_contact_name || '',
      emergency_contact_relationship: employee.emergency_contact_relationship || '',
      emergency_contact_phone: employee.emergency_contact_phone || '',
      is_active: employee.is_active,
    });
    setNotice('');
  }

  function resetForm() {
    setEditing(null);
    setForm(blankEmployee);
    setFormOpen(false);
  }

  async function saveEmployee(event) {
    event.preventDefault();
    setBusy(true);
    setNotice('');
    setError('');
    const payload = {
      ...form,
      department_id: form.department_id ? Number(form.department_id) : null,
      basic_salary: Number(form.basic_salary),
      hra: Number(form.hra),
      special_allowance: Number(form.special_allowance),
      monthly_salary: Number(form.basic_salary) + Number(form.hra) + Number(form.special_allowance),
      pf_percentage: Number(form.pf_percentage),
      professional_tax: Number(form.professional_tax),
      tds: Number(form.tds),
      phone: form.phone.trim() || null,
      date_of_birth: form.date_of_birth || null,
      address: form.address.trim() || null,
      emergency_contact_name: form.emergency_contact_name.trim() || null,
      emergency_contact_relationship: form.emergency_contact_relationship.trim() || null,
      emergency_contact_phone: form.emergency_contact_phone.trim() || null,
    };
    try {
      if (editing) {
        delete payload.temporary_password;
        await api.patch(`/employees/${editing}`, payload);
        setNotice('Employee details updated.');
      } else {
        await api.post('/employees', payload);
        setNotice('Employee profile created. Share the temporary password securely.');
      }
      resetForm();
      await loadEmployees();
    } catch (e) {
      setError(e.response?.data?.detail || 'Employee details could not be saved.');
    } finally {
      setBusy(false);
    }
  }

  async function deactivateEmployee(employee) {
    if (!window.confirm(`Deactivate ${employee.full_name}? They will no longer be able to sign in.`)) return;
    setError('');
    setNotice('');
    try {
      await api.delete(`/employees/${employee.id}`);
      setNotice(`${employee.full_name} was deactivated.`);
      await loadEmployees();
    } catch (e) {
      setError(e.response?.data?.detail || 'Employee could not be deactivated.');
    }
  }

  async function toggleEmployee(employee) {
    if (employee.is_active) return deactivateEmployee(employee);
    setError('');
    setNotice('');
    try {
      await api.patch(`/employees/${employee.id}`, { is_active: true });
      setNotice(`${employee.full_name} was reactivated.`);
      await loadEmployees();
    } catch (e) {
      setError(e.response?.data?.detail || 'Employee could not be reactivated.');
    }
  }

  async function uploadDocument(employeeId, file) {
    if (!file) return;
    setError('');
    setNotice('');
    const body = new FormData();
    body.append('file', file);
    try {
      await api.post(`/employees/${employeeId}/documents`, body);
      setNotice('Employee document uploaded.');
      await loadDocuments(employeeId);
    } catch (e) {
      setError(e.response?.data?.detail || 'Document upload failed.');
    }
  }

  async function loadDocuments(employeeId) {
    try {
      const { data } = await api.get(`/employees/${employeeId}/documents`);
      setDocuments((current) => ({ ...current, [employeeId]: data }));
    } catch (e) {
      setError(e.response?.data?.detail || 'Could not load employee documents.');
    }
  }

  async function downloadDocument(employeeId, employeeDocument) {
    try {
      const response = await api.get(`/employees/${employeeId}/documents/${employeeDocument.id}`, { responseType: 'blob' });
      const url = URL.createObjectURL(response.data);
      const link = document.createElement('a');
      link.href = url;
      link.download = employeeDocument.original_name;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e) {
      setError(e.response?.data?.detail || 'Document could not be downloaded.');
    }
  }

  const pageSize = 10;
  const filteredEmployees = rows.filter((employee) => {
    const query = search.trim().toLowerCase();
    const matchesSearch = !query || [
      employee.full_name,
      employee.employee_code,
      employee.email,
      employee.designation,
    ].some((value) => String(value || '').toLowerCase().includes(query));
    const matchesDepartment = !departmentFilter || String(employee.department_id || '') === departmentFilter;
    const matchesStatus = statusFilter === 'all' || (statusFilter === 'active' ? employee.is_active : !employee.is_active);
    return matchesSearch && matchesDepartment && matchesStatus;
  });
  const pageCount = Math.max(1, Math.ceil(filteredEmployees.length / pageSize));
  const visibleEmployees = filteredEmployees.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  return (
    <div className="workspace-page employee-directory-page">
      <header className="workspace-page-header">
        <div><h1>Employees</h1><p>Onboard and manage employee records.</p></div>
        <div className="employee-directory-header-actions">
          <button className="employee-primary-button" type="button" onClick={() => { resetForm(); setError(''); setNotice(''); setFormOpen(true); }}>＋ Add employee</button>
        </div>
      </header>
      {error && <div className="alert alert-warning">{error}</div>}
      {notice && <div className="alert alert-success" role="status">{notice}</div>}
      {formOpen && <div className="employee-dialog-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget && !busy) resetForm(); }}>
        <section className="employee-dialog employee-directory-dialog" role="dialog" aria-modal="true" aria-labelledby="employee-dialog-title">
          <div className="employee-dialog-heading"><div><h2 id="employee-dialog-title">{editing ? 'Edit employee' : 'Add employee'}</h2></div><button type="button" onClick={resetForm} disabled={busy} aria-label="Close">×</button></div>
          {error && <div className="dashboard-error employee-dialog-error" role="alert">{error}</div>}
          <form className="employee-form" onSubmit={saveEmployee}>
          <fieldset className="employee-form-group">
            <legend>Personal</legend>
            <label>Full name<input required minLength={2} value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} /></label>
            <label>Work email<input required type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></label>
            <label>Phone<input maxLength={30} value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></label>
            <label>Date of birth<input type="date" max={new Date().toISOString().slice(0, 10)} value={form.date_of_birth} onChange={(e) => setForm({ ...form, date_of_birth: e.target.value })} /></label>
            <label className="employee-form-wide">Home address<textarea rows="2" maxLength={2000} value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} /></label>
            <label>Emergency contact<input maxLength={160} value={form.emergency_contact_name} onChange={(e) => setForm({ ...form, emergency_contact_name: e.target.value })} /></label>
            <label>Relationship<input maxLength={80} value={form.emergency_contact_relationship} onChange={(e) => setForm({ ...form, emergency_contact_relationship: e.target.value })} /></label>
            <label>Emergency contact phone<input type="tel" maxLength={30} value={form.emergency_contact_phone} onChange={(e) => setForm({ ...form, emergency_contact_phone: e.target.value })} /></label>
          </fieldset>
          <fieldset className="employee-form-group">
            <legend>Employment</legend>
            <label>Employee code<input required minLength={2} maxLength={30} value={form.employee_code} onChange={(e) => setForm({ ...form, employee_code: e.target.value })} /></label>
            <label>Department<select value={form.department_id} onChange={(e) => setForm({ ...form, department_id: e.target.value })}><option value="">Unassigned</option>{departments.map((department) => <option key={department.id} value={department.id}>{department.name}</option>)}</select></label>
            <label>Designation<input required minLength={2} value={form.designation} onChange={(e) => setForm({ ...form, designation: e.target.value })} /></label>
            <label>Joining date<input required type="date" value={form.joining_date} onChange={(e) => setForm({ ...form, joining_date: e.target.value })} /></label>
          </fieldset>
          <fieldset className="employee-form-group">
            <legend>Monthly salary details</legend>
            <label>Basic salary<input required type="number" min="0" step="0.01" value={form.basic_salary} onChange={(e) => setForm({ ...form, basic_salary: e.target.value })} /></label>
            <label>HRA<input required type="number" min="0" step="0.01" value={form.hra} onChange={(e) => setForm({ ...form, hra: e.target.value })} /></label>
            <label>Special allowance<input required type="number" min="0" step="0.01" value={form.special_allowance} onChange={(e) => setForm({ ...form, special_allowance: e.target.value })} /></label>
            <label>PF (%)<input required type="number" min="0" max="100" step="0.01" value={form.pf_percentage} onChange={(e) => setForm({ ...form, pf_percentage: e.target.value })} /></label>
            <label>Professional tax<input required type="number" min="0" step="0.01" value={form.professional_tax} onChange={(e) => setForm({ ...form, professional_tax: e.target.value })} /></label>
            <label>TDS<input required type="number" min="0" step="0.01" value={form.tds} onChange={(e) => setForm({ ...form, tds: e.target.value })} /></label>
            <label>Monthly gross salary<input readOnly value={currency((Number(form.basic_salary) || 0) + (Number(form.hra) || 0) + (Number(form.special_allowance) || 0))} /></label>
          </fieldset>
          <fieldset className="employee-form-group">
            <legend>Access</legend>
            {!editing && <label>Temporary password<input required type="password" minLength={10} autoComplete="new-password" value={form.temporary_password} onChange={(e) => setForm({ ...form, temporary_password: e.target.value })} /></label>}
            <label>System role<select value={form.role || 'employee'} disabled><option value="employee">Employee</option><option value="hr">HR</option><option value="admin">Admin</option></select></label>
            {editing && <label className="employee-active-field"><input type="checkbox" checked={Boolean(form.is_active)} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} /> Active account</label>}
            <p>New employee accounts are created with the Employee role. Admins can change roles from Users &amp; roles.</p>
          </fieldset>
            <div className="employee-form-actions"><button className="employee-primary-button" disabled={busy}>{busy ? 'Saving…' : editing ? 'Save changes' : 'Create employee'}</button><button className="employee-secondary-button" type="button" disabled={busy} onClick={resetForm}>Cancel</button></div>
          </form>
        </section>
      </div>}
      <section className="directory-filters">
        <label className="directory-search">Search<input type="search" placeholder="Name, email, or employee code" value={search} onChange={(event) => { setSearch(event.target.value); setCurrentPage(1); }} /></label>
        <label>Department<select value={departmentFilter} onChange={(event) => { setDepartmentFilter(event.target.value); setCurrentPage(1); }}><option value="">All departments</option>{departments.map((department) => <option key={department.id} value={department.id}>{department.name}</option>)}</select></label>
        <label>Status<select value={statusFilter} onChange={(event) => { setStatusFilter(event.target.value); setCurrentPage(1); }}><option value="active">Active</option><option value="inactive">Inactive</option><option value="all">All statuses</option></select></label>
        <span className="directory-result-count">{loading ? 'Loading…' : `${filteredEmployees.length} employees`}</span>
      </section>
      <div className="table-responsive custom-table employee-directory-table">
        <table className="table table-hover mb-0">
          <thead>
            <tr>
              <th>Code</th>
              <th>Name</th>
              <th>Department</th>
              <th>Designation</th>
              <th>Role</th>
              <th>Joining date</th>
              <th>Gross / month</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {visibleEmployees.map((e) => (
              <React.Fragment key={e.id}>
              <tr>
                <td>{e.employee_code}</td>
                <td><strong className="employee-directory-name">{e.full_name}</strong><small className="employee-directory-email">{e.email}</small></td>
                <td>{e.department_name || departments.find((department) => department.id === e.department_id)?.name || '—'}</td>
                <td>{e.designation}</td>
                <td><span className="employee-role-badge">{e.role || 'employee'}</span></td>
                <td>{new Intl.DateTimeFormat('en', { day: '2-digit', month: 'short', year: 'numeric' }).format(new Date(`${e.joining_date}T00:00:00`))}</td>
                <td>{currency(e.monthly_salary)}</td>
                <td><span className={`status-pill ${e.is_active ? 'active' : 'inactive'}`}>{e.is_active ? 'Active' : 'Inactive'}</span></td>
                <td><div className="employee-row-actions">
                  <Link to={`/employees/${e.id}`}>View details</Link>
                  <button type="button" onClick={() => startEdit(e)}>Edit</button>
                  <button type="button" onClick={() => toggleEmployee(e)}>{e.is_active ? 'Deactivate' : 'Reactivate'}</button>
                  <label className="document-upload-button">Upload document<input type="file" accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png" onChange={(event) => { uploadDocument(e.id, event.target.files?.[0]); event.target.value = ''; }} /></label>
                  <button type="button" onClick={() => loadDocuments(e.id)}>Documents</button>
                </div></td>
              </tr>
              {documents[e.id] && <tr className="employee-documents-row"><td colSpan="9"><strong>Documents for {e.full_name}</strong>{documents[e.id].length ? documents[e.id].map((doc) => <button type="button" key={doc.id} onClick={() => downloadDocument(e.id, doc)}>{doc.original_name} · Download</button>) : <span>No documents uploaded yet.</span>}</td></tr>}
              </React.Fragment>
            ))}
          </tbody>
        </table>
        {loading && <p className="p-3 text-secondary">Loading employees…</p>}
        {!loading && !filteredEmployees.length && !error && <p className="p-3 text-secondary">{rows.length ? 'No employees match these filters.' : 'No employees yet.'}</p>}
      </div>
      {pageCount > 1 && <nav className="directory-pagination" aria-label="Employee list pages"><button type="button" disabled={currentPage === 1} onClick={() => setCurrentPage((page) => page - 1)}>Previous</button><span>Page {currentPage} of {pageCount}</span><button type="button" disabled={currentPage === pageCount} onClick={() => setCurrentPage((page) => page + 1)}>Next</button></nav>}
    </div>
  );
}

function EmployeeDetails() {
  const { employeeId } = useParams();
  const [employee, setEmployee] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError('');
    api.get(`/employees/${employeeId}`)
      .then(({ data }) => { if (active) setEmployee(data); })
      .catch((e) => { if (active) setError(e.response?.data?.detail || 'Employee details could not be loaded.'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [employeeId]);

  const displayDate = (value) => value
    ? new Intl.DateTimeFormat('en', { month: 'long', day: 'numeric', year: 'numeric' }).format(new Date(`${value}T00:00:00`))
    : 'Not added';
  const show = (value) => value || 'Not added';

  return (
    <div className="workspace-page">
      <header className="workspace-page-header">
        <div><span className="eyebrow">PEOPLE OPERATIONS</span><h1>Employee details</h1><p>Employment, contact, and emergency information.</p></div>
        <Link className="page-home-link" to="/employees">← Back to employee directory</Link>
      </header>
      {loading ? <div className="page-loading"><span className="loading-ring" /> Loading employee details…</div>
        : error ? <div className="dashboard-error" role="alert">{error}</div>
          : employee && <>
            <section className="profile-hero">
              <div className="profile-avatar">{employee.full_name?.split(' ').map((part) => part[0]).join('').slice(0, 2) || 'TM'}</div>
              <div className="profile-identity"><span className="banner-kicker">{employee.employee_code}</span><h2>{employee.full_name}</h2><p>{employee.designation}{employee.department_name ? ` · ${employee.department_name}` : ''}</p></div>
              <span className={`status-pill ${employee.is_active ? 'active' : 'inactive'}`}>{employee.is_active ? 'Active' : 'Inactive'}</span>
            </section>
            <section className="record-section">
              <div className="record-section-heading"><div><span className="eyebrow">EMPLOYMENT</span><h2>Work details</h2></div></div>
              <div className="profile-details employee-detail-grid">
                <div><small>WORK EMAIL</small><strong>{show(employee.email)}</strong></div>
                <div><small>EMPLOYEE ID</small><strong>{show(employee.employee_code)}</strong></div>
                <div><small>DEPARTMENT</small><strong>{show(employee.department_name)}</strong></div>
                <div><small>DESIGNATION</small><strong>{show(employee.designation)}</strong></div>
                <div><small>JOINED</small><strong>{displayDate(employee.joining_date)}</strong></div>
                <div><small>STATUS</small><strong>{employee.is_active ? 'Active' : 'Inactive'}</strong></div>
              </div>
            </section>
            <section className="record-section">
              <div className="record-section-heading"><div><span className="eyebrow">PERSONAL</span><h2>Contact details</h2></div></div>
              <div className="profile-details employee-detail-grid">
                <div><small>DATE OF BIRTH</small><strong>{displayDate(employee.date_of_birth)}</strong></div>
                <div><small>PHONE</small><strong>{show(employee.phone)}</strong></div>
                <div className="employee-detail-wide"><small>HOME ADDRESS</small><strong>{show(employee.address)}</strong></div>
              </div>
            </section>
            <section className="record-section">
              <div className="record-section-heading"><div><span className="eyebrow">EMERGENCY</span><h2>Emergency contact</h2></div></div>
              <div className="profile-details employee-detail-grid">
                <div><small>CONTACT NAME</small><strong>{show(employee.emergency_contact_name)}</strong></div>
                <div><small>RELATIONSHIP</small><strong>{show(employee.emergency_contact_relationship)}</strong></div>
                <div><small>PHONE</small><strong>{show(employee.emergency_contact_phone)}</strong></div>
              </div>
            </section>
            <section className="record-section">
              <div className="record-section-heading"><div><span className="eyebrow">COMPENSATION</span><h2>Salary details</h2></div></div>
              <div className="profile-details employee-detail-grid">
                <div><small>MONTHLY GROSS</small><strong>{currency(employee.monthly_salary)}</strong></div>
                <div><small>BASIC</small><strong>{currency(employee.basic_salary)}</strong></div>
                <div><small>HRA</small><strong>{currency(employee.hra)}</strong></div>
                <div><small>SPECIAL ALLOWANCE</small><strong>{currency(employee.special_allowance)}</strong></div>
              </div>
            </section>
          </>}
    </div>
  );
}

function EmployeePage({ kind, role }) {
  const [data, setData] = useState(null);
  const [profileDocuments, setProfileDocuments] = useState([]);
  const [balances, setBalances] = useState([]);
  const [profile, setProfile] = useState(null);
  const [employeeRows, setEmployeeRows] = useState([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState(null);
  const [documentBusy, setDocumentBusy] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [notice, setNotice] = useState('');
  const today = new Date();
  const [attendanceMonth, setAttendanceMonth] = useState(today.getMonth() + 1);
  const [attendanceYear, setAttendanceYear] = useState(today.getFullYear());
  const [attendanceBusy, setAttendanceBusy] = useState(false);
  const [correction, setCorrection] = useState(null);
  const [correctionForm, setCorrectionForm] = useState(null);
  const [holidayRows, setHolidayRows] = useState([]);
  const [holidayForm, setHolidayForm] = useState({ holiday_date: '', name: '' });
  const [holidayBusy, setHolidayBusy] = useState(false);
  const [leaveTypes, setLeaveTypes] = useState([]);
  const [leaveBalances, setLeaveBalances] = useState([]);
  const [leaveForm, setLeaveForm] = useState({ leave_type_id: '', start_date: '', end_date: '', reason: '' });
  const [leaveModalOpen, setLeaveModalOpen] = useState(false);
  const [leaveBusy, setLeaveBusy] = useState(false);
  const [leaveFilter, setLeaveFilter] = useState('all');
  const [leaveReviewNotes, setLeaveReviewNotes] = useState({});
  const [payrollMonth, setPayrollMonth] = useState(today.getMonth() + 1);
  const [payrollYear, setPayrollYear] = useState(today.getFullYear());
  const lastCompletedPayrollPeriod = new Date(today.getFullYear(), today.getMonth() - 1, 1);
  const [employeePayrollMonth, setEmployeePayrollMonth] = useState(lastCompletedPayrollPeriod.getMonth() + 1);
  const [employeePayrollYear, setEmployeePayrollYear] = useState(lastCompletedPayrollPeriod.getFullYear());
  const [attendanceTab, setAttendanceTab] = useState('summary');
  const [attendanceProfile, setAttendanceProfile] = useState(null);
  const [payrollDepartmentId, setPayrollDepartmentId] = useState('');
  const [departments, setDepartments] = useState([]);
  const [adjustmentTargetId, setAdjustmentTargetId] = useState(null);
  const [adjustmentForm, setAdjustmentForm] = useState({ amount: '', reason: '' });
  const isAdminPayroll = kind === 'payroll' && (role === 'admin' || role === 'hr');
  const isAdminAttendance = kind === 'attendance' && (role === 'admin' || role === 'hr');

  useEffect(() => {
    let active = true;
    const paths = { profile: '/employees/me', attendance: '/attendance/me', leaves: '/leaves/me', payroll: '/payroll/me' };
    async function loadPage() {
      setLoading(true);
      setError('');
      setNotice('');
      try {
        if (kind === 'leaves') {
          if (role === 'admin' || role === 'hr') {
            const params = leaveFilter === 'all' ? {} : { status: leaveFilter };
            const { data: requests } = await api.get('/leaves', { params });
            if (active) setData(requests);
          } else {
            const [requestResult, typeResult, balanceResult] = await Promise.all([
              api.get('/leaves/me'),
              api.get('/leave-types'),
              api.get('/leaves/balances/me'),
            ]);
            if (active) {
              setData(requestResult.data);
              setLeaveTypes(typeResult.data);
              setLeaveBalances(balanceResult.data);
              setLeaveForm((current) => ({ ...current, leave_type_id: current.leave_type_id || String(typeResult.data[0]?.id || '') }));
            }
          }
          return;
        }
        if (kind === 'attendance') {
          const startDate = `${attendanceYear}-${String(attendanceMonth).padStart(2, '0')}-01`;
          const lastDay = new Date(attendanceYear, attendanceMonth, 0).getDate();
          const endDate = `${attendanceYear}-${String(attendanceMonth).padStart(2, '0')}-${String(lastDay).padStart(2, '0')}`;
          if (isAdminAttendance) {
            const [attendanceResult, employeesResult, holidayResult] = await Promise.all([
              api.get('/attendance', { params: { start_date: startDate, end_date: endDate } }),
              api.get('/employees', { params: { include_inactive: true } }),
              api.get('/holidays', { params: { year: attendanceYear } }),
            ]);
            if (active) {
              setData(attendanceResult.data);
              setEmployeeRows(employeesResult.data);
              setHolidayRows(holidayResult.data);
            }
          } else {
            const [attendanceResult, profileResult] = await Promise.all([
              api.get('/attendance/me', { params: { month: attendanceMonth, year: attendanceYear } }),
              api.get('/employees/me'),
            ]);
            if (active) {
              setData(attendanceResult.data);
              setAttendanceProfile(profileResult.data);
            }
          }
          return;
        }
        if (isAdminPayroll) {
          const [payrollResult, employeesResult, departmentResult] = await Promise.all([
            api.get('/payroll', { params: { year: payrollYear, month: payrollMonth, ...(payrollDepartmentId ? { department_id: payrollDepartmentId } : {}) } }),
            api.get('/employees', { params: { include_inactive: true } }),
            api.get('/departments'),
          ]);
          if (active) {
            setData(payrollResult.data);
            setEmployeeRows(employeesResult.data);
            setDepartments(departmentResult.data);
          }
          return;
        }
        const result = await api.get(paths[kind]);
        if (!active) return;
        setData(result.data);
        if (kind === 'profile' && role === 'employee') {
          const documentResult = await api.get(`/employees/${result.data.id}/documents`);
          if (active) setProfileDocuments(documentResult.data);
        }
        if (kind === 'leaves') {
          const balanceResult = await api.get('/leaves/balances/me');
          if (active) setBalances(balanceResult.data);
        }
        if (kind === 'payroll') {
          const profileResult = await api.get('/employees/me');
          if (active) setProfile(profileResult.data);
        }
      } catch (e) {
        if (active) setError(e.response?.data?.detail || 'Unable to load this page. Please try again.');
      } finally {
        if (active) setLoading(false);
      }
    }
    loadPage();
    return () => { active = false; };
  }, [kind, role, leaveFilter, isAdminPayroll, isAdminAttendance, attendanceMonth, attendanceYear, payrollMonth, payrollYear, payrollDepartmentId]);

  async function uploadProfileDocument(event) {
    const input = event.currentTarget;
    const file = input.files?.[0];
    if (!file || !data?.id) return;
    setDocumentBusy(true);
    setError('');
    setNotice('');
    try {
      const body = new FormData();
      body.append('file', file);
      await api.post(`/employees/${data.id}/documents`, body);
      const { data: documents } = await api.get(`/employees/${data.id}/documents`);
      setProfileDocuments(documents);
      setNotice('Your document was uploaded.');
    } catch (e) {
      setError(e.response?.data?.detail || 'Your document could not be uploaded.');
    } finally {
      input.value = '';
      setDocumentBusy(false);
    }
  }

  async function downloadProfileDocument(document) {
    setError('');
    try {
      const response = await api.get(`/employees/${data.id}/documents/${document.id}`, { responseType: 'blob' });
      const url = URL.createObjectURL(response.data);
      const link = window.document.createElement('a');
      link.href = url;
      link.download = document.original_name;
      link.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e) {
      setError(e.response?.data?.detail || 'Your document could not be downloaded.');
    }
  }

  async function refreshAttendance() {
    if (isAdminAttendance) {
      const startDate = `${attendanceYear}-${String(attendanceMonth).padStart(2, '0')}-01`;
      const lastDay = new Date(attendanceYear, attendanceMonth, 0).getDate();
      const endDate = `${attendanceYear}-${String(attendanceMonth).padStart(2, '0')}-${String(lastDay).padStart(2, '0')}`;
      const { data: records } = await api.get('/attendance', { params: { start_date: startDate, end_date: endDate } });
      setData(records);
    } else {
      const { data: summary } = await api.get('/attendance/me', { params: { month: attendanceMonth, year: attendanceYear } });
      setData(summary);
    }
  }

  async function attendanceAction(action) {
    setAttendanceBusy(true);
    setNotice('');
    setError('');
    try {
      await api.post(`/attendance/${action}`);
      await refreshAttendance();
      setNotice(action === 'check-in' ? 'You are checked in. Have a good workday!' : 'You are checked out. Your hours have been recorded.');
    } catch (e) {
      setError(e.response?.data?.detail || 'Attendance could not be updated.');
    } finally {
      setAttendanceBusy(false);
    }
  }

  function beginCorrection(row) {
    const toInput = (value) => {
      if (!value) return '';
      const dateValue = new Date(value);
      dateValue.setMinutes(dateValue.getMinutes() - dateValue.getTimezoneOffset());
      return dateValue.toISOString().slice(0, 16);
    };
    setCorrection(row);
    setCorrectionForm({ check_in: toInput(row.check_in), check_out: toInput(row.check_out), status: row.status, reason: '' });
  }

  async function saveCorrection(event) {
    event.preventDefault();
    if (!correction || !correctionForm) return;
    setAttendanceBusy(true);
    setError('');
    setNotice('');
    try {
      const toUtc = (value) => value ? new Date(value).toISOString() : null;
      await api.patch(`/attendance/${correction.id}/correct`, {
        check_in: toUtc(correctionForm.check_in),
        check_out: toUtc(correctionForm.check_out),
        status: correctionForm.status,
        reason: correctionForm.reason,
      });
      await refreshAttendance();
      setCorrection(null);
      setCorrectionForm(null);
      setNotice('Attendance correction saved.');
    } catch (e) {
      setError(e.response?.data?.detail || 'Attendance correction could not be saved.');
    } finally {
      setAttendanceBusy(false);
    }
  }

  async function saveHoliday(event) {
    event.preventDefault();
    setHolidayBusy(true);
    setError('');
    setNotice('');
    try {
      await api.post('/holidays', holidayForm);
      const { data: holidays } = await api.get('/holidays', { params: { year: attendanceYear } });
      setHolidayRows(holidays);
      setHolidayForm({ holiday_date: '', name: '' });
      setNotice('Holiday added to the payroll calendar.');
    } catch (e) {
      setError(e.response?.data?.detail || 'Holiday could not be added.');
    } finally {
      setHolidayBusy(false);
    }
  }

  async function removeHoliday(holiday) {
    setHolidayBusy(true);
    setError('');
    setNotice('');
    try {
      await api.delete(`/holidays/${holiday.id}`);
      setHolidayRows((current) => current.filter((row) => row.id !== holiday.id));
      setNotice(`${holiday.name} was removed from the payroll calendar.`);
    } catch (e) {
      setError(e.response?.data?.detail || 'Holiday could not be removed.');
    } finally {
      setHolidayBusy(false);
    }
  }

  async function submitLeave(event) {
    event.preventDefault();
    setLeaveBusy(true);
    setError('');
    setNotice('');
    try {
      await api.post('/leaves', { ...leaveForm, leave_type_id: Number(leaveForm.leave_type_id) });
      const { data: requests } = await api.get('/leaves/me');
      setData(requests);
      setLeaveForm((current) => ({ ...current, start_date: '', end_date: '', reason: '' }));
      setLeaveModalOpen(false);
      setNotice('Your leave request was submitted for review.');
    } catch (e) {
      setError(e.response?.data?.detail || 'Leave request could not be submitted.');
    } finally {
      setLeaveBusy(false);
    }
  }

  async function decideLeave(leaveId, status) {
    setLeaveBusy(true);
    setError('');
    setNotice('');
    try {
      await api.post(`/leaves/${leaveId}/decision`, { status, note: leaveReviewNotes[leaveId] || null });
      const params = leaveFilter === 'all' ? {} : { status: leaveFilter };
      const { data: requests } = await api.get('/leaves', { params });
      setData(requests);
      setNotice(`Leave request ${status}.`);
    } catch (e) {
      setError(e.response?.data?.detail || 'Leave request could not be reviewed.');
    } finally {
      setLeaveBusy(false);
    }
  }

  async function generatePayroll() {
    setGenerating(true);
    setNotice('');
    try {
      const result = await api.post('/payroll/generate', { year: payrollYear, month: payrollMonth });
      const [payrollResult, employeesResult] = await Promise.all([
        api.get('/payroll', { params: { year: payrollYear, month: payrollMonth, ...(payrollDepartmentId ? { department_id: payrollDepartmentId } : {}) } }),
        api.get('/employees', { params: { include_inactive: true } }),
      ]);
      setData(payrollResult.data);
      setEmployeeRows(employeesResult.data);
      setNotice(`${result.data.generated_count} records generated for ${monthName(payrollMonth)} ${payrollYear}; ${result.data.skipped_existing} existing records were left unchanged.`);
    } catch (e) {
      setError(e.response?.data?.detail || 'Payroll could not be generated. Please try again.');
    } finally {
      setGenerating(false);
    }
  }

  async function simulateCredit(payrollId) {
    setError('');
    setNotice('');
    try {
      const { data: updated } = await api.post(`/payroll/${payrollId}/simulate-credit`);
      setData((current) => current.map((row) => row.id === updated.id ? updated : row));
      setNotice(`Credit simulation recorded for ${updated.employee_name || 'employee'}; no funds were transferred.`);
    } catch (e) {
      setError(e.response?.data?.detail || 'Salary credit simulation failed.');
    }
  }

  async function submitPayrollAdjustment(event) {
    event.preventDefault();
    if (!adjustmentTargetId) return;
    setError('');
    setNotice('');
    try {
      const { data: updated } = await api.post(`/payroll/${adjustmentTargetId}/adjustments`, adjustmentForm);
      setData((current) => current.map((row) => row.id === updated.id ? updated : row));
      setAdjustmentTargetId(null);
      setAdjustmentForm({ amount: '', reason: '' });
      setNotice(`Manual payroll adjustment saved for ${updated.employee_name}.`);
    } catch (e) {
      setError(e.response?.data?.detail || 'Payroll adjustment could not be saved.');
    }
  }

  async function downloadSlip(payrollId) {
    setDownloading(payrollId);
    setNotice('');
    try {
      const response = await api.get(`/payroll/${payrollId}/salary-slip.pdf`, { responseType: 'blob' });
      const url = URL.createObjectURL(response.data);
      const link = document.createElement('a');
      link.href = url;
      link.download = `salary-slip-${payrollId}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      setNotice(e.response?.data?.detail || 'Could not download the salary slip. Please try again.');
    } finally {
      setDownloading(null);
    }
  }

  const titles = { profile: 'My profile', attendance: 'Attendance', leaves: 'Time off', payroll: 'Pay & benefits' };
  const descriptions = {
    profile: 'Your work details, all in one place.',
    attendance: 'A clear view of your check-ins and hours.',
    leaves: 'Your time-off balance and request history.',
    payroll: 'Your monthly pay statements and salary history.',
  };
  const monthName = (month) => {
    const monthNumber = Number(month);
    if (!Number.isInteger(monthNumber) || monthNumber < 1 || monthNumber > 12) return 'Unknown month';
    return new Intl.DateTimeFormat('en', { month: 'long' }).format(new Date(2000, monthNumber - 1, 1));
  };
  const payrollRows = Array.isArray(data) ? data : [];
  const selectedEmployeePayrollRows = payrollRows.filter((row) => row.year === employeePayrollYear && row.month === employeePayrollMonth);
  const leaveRows = kind === 'leaves' && Array.isArray(data) ? data : [];
  const attendanceRows = data?.records || [];
  const teamAttendanceRows = Array.isArray(data) ? data : [];
  const todayKey = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
  const todayAttendance = attendanceRows.find((row) => row.work_date === todayKey);
  const currentPayrollRows = payrollRows.filter((row) => row.year === payrollYear && row.month === payrollMonth);
  const totalPayrollNet = currentPayrollRows.reduce((total, row) => total + Number(row.net_salary || 0), 0);
  const employeeById = new Map(employeeRows.map((item) => [item.id, item]));
  const selectedPayrollMonthIsComplete = new Date(payrollYear, payrollMonth, 0) < new Date(today.getFullYear(), today.getMonth(), today.getDate());

  return (
    <div className="workspace-page">
      <header className="workspace-page-header">
        <div>
          <span className="eyebrow">{isAdminPayroll || isAdminAttendance ? 'PEOPLE OPERATIONS' : 'YOUR PEOPLE SPACE'}</span>
          <h1>{isAdminPayroll ? 'Payroll overview' : isAdminAttendance ? 'Team attendance' : kind === 'payroll' ? 'Payroll & salary slips' : titles[kind]}</h1>
          <p>{isAdminPayroll ? 'Monthly payroll at a glance, for your whole team.' : isAdminAttendance ? 'Review attendance records and correct time entries.' : kind === 'attendance' ? 'Daily records, monthly summaries, and your work hours.' : kind === 'payroll' ? 'Monthly salary from attendance and approved leave, with Loss-of-Pay deduction.' : descriptions[kind]}</p>
        </div>
        {kind !== 'attendance' && !isAdminPayroll && kind !== 'payroll' && <Link className="page-home-link" to="/">← Back to overview</Link>}
      </header>
      {error && <div className="dashboard-error" role="alert">{error}</div>}
      {notice && <div className="dashboard-error" role="alert">{notice}</div>}
      {loading ? (
        <div className="page-loading"><span className="loading-ring" /> Gathering your details…</div>
      ) : (
        <>
          {kind === 'payroll' && isAdminPayroll && (
            <>
              <div className="attendance-period payroll-period">
                <label>Month<select value={payrollMonth} onChange={(e) => setPayrollMonth(Number(e.target.value))}>{Array.from({ length: 12 }, (_, index) => index + 1).map((month) => <option key={month} value={month}>{monthName(month)}</option>)}</select></label>
                <label>Year<input type="number" min="2000" max="2100" value={payrollYear} onChange={(e) => setPayrollYear(Number(e.target.value))} /></label>
                <label>Department<select value={payrollDepartmentId} onChange={(e) => setPayrollDepartmentId(e.target.value)}><option value="">All departments</option>{departments.map((department) => <option key={department.id} value={department.id}>{department.name}</option>)}</select></label>
              </div>
              <section className="page-highlight payroll-highlight admin-payroll-highlight">
                <div className="highlight-icon">₹</div>
                <div><span className="banner-kicker">{monthName(payrollMonth).toUpperCase()} {payrollYear} PAYROLL</span><strong>{currency(totalPayrollNet)}</strong><small>Net payroll for {currentPayrollRows.length} team members · weekday and holiday-aware</small></div>
                <button className="generate-payroll-button" onClick={generatePayroll} disabled={generating || !selectedPayrollMonthIsComplete}>{generating ? 'Generating…' : selectedPayrollMonthIsComplete ? '＋ Generate this month' : 'Select a completed month'}</button>
                <div className="highlight-decoration">₹</div>
              </section>
              <p className="payroll-policy-note">Payroll counts weekdays excluding company holidays. Scheduled days without attendance are unpaid; approved leave is paid within its annual allowance. PF, professional tax, TDS, and LOP are itemized. Generated records are locked; credit is a simulation only.</p>
              <section className="page-summary-grid payroll-summary-grid">
                <div className="page-summary-card"><span className="today-icon today-blue">▤</span><small>PAYSLIPS THIS MONTH</small><strong>{currentPayrollRows.length}</strong><span>Processed records</span></div>
                <div className="page-summary-card"><span className="today-icon today-green">✓</span><small>LOCKED RECORDS</small><strong>{currentPayrollRows.filter((row) => row.locked).length}</strong><span>Protected from changes</span></div>
                <div className="page-summary-card summary-accent"><span className="today-icon today-amber">♙</span><small>ACTIVE TEAM</small><strong>{employeeRows.length}</strong><span>People in the directory</span></div>
              </section>
              <section className="record-section">
                <div className="record-section-heading"><div><span className="eyebrow">COMPENSATION</span><h2>Payroll records</h2></div><span className="record-count">{payrollRows.length} total records</span></div>
                {payrollRows.length ? (
                  <div className="table-responsive custom-table"><table className="table"><thead><tr><th>Team member</th><th>Period</th><th>Gross</th><th>LOP</th><th>Net pay</th><th>Status</th><th>Action</th></tr></thead><tbody>
                    {payrollRows.map((row) => {
                      const member = employeeById.get(row.employee_id);
                      const employeeName = row.employee_name || member?.full_name || `Employee #${row.employee_id}`;
                      const employeeCode = row.employee_code || member?.employee_code || 'Team member';
                      return <React.Fragment key={row.id}>
                        <tr><td><div className="payroll-person"><span>{employeeName.split(' ').map((part) => part[0]).join('').slice(0, 2) || 'TM'}</span><div><strong>{employeeName}</strong><small>{employeeCode}</small></div></div></td><td>{monthName(row.month)} {row.year}</td><td>{currency(row.gross_salary)}</td><td>{row.lop_days} days · {currency(row.lop_deduction)}<small className="d-block">Other: {currency(row.other_deductions)}</small></td><td><strong>{currency(row.net_salary)}</strong><small className="d-block">Adjustments: {currency(row.manual_adjustment_total)}</small></td><td><span className={`status-pill ${row.simulated_credited ? 'active' : row.locked ? 'inactive' : 'status-pending'}`}>{row.simulated_credited ? 'Credited (simulated)' : row.locked ? 'Locked' : 'Draft'}</span></td><td><button className="inline-action-button" type="button" onClick={() => downloadSlip(row.id)} disabled={downloading === row.id}>{downloading === row.id ? 'Preparing…' : 'Download PDF'}</button>{role === 'admin' && !row.simulated_credited && <><button className="inline-action-button" type="button" onClick={() => { setAdjustmentTargetId(adjustmentTargetId === row.id ? null : row.id); setAdjustmentForm({ amount: '', reason: '' }); }}>Adjust</button><button className="inline-action-button" type="button" onClick={() => simulateCredit(row.id)}>Simulate credit</button></>}</td></tr>
                        {adjustmentTargetId === row.id && <tr><td colSpan="7"><form className="employee-form" onSubmit={submitPayrollAdjustment}><p>Positive amounts add earnings; negative amounts deduct from net salary. Each adjustment is audited.</p><label>Amount (+/-)<input required type="number" step="0.01" value={adjustmentForm.amount} onChange={(event) => setAdjustmentForm({ ...adjustmentForm, amount: event.target.value })} /></label><label>Reason<input required minLength="3" maxLength="500" value={adjustmentForm.reason} onChange={(event) => setAdjustmentForm({ ...adjustmentForm, reason: event.target.value })} /></label><div className="employee-form-actions"><button className="employee-primary-button">Save adjustment</button><button className="employee-secondary-button" type="button" onClick={() => setAdjustmentTargetId(null)}>Cancel</button></div>{row.adjustments?.length > 0 && <p>Adjustment history: {row.adjustments.map((item) => `${item.amount} (${item.reason})`).join(' · ')}</p>}</form></td></tr>}
                      </React.Fragment>;
                    })}
                  </tbody></table></div>
                ) : (
                  <div className="empty-state compact-empty"><span className="empty-art">₹</span><h3>No payroll records yet</h3><p>Generate this month’s payroll to prepare locked salary records for active team members.</p><button className="empty-action" onClick={generatePayroll} disabled={generating}>{generating ? 'Generating…' : 'Generate payroll'} <span>→</span></button></div>
                )}
              </section>
            </>
          )}
          {kind === 'payroll' && !isAdminPayroll && (
            <>
              <div className="attendance-period payroll-period">
                <label>Month<select value={employeePayrollMonth} onChange={(event) => setEmployeePayrollMonth(Number(event.target.value))}>{Array.from({ length: 12 }, (_, index) => index + 1).map((month) => <option key={month} value={month}>{monthName(month)}</option>)}</select></label>
                <label>Year<input type="number" min="2000" max="2100" value={employeePayrollYear} onChange={(event) => setEmployeePayrollYear(Number(event.target.value))} /></label>
              </div>
              <section className="record-section">
                <div className="record-section-heading"><div><span className="eyebrow">PAYROLL &amp; SALARY SLIPS · {monthName(employeePayrollMonth).toUpperCase()} {employeePayrollYear}</span><h2>My payroll records</h2></div><span className="record-count">{selectedEmployeePayrollRows.length} {selectedEmployeePayrollRows.length === 1 ? 'record' : 'records'}</span></div>
                <p className="payroll-policy-note">These records are private to your account. Generated payroll is locked; contact HR if you believe a correction is needed.</p>
                <div className="table-responsive custom-table employee-payroll-table">
                  <table className="table">
                    <thead><tr><th>Code</th><th>Employee</th><th>Department</th><th>P / W / LOP</th><th>Gross</th><th>LOP deduction</th><th>Adjust</th><th>Net salary</th><th>Status</th><th>Slip PDF</th></tr></thead>
                    <tbody>
                      {selectedEmployeePayrollRows.map((row) => (
                        <tr key={row.id}>
                          <td>{row.employee_code || profile?.employee_code || '—'}</td>
                          <td><strong>{row.employee_name || profile?.full_name || 'My payroll'}</strong></td>
                          <td>{profile?.department_name || '—'}</td>
                          <td>{row.payable_days} / {row.working_days} / {row.lop_days}</td>
                          <td>{currency(row.gross_salary)}</td>
                          <td>{currency(row.lop_deduction)}</td>
                          <td>{Number(row.manual_adjustment_total) ? currency(row.manual_adjustment_total) : '—'}</td>
                          <td><strong>{currency(row.net_salary)}</strong></td>
                          <td><span className={`status-pill ${row.simulated_credited ? 'active' : 'inactive'}`}>{row.simulated_credited ? 'Credited (simulated)' : row.locked ? 'Generated · locked' : 'Draft'}</span></td>
                          <td><button className="inline-action-button" type="button" onClick={() => downloadSlip(row.id)} disabled={downloading === row.id}>{downloading === row.id ? 'Preparing…' : 'Slip PDF'}</button></td>
                        </tr>
                      ))}
                      {selectedEmployeePayrollRows.length === 0 && <tr><td colSpan="10" className="employee-payroll-empty">{payrollRows.length ? `No payroll record for ${monthName(employeePayrollMonth)} ${employeePayrollYear}. Select another period.` : 'No payroll has been generated for your account yet. HR/Admin must generate a completed month after your salary details are configured.'}</td></tr>}
                    </tbody>
                  </table>
                </div>
              </section>
            </>
          )}

          {kind === 'attendance' && (
            <>
              {!isAdminAttendance && <div className="attendance-view-tabs" role="tablist" aria-label="Attendance view">
                <button type="button" role="tab" aria-selected={attendanceTab === 'daily'} className={attendanceTab === 'daily' ? 'active' : ''} onClick={() => setAttendanceTab('daily')}>Daily records</button>
                <button type="button" role="tab" aria-selected={attendanceTab === 'summary'} className={attendanceTab === 'summary' ? 'active' : ''} onClick={() => setAttendanceTab('summary')}>Monthly summary</button>
              </div>}
              <div className="attendance-period">
                <label>Month<select value={attendanceMonth} onChange={(e) => setAttendanceMonth(Number(e.target.value))}>{Array.from({ length: 12 }, (_, index) => index + 1).map((month) => <option key={month} value={month}>{monthName(month)}</option>)}</select></label>
                <label>Year<input type="number" min="2000" max="2100" value={attendanceYear} onChange={(e) => setAttendanceYear(Number(e.target.value))} /></label>
              </div>
              {isAdminAttendance ? (
                <>
                  <section className="record-section">
                    <div className="record-section-heading"><div><span className="eyebrow">PAYROLL CALENDAR</span><h2>Company holidays</h2></div><span className="record-count">{holidayRows.length} this year</span></div>
                    {role === 'admin' && <form className="employee-form" onSubmit={saveHoliday}>
                      <label>Holiday date<input required type="date" value={holidayForm.holiday_date} onChange={(e) => setHolidayForm({ ...holidayForm, holiday_date: e.target.value })} /></label>
                      <label>Holiday name<input required minLength={2} maxLength={120} value={holidayForm.name} onChange={(e) => setHolidayForm({ ...holidayForm, name: e.target.value })} /></label>
                      <div className="employee-form-actions"><button className="employee-primary-button" disabled={holidayBusy}>{holidayBusy ? 'Saving…' : 'Add holiday'}</button></div>
                    </form>}
                    {holidayRows.length > 0 && <div className="leave-request-list">{holidayRows.map((holiday) => <article className="leave-request-card" key={holiday.id}>
                      <strong>{holiday.name}</strong><span>{holiday.holiday_date}</span>
                      {role === 'admin' && <button className="inline-action-button" type="button" disabled={holidayBusy} onClick={() => removeHoliday(holiday)}>Remove</button>}
                    </article>)}</div>}
                  </section>
                  <section className="page-summary-grid">
                    <div className="page-summary-card"><span className="today-icon today-blue">◉</span><small>ATTENDANCE RECORDS</small><strong>{teamAttendanceRows.length}</strong><span>For selected month</span></div>
                    <div className="page-summary-card"><span className="today-icon today-green">◷</span><small>HOURS RECORDED</small><strong>{Math.floor(teamAttendanceRows.reduce((total, row) => total + row.working_minutes, 0) / 60)}<i>h</i></strong><span>Team total</span></div>
                    <div className="page-summary-card summary-accent"><span className="today-icon today-amber">♙</span><small>ACTIVE EMPLOYEES</small><strong>{employeeRows.filter((employee) => employee.is_active).length}</strong><span>In employee directory</span></div>
                  </section>
                  <section className="record-section">
                    <div className="record-section-heading"><div><span className="eyebrow">TEAM TIME</span><h2>Monthly attendance</h2></div><span className="record-count">{teamAttendanceRows.length} records</span></div>
                    {teamAttendanceRows.length ? (
                      <div className="table-responsive custom-table"><table className="table"><thead><tr><th>Team member</th><th>Date</th><th>Check in</th><th>Check out</th><th>Hours</th><th>Status</th><th>Correction</th></tr></thead><tbody>
                        {teamAttendanceRows.map((row) => <tr key={row.id}>
                          <td><div className="payroll-person"><span>{row.employee_name?.split(' ').map((part) => part[0]).join('').slice(0, 2) || 'TM'}</span><div><strong>{row.employee_name || `Employee #${row.employee_id}`}</strong><small>{row.employee_code || ''}</small></div></div></td>
                          <td>{row.work_date}</td>
                          <td>{row.check_in ? new Date(row.check_in).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '—'}</td>
                          <td>{row.check_out ? new Date(row.check_out).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '—'}</td>
                          <td>{Math.floor(row.working_minutes / 60)}h {row.working_minutes % 60}m</td>
                          <td><span className={`status-pill status-${row.status}`}>{row.status.replace('_', ' ')}</span></td>
                          <td>{role === 'admin' && <button className="inline-action-button" type="button" onClick={() => beginCorrection(row)}>Correct</button>}</td>
                        </tr>)}
                      </tbody></table></div>
                    ) : <div className="empty-state compact-empty"><span className="empty-art">◷</span><h3>No team records for this month</h3><p>Employee check-ins will appear here for the selected period.</p></div>}
                  </section>
                  {correction && correctionForm && <div className="correction-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setCorrection(null); }}>
                    <section className="correction-dialog" role="dialog" aria-modal="true" aria-labelledby="correction-title">
                      <div className="record-section-heading"><div><span className="eyebrow">ADMIN OVERRIDE</span><h2 id="correction-title">Correct attendance</h2></div><button type="button" className="dialog-close" onClick={() => setCorrection(null)} aria-label="Close">×</button></div>
                      <p>{correction.employee_name} · {correction.work_date}</p>
                      <form className="employee-form" onSubmit={saveCorrection}>
                        <label>Check in<input type="datetime-local" value={correctionForm.check_in} onChange={(e) => setCorrectionForm({ ...correctionForm, check_in: e.target.value })} /></label>
                        <label>Check out<input type="datetime-local" value={correctionForm.check_out} onChange={(e) => setCorrectionForm({ ...correctionForm, check_out: e.target.value })} /></label>
                        <label>Status<select value={correctionForm.status} onChange={(e) => setCorrectionForm({ ...correctionForm, status: e.target.value })}><option value="present">Present</option><option value="absent">Absent</option><option value="half_day">Half day</option><option value="on_leave">On leave</option></select></label>
                        <label className="leave-reason-field">Correction reason<textarea required minLength={3} maxLength={500} rows="3" value={correctionForm.reason} onChange={(e) => setCorrectionForm({ ...correctionForm, reason: e.target.value })} /></label>
                        <div className="employee-form-actions"><button className="employee-primary-button" disabled={attendanceBusy}>{attendanceBusy ? 'Saving…' : 'Save correction'}</button><button className="employee-secondary-button" type="button" onClick={() => setCorrection(null)}>Cancel</button></div>
                      </form>
                    </section>
                  </div>}
                </>
              ) : (
                <>
                  {attendanceTab === 'summary' ? (
                    <section className="record-section attendance-monthly-summary">
                      <div className="record-section-heading"><div><span className="eyebrow">MONTHLY SUMMARY · {monthName(attendanceMonth).toUpperCase()} {attendanceYear}</span><h2>My attendance</h2></div><span className="record-count">Personal report</span></div>
                      {attendanceProfile ? <div className="table-responsive custom-table attendance-summary-table">
                        <table className="table">
                          <thead><tr><th>Code</th><th>Employee</th><th>Department</th><th>Working days</th><th>Present</th><th>Half days</th><th>Leave</th><th>Absent</th><th>Open check-ins</th><th>Hours</th></tr></thead>
                          <tbody><tr>
                            <td>{attendanceProfile.employee_code}</td>
                            <td><strong>{attendanceProfile.full_name}</strong></td>
                            <td>{attendanceProfile.department_name || '—'}</td>
                            <td>{data?.working_days ?? 0}</td>
                            <td>{attendanceRows.filter((row) => row.status === 'present').length}</td>
                            <td>{data?.days_half_day ?? 0}</td>
                            <td>{data?.days_on_leave ?? 0}</td>
                            <td>{data?.days_absent ?? 0}</td>
                            <td>{attendanceRows.filter((row) => row.check_in && !row.check_out).length}</td>
                            <td>{((data?.total_working_minutes || 0) / 60).toFixed(1)}</td>
                          </tr></tbody>
                        </table>
                      </div> : <p className="inline-empty">Your employee profile could not be loaded.</p>}
                    </section>
                  ) : (
                    <>
                      <section className="attendance-checkin-card">
                        <div><span className="eyebrow">TODAY · {today.toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' })}</span><h2>{todayAttendance?.check_out ? 'Your day is complete' : todayAttendance?.check_in ? 'You are checked in' : 'Ready to start your day?'}</h2><p>{todayAttendance?.check_in ? `Checked in at ${new Date(todayAttendance.check_in).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}${todayAttendance.check_out ? ` · Checked out at ${new Date(todayAttendance.check_out).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}` : ''}` : 'Check in to start recording your work hours.'}</p></div>
                        {!todayAttendance?.check_in ? <button className="employee-primary-button" type="button" disabled={attendanceBusy} onClick={() => attendanceAction('check-in')}>{attendanceBusy ? 'Updating…' : 'Check in'}</button> : !todayAttendance.check_out ? <button className="employee-primary-button" type="button" disabled={attendanceBusy} onClick={() => attendanceAction('check-out')}>{attendanceBusy ? 'Updating…' : 'Check out'}</button> : <span className="status-pill active">Complete</span>}
                      </section>
                      <section className="record-section">
                        <div className="record-section-heading"><div><span className="eyebrow">YOUR WORKDAYS</span><h2>Daily attendance</h2></div><span className="record-count">{attendanceRows.length} records</span></div>
                        {attendanceRows.length ? (
                          <div className="table-responsive custom-table"><table className="table"><thead><tr><th>Date</th><th>Check in</th><th>Check out</th><th>Hours</th><th>Status</th></tr></thead><tbody>
                            {attendanceRows.map((row) => <tr key={row.id}><td><strong>{new Intl.DateTimeFormat('en', { weekday: 'short', month: 'short', day: 'numeric' }).format(new Date(`${row.work_date}T00:00:00`))}</strong></td><td>{row.check_in ? new Date(row.check_in).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '—'}</td><td>{row.check_out ? new Date(row.check_out).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '—'}</td><td>{Math.floor((row.working_minutes || 0) / 60)}h {(row.working_minutes || 0) % 60}m</td><td><span className={`status-pill status-${row.status}`}>{row.status.replace('_', ' ')}</span></td></tr>)}
                          </tbody></table></div>
                        ) : <div className="empty-state compact-empty"><span className="empty-art">◷</span><h3>No attendance records yet</h3><p>Your check-in history for this month will appear here.</p></div>}
                      </section>
                    </>
                  )}
                </>
              )}
            </>
          )}

          {kind === 'leaves' && (
            <>
              {role === 'employee' ? (
                <>
                  <section className="record-section balance-section">
                    <div className="record-section-heading"><div><span className="eyebrow">YOUR PAID TIME OFF</span><h2>Leave balance</h2></div><div className="employee-directory-header-actions"><span className="record-count">{new Date().getFullYear()}</span><button className="employee-primary-button" type="button" onClick={() => setLeaveModalOpen(true)}>Apply for leave</button></div></div>
                    {leaveBalances.length ? <div className="balance-grid">{leaveBalances.map((balance) => <div className="balance-card" key={balance.leave_type_id}><span className="balance-icon">✳</span><small>{balance.leave_type}</small><strong>{Number(balance.remaining_days)}</strong><span>of {balance.annual_allowance} days available</span></div>)}</div> : <p className="inline-empty">No leave types have been configured yet.</p>}
                  </section>
                  {leaveModalOpen && <div className="employee-dialog-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget && !leaveBusy) setLeaveModalOpen(false); }}>
                    <section className="employee-dialog" role="dialog" aria-modal="true" aria-labelledby="employee-leave-dialog-title">
                      <div className="employee-dialog-heading"><h2 id="employee-leave-dialog-title">Apply for leave</h2><button type="button" onClick={() => setLeaveModalOpen(false)} disabled={leaveBusy} aria-label="Close">×</button></div>
                      {error && <div className="dashboard-error employee-dialog-error" role="alert">{error}</div>}
                      <form className="employee-dashboard-leave-form" onSubmit={submitLeave}>
                        <label>Leave type<select required value={leaveForm.leave_type_id} onChange={(e) => setLeaveForm({ ...leaveForm, leave_type_id: e.target.value })}><option value="">Choose a leave type</option>{leaveTypes.map((type) => <option key={type.id} value={type.id}>{type.name} · {type.annual_allowance} paid days/year</option>)}</select></label>
                        <div className="employee-leave-date-fields">
                          <label>Start date<input required type="date" min={dateKey(today)} value={leaveForm.start_date} onChange={(e) => setLeaveForm({ ...leaveForm, start_date: e.target.value })} /></label>
                          <label>End date<input required type="date" min={leaveForm.start_date || dateKey(today)} value={leaveForm.end_date} onChange={(e) => setLeaveForm({ ...leaveForm, end_date: e.target.value })} /></label>
                        </div>
                        <label>Reason<textarea required minLength={3} maxLength={2000} rows="3" value={leaveForm.reason} onChange={(e) => setLeaveForm({ ...leaveForm, reason: e.target.value })} /></label>
                        <p>Requests are reviewed by HR/Admin. Weekends and company holidays are not counted.</p>
                        <div className="employee-dialog-actions"><button className="employee-secondary-button" type="button" disabled={leaveBusy} onClick={() => setLeaveModalOpen(false)}>Cancel</button><button className="employee-primary-button" disabled={leaveBusy || leaveTypes.length === 0}>{leaveBusy ? 'Submitting…' : 'Submit request'}</button></div>
                      </form>
                    </section>
                  </div>}
                </>
              ) : (
                <section className="record-section">
                  <div className="record-section-heading"><div><span className="eyebrow">PEOPLE OPERATIONS</span><h2>Leave requests</h2></div><label className="leave-filter">Show<select value={leaveFilter} onChange={(e) => setLeaveFilter(e.target.value)}><option value="all">All requests</option><option value="pending">Pending</option><option value="approved">Approved</option><option value="rejected">Rejected</option></select></label></div>
                  {leaveRows.length ? <div className="leave-request-list">{leaveRows.map((row) => <article className="leave-request-card" key={row.id}>
                    <div className="leave-request-person"><span className="profile-avatar">{row.employee_name?.split(' ').map((part) => part[0]).join('').slice(0, 2) || 'TM'}</span><div><strong>{row.employee_name || `Employee #${row.employee_id}`}</strong><small>{row.employee_code || 'Team member'} · {row.leave_type || 'Leave'}</small></div></div>
                    <div className="leave-request-dates"><strong>{row.start_date} — {row.end_date}</strong><small>{row.days} calendar days · {row.annual_allowance ?? 0} paid days/year</small></div>
                    <p className="leave-request-reason">{row.reason}</p>
                    <span className={`status-pill status-${row.status}`}>{row.status}</span>
                    {row.status === 'pending' && <div className="leave-decision-actions"><button type="button" disabled={leaveBusy} onClick={() => decideLeave(row.id, 'approved')}>Approve</button><button type="button" disabled={leaveBusy} onClick={() => decideLeave(row.id, 'rejected')}>Reject</button></div>}
                    {row.status === 'pending' && <label className="leave-reason-field">Review note<textarea maxLength={1000} rows="2" value={leaveReviewNotes[row.id] || ''} onChange={(e) => setLeaveReviewNotes({ ...leaveReviewNotes, [row.id]: e.target.value })} /></label>}
                    {row.reviewed_at && <small className="leave-review-date">Reviewed {new Date(row.reviewed_at).toLocaleDateString()}{row.review_note ? ` · ${row.review_note}` : ''}</small>}
                  </article>)}</div> : <div className="empty-state compact-empty"><span className="empty-art">✳</span><h3>No {leaveFilter === 'all' ? '' : `${leaveFilter} `}leave requests</h3><p>New employee requests will appear here for review.</p></div>}
                </section>
              )}
              <section className="record-section">
                <div className="record-section-heading"><div><span className="eyebrow">{role === 'employee' ? 'YOUR REQUESTS' : 'REQUEST ARCHIVE'}</span><h2>{role === 'employee' ? 'Time-off history' : 'Request history'}</h2></div><span className="record-count">{leaveRows.length} requests</span></div>
                {role === 'employee' && (leaveRows.length ? <div className="leave-list">{leaveRows.map((row) => <article className="leave-card" key={row.id}><span className="leave-date-box"><strong>{new Date(`${row.start_date}T00:00:00`).getDate()}</strong><small>{monthName(new Date(`${row.start_date}T00:00:00`).getMonth() + 1).slice(0, 3)}</small></span><div className="leave-info"><strong>{row.leave_type || row.reason || 'Time off request'}</strong><span>{row.start_date} — {row.end_date} · {row.days} days</span><small>{row.reason}</small></div><span className={`status-pill status-${row.status}`}>{row.status}</span></article>)}</div> : <div className="empty-state compact-empty"><span className="empty-art">✳</span><h3>No time-off requests yet</h3><p>Your leave requests and their status will be easy to find here.</p></div>)}
              </section>
            </>
          )}

          {kind === 'profile' && (
            <>
              <section className="profile-hero">
                <div className="profile-avatar">{profile?.full_name?.split(' ').map((part) => part[0]).join('').slice(0, 2) || 'ME'}</div>
                <div className="profile-identity"><span className="banner-kicker">TEAM MEMBER</span><h2>{data?.full_name || 'Your profile'}</h2><p>{data?.designation || 'Employee'}{data?.department_id ? ` · Department ${data.department_id}` : ''}</p></div>
                <span className={`status-pill ${data?.is_active ? 'active' : 'inactive'}`}>{data?.is_active ? 'Active' : 'Inactive'}</span>
              </section>
              <section className="record-section">
                <div className="record-section-heading"><div><span className="eyebrow">YOUR DETAILS</span><h2>Work profile</h2></div></div>
                <div className="profile-details">
                  <div><small>WORK EMAIL</small><strong>{data?.email || '—'}</strong></div>
                  <div><small>EMPLOYEE ID</small><strong>{data?.employee_code || '—'}</strong></div>
                  <div><small>DESIGNATION</small><strong>{data?.designation || '—'}</strong></div>
                  <div><small>DEPARTMENT</small><strong>{data?.department_name || (data?.department_id ? `Department ${data.department_id}` : 'Not assigned')}</strong></div>
                  <div><small>JOINED</small><strong>{data?.joining_date ? new Intl.DateTimeFormat('en', { month: 'long', day: 'numeric', year: 'numeric' }).format(new Date(`${data.joining_date}T00:00:00`)) : '—'}</strong></div>
                  <div><small>PHONE</small><strong>{data?.phone || 'Not added'}</strong></div>
                  <div><small>DATE OF BIRTH</small><strong>{data?.date_of_birth ? new Intl.DateTimeFormat('en', { month: 'long', day: 'numeric', year: 'numeric' }).format(new Date(`${data.date_of_birth}T00:00:00`)) : 'Not added'}</strong></div>
                  <div><small>HOME ADDRESS</small><strong>{data?.address || 'Not added'}</strong></div>
                  <div><small>EMERGENCY CONTACT</small><strong>{data?.emergency_contact_name || 'Not added'}</strong></div>
                  <div><small>RELATIONSHIP</small><strong>{data?.emergency_contact_relationship || 'Not added'}</strong></div>
                  <div><small>EMERGENCY PHONE</small><strong>{data?.emergency_contact_phone || 'Not added'}</strong></div>
                </div>
              </section>
              {role === 'employee' && (
                <section className="record-section">
                  <div className="record-section-heading">
                    <div><span className="eyebrow">YOUR FILES</span><h2>My documents</h2></div>
                    <label className={`employee-primary-button profile-document-upload${documentBusy ? ' is-busy' : ''}`}>
                      {documentBusy ? 'Uploading…' : '＋ Upload document'}
                      <input
                        type="file"
                        accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png"
                        disabled={documentBusy}
                        onChange={uploadProfileDocument}
                        aria-label="Upload a personal document"
                      />
                    </label>
                  </div>
                  <p className="payroll-policy-note">Upload a PDF, JPEG, or PNG file up to 5 MB. Only you and authorized HR/Admin staff can access your documents.</p>
                  {profileDocuments.length ? (
                    <div className="profile-document-list">
                      {profileDocuments.map((document) => (
                        <div className="profile-document-item" key={document.id}>
                          <span className="today-icon today-blue">▤</span>
                          <span><strong>{document.original_name}</strong><small>Uploaded {new Date(document.uploaded_at).toLocaleDateString()}</small></span>
                          <button className="employee-secondary-button" type="button" onClick={() => downloadProfileDocument(document)}>Download</button>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="empty-state compact-empty"><h3>No documents uploaded</h3><p>Add an identity, education, or other requested employment document.</p></div>
                  )}
                </section>
              )}
            </>
          )}
        </>
      )}
    </div>
  );
}

function DepartmentsPage() {
  const [departments, setDepartments] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [search, setSearch] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    Promise.all([
      api.get('/departments'),
      api.get('/employees'),
    ])
      .then(([departmentResult, employeeResult]) => {
        if (!active) return;
        setDepartments(departmentResult.data);
        setEmployees(employeeResult.data);
      })
      .catch((e) => {
        if (active) setError(e.response?.data?.detail || 'Departments could not be loaded.');
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, []);

  const departmentRows = departments
    .map((department) => ({
      ...department,
      employeeCount: employees.filter((employee) => employee.department_id === department.id).length,
      employees: employees.filter((employee) => employee.department_id === department.id),
    }))
    .filter((department) => {
      const query = search.trim().toLowerCase();
      return !query || department.name.toLowerCase().includes(query)
        || department.employees.some((employee) => employee.full_name.toLowerCase().includes(query));
    });
  const pageSize = 10;
  const pageCount = Math.max(1, Math.ceil(departmentRows.length / pageSize));
  const visibleDepartments = departmentRows.slice((currentPage - 1) * pageSize, currentPage * pageSize);
  const assignedCount = employees.filter((employee) => employee.department_id).length;

  return (
    <div className="workspace-page">
      <header className="workspace-page-header"><div><span className="eyebrow">PEOPLE OPERATIONS</span><h1>Departments</h1><p>Explore teams and current employee distribution.</p></div><Link className="page-home-link" to="/">← Back to dashboard</Link></header>
      {error && <div className="dashboard-error" role="alert">{error}</div>}
      <section className="page-summary-grid">
        <article className="page-summary-card"><span className="today-icon today-blue">▤</span><small>DEPARTMENTS</small><strong>{loading ? '—' : departments.length}</strong><span>Organization teams</span></article>
        <article className="page-summary-card"><span className="today-icon today-green">♙</span><small>ASSIGNED EMPLOYEES</small><strong>{loading ? '—' : assignedCount}</strong><span>Across all departments</span></article>
        <article className="page-summary-card summary-accent"><span className="today-icon today-amber">◎</span><small>UNASSIGNED</small><strong>{loading ? '—' : employees.length - assignedCount}</strong><span>Need a department assignment</span></article>
      </section>
      <section className="record-section">
        <div className="record-section-heading"><div><span className="eyebrow">TEAM DIRECTORY</span><h2>Department headcount</h2></div><span className="record-count">{departmentRows.length} departments</span></div>
        <div className="directory-filters">
          <label className="directory-search">Search teams or employees<input type="search" placeholder="Search by department or employee" value={search} onChange={(event) => { setSearch(event.target.value); setCurrentPage(1); }} /></label>
        </div>
        {loading ? <div className="page-loading"><span className="loading-ring" /> Loading departments…</div> : visibleDepartments.length ? (
          <div className="table-responsive custom-table"><table className="table"><thead><tr><th>Department</th><th>Active headcount</th><th>Team members</th></tr></thead><tbody>
            {visibleDepartments.map((department) => <tr key={department.id}><td><strong>{department.name}</strong></td><td>{department.employeeCount}</td><td>{department.employees.map((employee) => employee.full_name).join(', ') || 'No active employees'}</td></tr>)}
          </tbody></table></div>
        ) : <div className="empty-state compact-empty"><h3>{departments.length ? 'No teams match your search' : 'No departments available'}</h3><p>{departments.length ? 'Try a different department or employee name.' : 'Create departments using the configured database seed/setup process.'}</p></div>}
        {pageCount > 1 && <nav className="directory-pagination" aria-label="Department list pages"><button type="button" disabled={currentPage === 1} onClick={() => setCurrentPage((page) => page - 1)}>Previous</button><span>Page {currentPage} of {pageCount}</span><button type="button" disabled={currentPage === pageCount} onClick={() => setCurrentPage((page) => page + 1)}>Next</button></nav>}
      </section>
    </div>
  );
}

function SettingsPage({ role, timeFormat, onTimeFormatChange, compactLayout, onCompactLayoutChange }) {
  return (
    <div className="workspace-page">
      <header className="workspace-page-header"><div><span className="eyebrow">PREFERENCES</span><h1>Settings</h1><p>Personalize how the HRMS workspace is displayed in this browser.</p></div><Link className="page-home-link" to="/">← Back to dashboard</Link></header>
      <section className="record-section settings-section">
        <div className="record-section-heading"><div><span className="eyebrow">DISPLAY</span><h2>Workspace preferences</h2></div></div>
        <label className="settings-preference-row"><span><strong>Time format</strong><small>Choose how attendance times are displayed on your dashboard.</small></span><select aria-label="Time format" value={timeFormat} onChange={(event) => onTimeFormatChange(event.target.value)}><option value="12h">12-hour clock</option><option value="24h">24-hour clock</option></select></label>
        <label className="settings-preference-row"><span><strong>Compact layout</strong><small>Reduce spacing to fit more information on screen.</small></span><input type="checkbox" checked={compactLayout} onChange={(event) => onCompactLayoutChange(event.target.checked)} /></label>
      </section>
      <section className="record-section settings-section">
        <div className="record-section-heading"><div><span className="eyebrow">ACCOUNT</span><h2>Signed-in role</h2></div></div>
        <p className="settings-role-description">You are signed in as <strong>{role}</strong>. Access to HRMS records and actions is still enforced by the backend role permissions.</p>
      </section>
    </div>
  );
}

export default function App() {
  const [role, setRole] = useState(null);
  const [authStatus, setAuthStatus] = useState('checking');
  const [authError, setAuthError] = useState('');
  const [sessionExpired, setSessionExpired] = useState(false);
  const [timeFormat, setTimeFormat] = useState(() => localStorage.getItem('hrms_time_format') === '12h' ? '12h' : '24h');
  const [compactLayout, setCompactLayout] = useState(() => localStorage.getItem('hrms_compact_layout') === 'true');
  const navigate = useNavigate();
  const isAdmin = role === 'admin';
  const isHRStaff = isAdmin || role === 'hr';

  function updateTimeFormat(value) {
    setTimeFormat(value);
    localStorage.setItem('hrms_time_format', value);
  }

  function updateCompactLayout(value) {
    setCompactLayout(value);
    localStorage.setItem('hrms_compact_layout', String(value));
  }

  useEffect(() => {
    let active = true;
    function handleUnauthorized() {
      setRole(null);
      setAuthStatus('anonymous');
      setSessionExpired(true);
      navigate('/');
    }

    window.addEventListener('hrms:unauthorized', handleUnauthorized);
    restoreSession()
      .then((data) => {
        if (!active) return;
        if (data) {
          setRole(data.role);
          setAuthStatus('authenticated');
        } else {
          setAuthStatus('anonymous');
        }
      })
      .catch(() => {
        if (!active) return;
        setAuthError('Unable to validate your session. Check your connection and try again.');
        setAuthStatus('anonymous');
      });
    return () => {
      active = false;
      window.removeEventListener('hrms:unauthorized', handleUnauthorized);
    };
  }, [navigate]);

  async function logout() {
    try {
      await api.post('/auth/logout');
      setAuthError('');
    } catch {
      setAuthError('We could not contact the server to end your session. Please try again.');
    } finally {
      setAccessToken(null);
      setRole(null);
      setAuthStatus('anonymous');
      setSessionExpired(false);
      navigate('/');
    }
  }

  if (authStatus === 'checking') {
    return <div className="auth-loading" role="status">Checking your session…</div>;
  }

  if (authStatus !== 'authenticated') {
    return <Login onLogin={(data) => {
      setRole(data.role);
      setAuthStatus('authenticated');
      setSessionExpired(false);
      setAuthError('');
      navigate('/');
    }} sessionExpired={sessionExpired} authError={authError} />;
  }

  return (
    <div className={`app-shell workspace-shell${compactLayout ? ' compact-workspace' : ''}`}>
      <aside className="sidebar">
        <div className="brand-block">
          <div className="brand-mark">H</div>
          <div>
            <h4>HRMS</h4>
            <small>People operations</small>
          </div>
        </div>

        <nav className="compact-sidebar-nav">
          <div className="sidebar-group">
            <div className="sidebar-caption">OVERVIEW</div>
            <NavLink end className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`} to="/"><span>▦</span> Dashboard</NavLink>
          </div>
          <div className="sidebar-group">
            <div className="sidebar-caption">HRMS FEATURES</div>
            {role === 'admin' && <NavLink className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`} to="/access"><span>♧</span> Users &amp; roles</NavLink>}
            <NavLink className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`} to="/employees"><span>♙</span> Employee Management</NavLink>
            <NavLink className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`} to="/attendance"><span>◷</span> Attendance Management</NavLink>
            <NavLink className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`} to="/leaves"><span>▣</span> Leave Management</NavLink>
            <NavLink className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`} to="/payroll"><span>₹</span> Payroll Management</NavLink>
            <NavLink className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`} to={isHRStaff ? '/reports' : '/payroll'}><span>▤</span> PDF Salary Slips &amp; Reports</NavLink>
            <NavLink className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`} to="/notifications"><span>✉</span> Notifications &amp; Audit Logs</NavLink>
            <NavLink className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`} to="/reports"><span>▥</span> Reports &amp; Analytics</NavLink>
          </div>
          {isHRStaff && <div className="sidebar-group">
            <div className="sidebar-caption">WORKSPACE</div>
            <NavLink className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`} to="/departments"><span>▤</span> Departments</NavLink>
          </div>}
          <div className="sidebar-group">
            <div className="sidebar-caption">ACCOUNT</div>
            <NavLink className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`} to="/profile"><span>♙</span> My Profile</NavLink>
          </div>
        </nav>

        <div className="sidebar-bottom">
          <div className="sidebar-profile">
            <span className="header-avatar">{role === 'admin' || role === 'hr' ? 'HR' : 'ME'}</span>
            <span><strong>{role === 'admin' ? 'Administrator' : role === 'hr' ? 'People team' : 'Team member'}</strong><small>{role || 'employee'} account</small></span>
          </div>
          <button className="logout-button" onClick={logout}><span>↪</span> Logout</button>
        </div>
      </aside>

      <main className="main-content">
        <Routes>
          <Route path="/" element={<Dashboard role={role} clockFormat={timeFormat} />} />
          <Route path="/employees" element={isHRStaff ? <Employees /> : <EmployeeDirectory />} />
          <Route path="/employees/:employeeId" element={isHRStaff ? <EmployeeDetails /> : <Navigate to="/" replace />} />
          <Route path="/departments" element={isHRStaff ? <DepartmentsPage /> : <Navigate to="/" replace />} />
          <Route path="/reports" element={<ReportsPanel role={role} />} />
          <Route path="/notifications" element={<NotificationLogs role={role} />} />
          <Route path="/settings" element={<SettingsPage role={role} timeFormat={timeFormat} onTimeFormatChange={updateTimeFormat} compactLayout={compactLayout} onCompactLayoutChange={updateCompactLayout} />} />
          <Route path="/access" element={isAdmin ? <AdminAccessPanel /> : <Navigate to="/" replace />} />
          <Route path="/audit" element={isAdmin ? <AuditLogs /> : <Navigate to="/" replace />} />
          <Route path="/profile" element={<EmployeePage kind="profile" role={role} />} />
          <Route path="/attendance" element={<EmployeePage kind="attendance" role={role} />} />
          <Route path="/leaves" element={<EmployeePage kind="leaves" role={role} />} />
          <Route path="/payroll" element={<EmployeePage kind="payroll" role={role} />} />
          <Route path="/register" element={<Navigate to="/" replace />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}
