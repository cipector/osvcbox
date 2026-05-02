from calendar import monthcalendar, monthrange
from datetime import date, time

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

from .forms import ClientForm, ProjectForm, RegularPaymentForm, WorkEntryForm, WorkspaceSettingsForm
from .exports import build_work_entries_xlsx
from .holidays import czech_public_holidays_map
from .models import Client, Project, RegularPayment, WorkEntry, Workspace, WorkspaceMembership
from .payments import regular_payment_qr_data_uri
from .selectors import get_dashboard


def get_current_workspace(user: User):
    membership = (
        WorkspaceMembership.objects.filter(user=user)
        .select_related("workspace")
        .order_by("workspace_id")
        .first()
    )
    if membership:
        return membership.workspace

    workspace = Workspace.objects.create(name=f"Pracovní prostor {user.username}")
    WorkspaceMembership.objects.create(workspace=workspace, user=user)
    return workspace


@login_required
def dashboard(request):
    workspace = get_current_workspace(request.user)
    today = timezone.localdate()
    period = request.GET.get("period", "month")
    if period not in {"month", "year"}:
        period = "month"
    year = _parse_int(request.GET.get("year"), today.year)
    month = _parse_int(request.GET.get("month"), today.month)
    if year < 1 or year > 9999:
        year = today.year
    if month < 1 or month > 12:
        month = today.month
    data = get_dashboard(workspace=workspace, user=request.user, year=year, month=month, period=period)
    return render(
        request,
        "timebox/dashboard.html",
        {
            "workspace": workspace,
            "dashboard": data,
            "period": period,
            "year": year,
            "month": month,
        },
    )


@login_required
def workspace_settings(request):
    workspace = get_current_workspace(request.user)
    if request.method == "POST":
        form = WorkspaceSettingsForm(request.POST, instance=workspace)
        if form.is_valid():
            form.save()
            return redirect("dashboard")
    else:
        form = WorkspaceSettingsForm(instance=workspace)
    return render(request, "timebox/form.html", {"title": "Nastavení pracovního prostoru", "form": form})


@login_required
def client_list(request):
    workspace = get_current_workspace(request.user)
    clients = Client.objects.filter(workspace=workspace)
    return render(request, "timebox/client_list.html", {"workspace": workspace, "clients": clients})


@login_required
def client_create(request):
    workspace = get_current_workspace(request.user)
    if request.method == "POST":
        form = ClientForm(request.POST)
        if form.is_valid():
            client = form.save(commit=False)
            client.workspace = workspace
            client.save()
            return redirect("client_list")
    else:
        form = ClientForm()
    return render(request, "timebox/form.html", {"title": "Nový klient", "form": form})


@login_required
def project_list(request):
    workspace = get_current_workspace(request.user)
    projects = Project.objects.filter(workspace=workspace).select_related("client")
    return render(request, "timebox/project_list.html", {"workspace": workspace, "projects": projects})


@login_required
def project_create(request):
    workspace = get_current_workspace(request.user)
    if request.method == "POST":
        form = ProjectForm(request.POST, workspace=workspace)
        if form.is_valid():
            project = form.save(commit=False)
            project.workspace = workspace
            project.save()
            return redirect("project_list")
    else:
        form = ProjectForm(workspace=workspace)
    return render(request, "timebox/form.html", {"title": "Nový projekt", "form": form})


@login_required
def regular_payment_list(request):
    workspace = get_current_workspace(request.user)
    payments = []
    for payment in RegularPayment.objects.filter(workspace=workspace, user=request.user):
        payments.append({"payment": payment, "qr_data_uri": regular_payment_qr_data_uri(payment)})
    return render(request, "timebox/regular_payment_list.html", {"workspace": workspace, "payments": payments})


@login_required
def regular_payment_create(request):
    workspace = get_current_workspace(request.user)
    if request.method == "POST":
        form = RegularPaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.workspace = workspace
            payment.user = request.user
            payment.save()
            return redirect("regular_payment_list")
    else:
        form = RegularPaymentForm(initial={"is_active": True})
    return render(request, "timebox/form.html", {"title": "Nová pravidelná platba", "form": form})


@login_required
def regular_payment_update(request, pk):
    workspace = get_current_workspace(request.user)
    payment = get_object_or_404(RegularPayment, pk=pk, workspace=workspace, user=request.user)
    if request.method == "POST":
        form = RegularPaymentForm(request.POST, instance=payment)
        if form.is_valid():
            form.save()
            return redirect("regular_payment_list")
    else:
        form = RegularPaymentForm(instance=payment)
    return render(request, "timebox/form.html", {"title": "Upravit pravidelnou platbu", "form": form})


@login_required
def work_entry_create(request):
    workspace = get_current_workspace(request.user)
    today = timezone.localdate()
    if request.method == "POST":
        form = WorkEntryForm(request.POST, workspace=workspace)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.workspace = workspace
            entry.user = request.user
            entry.save()
            return redirect("dashboard")
        calendar_date = _parse_date(request.POST.get("date"), today)
    else:
        calendar_date = _calendar_date_from_request(request, today)
        form = WorkEntryForm(
            workspace=workspace,
            initial={
                "date": today,
                "start_time": time(8, 0),
                "end_time": time(16, 30),
                "deduct_lunch_break": True,
                "is_billable": True,
            },
        )
    return render(
        request,
        "timebox/work_entry_form.html",
        {"title": "Zapsat hodiny", "form": form, "calendar": _work_entry_calendar(calendar_date)},
    )


