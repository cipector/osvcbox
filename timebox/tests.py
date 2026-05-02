from datetime import date, time
from decimal import Decimal
from io import BytesIO
from zipfile import ZipFile

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from .models import Client, Project, RegularPayment, WorkEntry, Workspace, WorkspaceMembership
from .holidays import czech_public_holidays_map
from .payments import czech_iban, regular_payment_qr_data_uri
from .selectors import get_dashboard, get_monthly_dashboard


class MonthlyDashboardTests(TestCase):
    def test_dashboard_counts_current_month_hours_and_rates(self):
        user = User.objects.create_user(username="anna", password="secret")
        workspace = Workspace.objects.create(
            name="Anna",
            default_daily_hours=Decimal("8.00"),
            default_hourly_rate_czk=Decimal("1000.00"),
        )
        client = Client.objects.create(
            workspace=workspace,
            name="Acme",
            default_hourly_rate_czk=Decimal("1200.00"),
        )
        project = Project.objects.create(
            workspace=workspace,
            client=client,
            name="Web",
            hourly_rate_czk=Decimal("1500.00"),
        )
        WorkEntry.objects.create(
            workspace=workspace,
            user=user,
            project=project,
            date=date(2026, 5, 1),
            start_time=time(9, 0),
            end_time=time(15, 0),
            is_billable=True,
        )
        WorkEntry.objects.create(
            workspace=workspace,
            user=user,
            project=project,
            date=date(2026, 5, 2),
            start_time=time(10, 0),
            end_time=time(12, 0),
            is_billable=False,
        )

        dashboard = get_monthly_dashboard(workspace=workspace, user=user, year=2026, month=5)

        self.assertEqual(dashboard.working_days, 19)
        self.assertEqual(dashboard.holiday_count, 2)
        self.assertEqual(dashboard.fund_holiday_count, 2)
        self.assertEqual([holiday.isoformat() for holiday, _ in dashboard.holidays], ["2026-05-01", "2026-05-08"])
        self.assertEqual(dashboard.work_fund_hours, Decimal("152.00"))
        self.assertEqual(dashboard.worked_hours, Decimal("8.00"))
        self.assertEqual(dashboard.billable_hours, Decimal("6.00"))
        self.assertEqual(dashboard.non_billable_hours, Decimal("2.00"))
        self.assertEqual(dashboard.balance_hours, Decimal("-144.00"))
        self.assertEqual(dashboard.invoice_amount_czk, Decimal("9000.0000"))
        self.assertEqual(dashboard.clients[0].client_name, "Acme")
        self.assertEqual(dashboard.clients[0].projects[0].project_name, "Web")

    def test_dashboard_uses_client_rate_when_project_rate_is_empty(self):
        user = User.objects.create_user(username="daniela", password="secret")
        workspace = Workspace.objects.create(name="Daniela", default_hourly_rate_czk=Decimal("900.00"))
        client = Client.objects.create(
            workspace=workspace,
            name="Client rate",
            default_hourly_rate_czk=Decimal("1100.00"),
        )
        project = Project.objects.create(workspace=workspace, client=client, name="Support")
        WorkEntry.objects.create(
            workspace=workspace,
            user=user,
            project=project,
            date=date(2026, 5, 4),
            start_time=time(8, 30),
            end_time=time(11, 0),
            is_billable=True,
        )

        dashboard = get_monthly_dashboard(workspace=workspace, user=user, year=2026, month=5)

        self.assertEqual(dashboard.billable_hours, Decimal("2.50"))
        self.assertEqual(dashboard.invoice_amount_czk, Decimal("2750.0000"))

    def test_lunch_break_is_deducted_from_dashboard_hours_and_amount(self):
        user = User.objects.create_user(username="eva", password="secret")
        workspace = Workspace.objects.create(name="Eva")
        client = Client.objects.create(workspace=workspace, name="Acme")
        project = Project.objects.create(
            workspace=workspace,
            client=client,
            name="Consulting",
            hourly_rate_czk=Decimal("1000.00"),
        )
        WorkEntry.objects.create(
            workspace=workspace,
            user=user,
            project=project,
            date=date(2026, 5, 5),
            start_time=time(9, 0),
            end_time=time(17, 0),
            deduct_lunch_break=True,
            is_billable=True,
        )

        dashboard = get_monthly_dashboard(workspace=workspace, user=user, year=2026, month=5)

        self.assertEqual(dashboard.worked_hours, Decimal("7.50"))
        self.assertEqual(dashboard.billable_hours, Decimal("7.50"))
        self.assertEqual(dashboard.invoice_amount_czk, Decimal("7500.0000"))

    def test_dashboard_can_count_whole_year(self):
        user = User.objects.create_user(username="yearly", password="secret")
        workspace = Workspace.objects.create(name="Yearly", default_daily_hours=Decimal("8.00"))
        client = Client.objects.create(workspace=workspace, name="Client")
        project = Project.objects.create(workspace=workspace, client=client, name="Project")
        WorkEntry.objects.create(
            workspace=workspace,
            user=user,
            project=project,
            date=date(2026, 1, 5),
            start_time=time(9, 0),
            end_time=time(11, 0),
            is_billable=True,
        )
        WorkEntry.objects.create(
            workspace=workspace,
            user=user,
            project=project,
            date=date(2026, 5, 5),
            start_time=time(9, 0),
            end_time=time(12, 0),
            is_billable=False,
        )

        dashboard = get_dashboard(workspace=workspace, user=user, year=2026, period="year")

        self.assertEqual(dashboard.month, None)
        self.assertEqual(dashboard.month_label, "2026")
        self.assertEqual(dashboard.working_days, 250)
        self.assertEqual(dashboard.worked_hours, Decimal("5.00"))

    def test_dashboard_deducts_regular_payments_from_net_amount(self):
        user = User.objects.create_user(username="netto", password="secret")
        workspace = Workspace.objects.create(name="Netto")
        client = Client.objects.create(workspace=workspace, name="Client")
        project = Project.objects.create(
            workspace=workspace,
            client=client,
            name="Project",
            hourly_rate_czk=Decimal("1000.00"),
        )
        WorkEntry.objects.create(
            workspace=workspace,
            user=user,
            project=project,
            date=date(2026, 5, 4),
            start_time=time(9, 0),
            end_time=time(17, 0),
            is_billable=True,
        )
        RegularPayment.objects.create(
            workspace=workspace,
            user=user,
            name="Telefon",
            amount_czk=Decimal("500.00"),
            account_number="123456789",
            bank_code="0100",
            reminder_day=10,
        )

        dashboard = get_monthly_dashboard(workspace=workspace, user=user, year=2026, month=5)

        self.assertEqual(dashboard.invoice_amount_czk, Decimal("8000.0000"))
        self.assertEqual(dashboard.regular_expenses_czk, Decimal("500.00"))
        self.assertEqual(dashboard.net_invoice_amount_czk, Decimal("7500.0000"))

    def test_dashboard_excludes_movable_czech_holidays(self):
        user = User.objects.create_user(username="easter", password="secret")
        workspace = Workspace.objects.create(name="Easter", default_daily_hours=Decimal("8.00"))

        dashboard = get_monthly_dashboard(workspace=workspace, user=user, year=2026, month=4)

        self.assertEqual(dashboard.working_days, 20)
        self.assertEqual(dashboard.holiday_count, 2)
        self.assertEqual(dashboard.fund_holiday_count, 2)
        self.assertEqual(dashboard.work_fund_hours, Decimal("160.00"))

    def test_holidays_library_returns_future_czech_holidays(self):
        holiday_map = czech_public_holidays_map(2027)

        self.assertIn(date(2027, 1, 1), holiday_map)
        self.assertIn(date(2027, 3, 26), holiday_map)
        self.assertIn(date(2027, 3, 29), holiday_map)

    def test_april_2027_has_no_czech_public_holidays(self):
        user = User.objects.create_user(username="april2027", password="secret")
        workspace = Workspace.objects.create(name="April", default_daily_hours=Decimal("8.00"))

        dashboard = get_monthly_dashboard(workspace=workspace, user=user, year=2027, month=4)

        self.assertEqual(dashboard.holiday_count, 0)
        self.assertEqual(dashboard.fund_holiday_count, 0)


