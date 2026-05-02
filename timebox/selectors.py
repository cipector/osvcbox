import calendar
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from .holidays import czech_public_holidays_map, is_czech_business_day
from .models import RegularPayment, WorkEntry


@dataclass(frozen=True)
class DashboardProjectRow:
    project_name: str
    billable_hours: Decimal
    amount_czk: Decimal


@dataclass(frozen=True)
class DashboardClientRow:
    client_name: str
    billable_hours: Decimal
    amount_czk: Decimal
    projects: list[DashboardProjectRow]


@dataclass(frozen=True)
class MonthlyDashboard:
    year: int
    month: int | None
    month_label: str
    period: str
    working_days: int
    fund_holiday_count: int
    holiday_count: int
    holidays: list[tuple[date, str]]
    work_fund_hours: Decimal
    worked_hours: Decimal
    billable_hours: Decimal
    non_billable_hours: Decimal
    balance_hours: Decimal
    invoice_amount_czk: Decimal
    regular_expenses_czk: Decimal
    net_invoice_amount_czk: Decimal
    clients: list[DashboardClientRow]


def get_monthly_dashboard(*, workspace, user, year, month):
    return get_dashboard(workspace=workspace, user=user, year=year, month=month, period="month")


def get_dashboard(*, workspace, user, year, period, month=None):
    if period == "year":
        working_days = sum(_working_days_in_month(year, month_number) for month_number in range(1, 13))
        holidays = _holidays_in_year(year)
        entries = WorkEntry.objects.filter(
            workspace=workspace,
            user=user,
            date__year=year,
        ).select_related("workspace", "project", "project__client")
        month_label = str(year)
        month = None
        expense_multiplier = Decimal("12")
    else:
        working_days = _working_days_in_month(year, month)
        holidays = _holidays_in_month(year, month)
        entries = WorkEntry.objects.filter(
            workspace=workspace,
            user=user,
            date__year=year,
            date__month=month,
        ).select_related("workspace", "project", "project__client")
        month_label = f"{month:02d}/{year}"
        expense_multiplier = Decimal("1")

    return _build_dashboard(
        workspace=workspace,
        user=user,
        year=year,
        month=month,
        month_label=month_label,
        period=period,
        working_days=working_days,
        holidays=holidays,
        entries=entries,
        expense_multiplier=expense_multiplier,
    )


def _working_days_in_month(year, month):
    _, days_in_month = calendar.monthrange(year, month)
    return sum(
        1
        for day in range(1, days_in_month + 1)
        if is_czech_business_day(date(year, month, day))
    )


def _holidays_in_month(year, month):
    return [
        (holiday, name)
        for holiday, name in sorted(czech_public_holidays_map(year).items())
        if holiday.month == month
    ]


def _holidays_in_year(year):
    return list(sorted(czech_public_holidays_map(year).items()))


def _build_dashboard(*, workspace, user, year, month, month_label, period, working_days, holidays, entries, expense_multiplier):
    worked_hours = Decimal("0.00")
    billable_hours = Decimal("0.00")
    non_billable_hours = Decimal("0.00")
    invoice_amount_czk = Decimal("0.00")
    breakdown = defaultdict(lambda: {"hours": Decimal("0.00"), "amount": Decimal("0.00"), "projects": defaultdict(lambda: {"hours": Decimal("0.00"), "amount": Decimal("0.00")})})

    for entry in entries:
        hours = entry.duration_hours
        worked_hours += hours
        if entry.is_billable:
            billable_hours += hours
            rate = entry.hourly_rate_czk
            amount = hours * rate
            invoice_amount_czk += amount
            client_bucket = breakdown[entry.project.client.name]
            client_bucket["hours"] += hours
            client_bucket["amount"] += amount
            project_bucket = client_bucket["projects"][entry.project.name]
            project_bucket["hours"] += hours
            project_bucket["amount"] += amount
        else:
            non_billable_hours += hours

    work_fund_hours = Decimal(working_days) * workspace.default_daily_hours
    monthly_regular_expenses = sum(
        (
            payment.amount_czk
            for payment in RegularPayment.objects.filter(workspace=workspace, user=user, is_active=True)
        ),
        start=Decimal("0.00"),
    )
    regular_expenses_czk = monthly_regular_expenses * expense_multiplier
    client_rows = [
        DashboardClientRow(
            client_name=client_name,
            billable_hours=data["hours"],
            amount_czk=data["amount"],
            projects=[
                DashboardProjectRow(project_name=project_name, billable_hours=project["hours"], amount_czk=project["amount"])
                for project_name, project in sorted(data["projects"].items())
            ],
        )
        for client_name, data in sorted(breakdown.items())
    ]

    return MonthlyDashboard(
        year=year,
        month=month,
        month_label=month_label,
        period=period,
        working_days=working_days,
        fund_holiday_count=sum(1 for holiday, _ in holidays if holiday.weekday() < 5),
        holiday_count=len(holidays),
        holidays=holidays,
        work_fund_hours=work_fund_hours,
        worked_hours=worked_hours,
        billable_hours=billable_hours,
        non_billable_hours=non_billable_hours,
        balance_hours=worked_hours - work_fund_hours,
        invoice_amount_czk=invoice_amount_czk,
        regular_expenses_czk=regular_expenses_czk,
        net_invoice_amount_czk=invoice_amount_czk - regular_expenses_czk,
        clients=client_rows,
    )