@login_required
def work_entry_update(request, pk):
    workspace = get_current_workspace(request.user)
    entry = get_object_or_404(WorkEntry, pk=pk, workspace=workspace, user=request.user)
    if request.method == "POST":
        form = WorkEntryForm(request.POST, workspace=workspace, instance=entry)
        if form.is_valid():
            form.save()
            return redirect("work_entry_report")
        calendar_date = _parse_date(request.POST.get("date"), entry.date)
    else:
        form = WorkEntryForm(workspace=workspace, instance=entry)
        calendar_date = _calendar_date_from_request(request, entry.date)
    return render(
        request,
        "timebox/work_entry_form.html",
        {"title": "Upravit hodiny", "form": form, "calendar": _work_entry_calendar(calendar_date)},
    )


@login_required
def work_entry_delete(request, pk):
    workspace = get_current_workspace(request.user)
    entry = get_object_or_404(WorkEntry, pk=pk, workspace=workspace, user=request.user)
    if request.method == "POST":
        year = entry.date.year
        month = entry.date.month
        entry.delete()
        return redirect(f"{reverse('work_entry_report')}?year={year}&month={month}")
    return redirect("work_entry_report")


@login_required
def work_entry_report(request):
    workspace = get_current_workspace(request.user)
    today = timezone.localdate()
    year = _parse_int(request.GET.get("year"), today.year)
    month = _parse_int(request.GET.get("month"), today.month)
    if year < 1 or year > 9999:
        year = today.year
    if month < 1 or month > 12:
        month = today.month

    selected_client_id = _parse_int(request.GET.get("client"), None)
    selected_project_id = _parse_int(request.GET.get("project"), None)
    entries = _filtered_work_entries(
        workspace=workspace,
        user=request.user,
        year=year,
        month=month,
        client_id=selected_client_id,
        project_id=selected_project_id,
    )

    if request.GET.get("export") == "xlsx":
        response = HttpResponse(
            build_work_entries_xlsx(entries),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="{_work_entry_export_filename(workspace, selected_client_id, selected_project_id, year, month)}"'
        return response

    export_query = request.GET.copy()
    export_query["export"] = "xlsx"
    return render(
        request,
        "timebox/work_entry_report.html",
        {
            "workspace": workspace,
            "entries": entries,
            "clients": Client.objects.filter(workspace=workspace),
            "projects": Project.objects.filter(workspace=workspace).select_related("client"),
            "selected_client_id": selected_client_id,
            "selected_project_id": selected_project_id,
            "year": year,
            "month": month,
            "totals": _work_entry_report_totals(entries),
            "export_query": export_query.urlencode(),
        },
    )


def _filtered_work_entries(*, workspace, user, year, month, client_id, project_id):
    _, last_day = monthrange(year, month)
    entries = (
        WorkEntry.objects.filter(
            workspace=workspace,
            user=user,
            date__gte=f"{year}-{month:02d}-01",
            date__lte=f"{year}-{month:02d}-{last_day:02d}",
        )
        .select_related("project", "project__client", "workspace")
        .order_by("date", "start_time", "id")
    )
    if client_id:
        entries = entries.filter(project__client_id=client_id, project__client__workspace=workspace)
    if project_id:
        entries = entries.filter(project_id=project_id, project__workspace=workspace)
    return list(entries)


def _work_entry_report_totals(entries):
    return {
        "worked_hours": sum((entry.duration_hours for entry in entries), start=0),
        "billable_hours": sum((entry.duration_hours for entry in entries if entry.is_billable), start=0),
        "amount_czk": sum((entry.invoice_amount_czk for entry in entries), start=0),
    }


def _parse_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse_date(value, default):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return default


def _calendar_date_from_request(request, default):
    year = _parse_int(request.GET.get("calendar_year"), default.year)
    month = _parse_int(request.GET.get("calendar_month"), default.month)
    if year < 1 or year > 9999:
        year = default.year
    if month < 1 or month > 12:
        month = default.month
    day = default.day if year == default.year and month == default.month else 1
    _, last_day = monthrange(year, month)
    return date(year, month, min(day, last_day))


def _work_entry_calendar(selected_date):
    holidays = czech_public_holidays_map(selected_date.year)
    weeks = []
    for week in monthcalendar(selected_date.year, selected_date.month):
        week_days = []
        for day_number in week:
            if not day_number:
                week_days.append({"day": "", "in_month": False})
                continue
            current = date(selected_date.year, selected_date.month, day_number)
            holiday_name = holidays.get(current)
            week_days.append(
                {
                    "day": day_number,
                    "date": current.isoformat(),
                    "in_month": True,
                    "is_weekend": current.weekday() >= 5,
                    "is_holiday": bool(holiday_name),
                    "holiday_name": holiday_name,
                    "is_selected": current == selected_date,
                    "is_today": current == timezone.localdate(),
                }
            )
        weeks.append(week_days)
    return {
        "label": f"{selected_date.month:02d}/{selected_date.year}",
        "previous": _shift_month(selected_date, -1),
        "next": _shift_month(selected_date, 1),
        "weeks": weeks,
    }


def _shift_month(value, offset):
    month_index = value.year * 12 + value.month - 1 + offset
    year, month_zero_based = divmod(month_index, 12)
    return {"year": year, "month": month_zero_based + 1}


def _work_entry_export_filename(workspace, client_id, project_id, year, month):
    client = None
    if client_id:
        client = Client.objects.filter(workspace=workspace, id=client_id).first()
    elif project_id:
        project = Project.objects.filter(workspace=workspace, id=project_id).select_related("client").first()
        client = project.client if project else None
    label = client.name if client else workspace.name
    safe_label = slugify(label) or "rozpis"
    return f"{safe_label}-{month:02d}-{year}.xlsx"