class WorkEntryValidationTests(TestCase):
    def test_project_must_belong_to_entry_workspace(self):
        user = User.objects.create_user(username="bob", password="secret")
        workspace = Workspace.objects.create(name="Bob")
        other_workspace = Workspace.objects.create(name="Other")
        client = Client.objects.create(workspace=other_workspace, name="Other client")
        project = Project.objects.create(workspace=other_workspace, client=client, name="Other project")
        entry = WorkEntry(
            workspace=workspace,
            user=user,
            project=project,
            date=date(2026, 5, 1),
            start_time=time(9, 0),
            end_time=time(10, 0),
            is_billable=True,
        )

        with self.assertRaises(ValidationError):
            entry.full_clean()

    def test_end_time_must_be_after_start_time(self):
        user = User.objects.create_user(username="cyril", password="secret")
        workspace = Workspace.objects.create(name="Cyril")
        client = Client.objects.create(workspace=workspace, name="Client")
        project = Project.objects.create(workspace=workspace, client=client, name="Project")
        entry = WorkEntry(
            workspace=workspace,
            user=user,
            project=project,
            date=date(2026, 5, 1),
            start_time=time(10, 0),
            end_time=time(10, 0),
            is_billable=True,
        )

        with self.assertRaises(ValidationError):
            entry.full_clean()

    def test_lunch_break_cannot_make_duration_zero(self):
        user = User.objects.create_user(username="david", password="secret")
        workspace = Workspace.objects.create(name="David")
        client = Client.objects.create(workspace=workspace, name="Client")
        project = Project.objects.create(workspace=workspace, client=client, name="Project")
        entry = WorkEntry(
            workspace=workspace,
            user=user,
            project=project,
            date=date(2026, 5, 1),
            start_time=time(10, 0),
            end_time=time(10, 30),
            deduct_lunch_break=True,
            is_billable=True,
        )

        with self.assertRaises(ValidationError):
            entry.full_clean()


