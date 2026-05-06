# osvcbox

Simple Django app for monthly time tracking and invoicing for self-employed users.

See the Czech version in [README.cs.md](README.cs.md).

## Setup

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Then open `http://127.0.0.1:8000/` and sign in with the user you created.

## Smoke Test Flow

1. Sign in. The app creates a workspace automatically on first access.
2. Open `Workspace` and set `default_daily_hours`, for example `8.00`, plus an optional default hourly rate.
3. Open `Clients` and create a client. You can also set a client-specific default rate.
4. Open `Projects` and create a project under that client. You can also set a project-specific rate.
5. Open `Log hours` and add an entry for the current month. The form pre-fills today's date, 08:00-16:30, and a 30 minute lunch deduction. You can also pick the date from the colored calendar, which highlights weekends and Czech public holidays.
6. Go back to `Dashboard`.
7. In `Dashboard`, choose the month or year you want to view. The current month is the default.
8. Open `Report`, choose a month, and optionally filter by client or project.
9. On `Report`, use `Export XLSX` to export the currently filtered entries to Excel. The file contains date, start, end, total hours, and note only.
10. If you make a mistake, click `Edit` next to the entry in `Report`.
11. Use the `◐` button in the top bar to switch the theme. The choice stays saved in the browser.
12. Open `Payments` and add recurring payments. The app generates a QR code for each payment and subtracts them from the invoiced amount as a net total after those expenses.

The dashboard shows the selected month or year, the work fund from Monday to Friday without Czech public holidays, worked hours calculated from start and end times with an optional 30 minute lunch deduction, billable and non-billable hours, balance, total invoice amount, and a breakdown by clients and projects.
It also lists holidays that reduce the fund, including their dates.

Hourly rate can vary by project or client. The invoice rate is resolved in this order: `Project.hourly_rate_czk`, `Client.default_hourly_rate_czk`, `Workspace.default_hourly_rate_czk`, otherwise `0`.
