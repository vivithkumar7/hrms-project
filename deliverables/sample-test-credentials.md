# Local HRMS test accounts

Do not use shared or committed passwords for test accounts. The seed command
requires the administrator email and a unique password to be provided in the
local environment; this file intentionally contains no working credentials.

## Admin

In PowerShell, set the local admin identity before seeding:

```powershell
$env:HRMS_ADMIN_EMAIL = "admin@example.com"
$env:HRMS_ADMIN_PASSWORD = "<replace-with-a-unique-password-of-at-least-12-characters>"
cd backend
.\.venv\Scripts\python.exe -m app.seed
```

Replace the placeholder before running the command. Use a password that is not
used for any other account, and do not commit it to source control or paste it
into screenshots or API exports. The same email and password are used to sign
in to the local app as Admin.

## HR and Employee

Create HR and Employee accounts in the local app using unused test email
addresses, for example:

| Role | Example local email | Provisioning |
|---|---|---|
| HR | `hr@example.com` | Register a local account, then have the Admin assign the HR role in **Roles & access**. |
| Employee | `employee@example.com` | Register as an Employee, or have HR/Admin onboard the employee and provide a unique temporary password. |

Choose unique passwords locally for these accounts too. Public registration
creates Employee access only; it cannot create Admin or HR accounts. These
example email addresses are identifiers, not pre-seeded accounts.

## Quick verification

1. Start the backend and frontend using the project [README](../README.md).
2. Seed the local Admin account using the environment variables above.
3. Sign in as Admin and create or promote the HR test account.
4. Create/register an Employee test account and verify its role-specific pages.
5. Use fictional test records only. The checked-in salary-slip PDF is a sample,
   not a real payroll statement.