class WorkEntryReportTests(TestCase):
    def test_work_entry_create_has_default_day_hours_and_lunch(self):
        user = User.objects.create_user(username="defaulty", password="secret")
        workspace = Workspace.objects.create(name="Defaulty")
        WorkspaceMembership.objects.create(workspace=workspace, user=user)

        self.client.login(username="defaulty", password="secret")
        response = self.client.get(reverse("work_entry_create"))

        self.assertEqual(response.context["form"].initial["start_time"], time(8, 0))
        self.assertEqual(response.context["form"].initial["end_time"], time(16, 30))
        self.assertEqual(response.context["form"].initial["deduct_lunch_break"], True)
        self.assertIn("calendar", response.context)

    def test_work_entry_calendar_can_open_another_month(self):
        user = User.objects.create_user(username="calendar", password="secret")
        workspace = Workspace.objects.create(name="Kalendář")
        WorkspaceMembership.objects.create(workspace=workspace, user=user)

        self.client.login(username="calendar", password="secret")
        response = self.client.get(reverse("work_entry_create"), {"calendar_year": "2027", "calendar_month": "3"})

        self.assertEqual(response.context["calendar"]["label"], "03/2027")
        self.assertEqual(response.context["calendar"]["previous"], {"year": 2027, "month": 2})
        self.assertEqual(response.context["calendar"]["next"], {"year": 2027, "month": 4})

    def test_report_filters_entries_by_client(self):
        user = User.objects.create_user(username="franta", password="secret")
        workspace = Workspace.objects.create(name="Franta")
        WorkspaceMembership.objects.create(workspace=workspace, user=user)
        selected_client = Client.objects.create(workspace=workspace, name="Selected")
        other_client = Client.objects.create(workspace=workspace, name="Other")
        selected_project = Project.objects.create(workspace=workspace, client=selected_client, name="App")
        other_project = Project.objects.create(workspace=workspace, client=other_client, name="Ops")
        WorkEntry.objects.create(
            workspace=workspace,
            user=user,
            project=selected_project,
            date=date(2026, 5, 6),
            start_time=time(9, 0),
            end_time=time(11, 0),
            is_billable=True,
        )
        WorkEntry.objects.create(
            workspace=workspace,
            user=user,
            project=other_project,
            date=date(2026, 5, 6),
            start_time=time(12, 0),
            end_time=time(13, 0),
            is_billable=True,
        )

        self.client.login(username="franta", password="secret")
        response = self.client.get(
            reverse("work_entry_report"),
            {"year": "2026", "month": "5", "client": str(selected_client.id)},
        )

        self.assertEqual([entry.project.name for entry in response.context["entries"]], ["App"])

    def test_report_export_returns_client_named_xlsx_without_money_or_project(self):
        user = User.objects.create_user(username="gita", password="secret")
        workspace = Workspace.objects.create(name="Gita")
        WorkspaceMembership.objects.create(workspace=workspace, user=user)
        client = Client.objects.create(workspace=workspace, name="Export Client")
        project = Project.objects.create(workspace=workspace, client=client, name="Export project")
        WorkEntry.objects.create(
            workspace=workspace,
            user=user,
            project=project,
            date=date(2026, 5, 7),
            start_time=time(9, 0),
            end_time=time(17, 0),
            deduct_lunch_break=True,
            is_billable=True,
            note="Export note",
        )
        WorkEntry.objects.create(
            workspace=workspace,
            user=user,
            project=project,
            date=date(2026, 5, 7),
            start_time=time(18, 0),
            end_time=time(19, 15),
            is_billable=True,
            note="Second note",
        )

        self.client.login(username="gita", password="secret")
        response = self.client.get(
            reverse("work_entry_report"),
            {"year": "2026", "month": "5", "client": str(client.id), "export": "xlsx"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        self.assertIn("export-client-05-2026.xlsx", response["Content-Disposition"])
        workbook = ZipFile(BytesIO(response.content))
        worksheet = workbook.read("xl/worksheets/sheet1.xml").decode()
        self.assertIn("Datum", worksheet)
        self.assertIn("Začátek", worksheet)
        self.assertIn("Konec", worksheet)
        self.assertIn("Součet hodin", worksheet)
        self.assertIn("Export note", worksheet)
        self.assertIn("Second note", worksheet)
        self.assertIn("Součet celkem", worksheet)
        self.assertIn("<v>7.50</v>", worksheet)
        self.assertIn("<v>1.25</v>", worksheet)
        self.assertIn("<v>8.75</v>", worksheet)
        self.assertNotIn("Součet dne", worksheet)
        self.assertNotIn("Export project", worksheet)
        self.assertNotIn("Částka", worksheet)

    def test_work_entry_can_be_edited_by_owner(self):
        user = User.objects.create_user(username="hana", password="secret")
        workspace = Workspace.objects.create(name="Hana")
        WorkspaceMembership.objects.create(workspace=workspace, user=user)
        client = Client.objects.create(workspace=workspace, name="Client")
        project = Project.objects.create(workspace=workspace, client=client, name="Project")
        entry = WorkEntry.objects.create(
            workspace=workspace,
            user=user,
            project=project,
            date=date(2026, 5, 8),
            start_time=time(9, 0),
            end_time=time(10, 0),
            is_billable=True,
        )

        self.client.login(username="hana", password="secret")
        response = self.client.post(
            reverse("work_entry_update", args=[entry.id]),
            {
                "date": "2026-05-08",
                "project": str(project.id),
                "start_time": "09:00",
                "end_time": "11:30",
                "is_billable": "on",
                "note": "fixed",
            },
        )

        entry.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(entry.end_time, time(11, 30))
        self.assertEqual(entry.note, "fixed")

    def test_work_entry_can_be_deleted_by_owner(self):
        user = User.objects.create_user(username="mazani", password="secret")
        workspace = Workspace.objects.create(name="Mazání")
        WorkspaceMembership.objects.create(workspace=workspace, user=user)
        client = Client.objects.create(workspace=workspace, name="Klient")
        project = Project.objects.create(workspace=workspace, client=client, name="Projekt")
        entry = WorkEntry.objects.create(
            workspace=workspace,
            user=user,
            project=project,
            date=date(2026, 4, 1),
            start_time=time(9, 0),
            end_time=time(10, 0),
            is_billable=True,
        )

        self.client.login(username="mazani", password="secret")
        response = self.client.post(reverse("work_entry_delete", args=[entry.id]))

        self.assertEqual(response.status_code, 302)
        self.assertFalse(WorkEntry.objects.filter(id=entry.id).exists())


class RegularPaymentTests(TestCase):
    def test_czech_iban_is_generated_from_domestic_account(self):
        iban = czech_iban("", "19", "0800")

        self.assertEqual(iban, "CZ3308000000000000000019")
        self.assertEqual(int(f"{iban[4:]}1235{iban[2:4]}") % 97, 1)

    def test_regular_payment_can_be_created_and_qr_is_generated(self):
        user = User.objects.create_user(username="platby", password="secret")
        workspace = Workspace.objects.create(name="Platby")
        WorkspaceMembership.objects.create(workspace=workspace, user=user)

        self.client.login(username="platby", password="secret")
        response = self.client.post(
            reverse("regular_payment_create"),
            {
                "name": "Telefon",
                "amount_czk": "499.00",
                "account_prefix": "",
                "account_number": "19",
                "bank_code": "0800",
                "variable_symbol": "123",
                "message": "pausal",
                "reminder_day": "15",
                "is_active": "on",
            },
        )

        self.assertEqual(response.status_code, 302)
        payment = RegularPayment.objects.get(workspace=workspace, user=user)
        self.assertEqual(payment.name, "Telefon")
        self.assertTrue(regular_payment_qr_data_uri(payment).startswith("data:image/svg+xml;base64,"))
