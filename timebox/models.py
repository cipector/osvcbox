from datetime import datetime
from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Workspace(models.Model):
    name = models.CharField(max_length=120)
    default_daily_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal("8.00"),
        validators=[MinValueValidator(Decimal("0.01")), MaxValueValidator(Decimal("24.00"))],
    )
    default_hourly_rate_czk = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class WorkspaceMembership(models.Model):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="workspace_memberships")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["workspace", "user"], name="unique_workspace_user"),
        ]

    def __str__(self):
        return f"{self.user} @ {self.workspace}"


class Client(models.Model):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="clients")
    name = models.CharField(max_length=160)
    default_hourly_rate_czk = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["workspace", "name"], name="unique_client_name_per_workspace"),
        ]

    def __str__(self):
        return self.name


class Project(models.Model):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="projects")
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="projects")
    name = models.CharField(max_length=160)
    hourly_rate_czk = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["client__name", "name"]
        constraints = [
            models.UniqueConstraint(fields=["workspace", "client", "name"], name="unique_project_name_per_client"),
        ]

    def clean(self):
        if self.client_id and self.workspace_id and self.client.workspace_id != self.workspace_id:
            from django.core.exceptions import ValidationError

            raise ValidationError({"client": "Klient musí patřit do aktuálního pracovního prostoru."})

    def __str__(self):
        return f"{self.client.name} / {self.name}"


class WorkEntry(models.Model):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="work_entries")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="work_entries")
    project = models.ForeignKey(Project, on_delete=models.PROTECT, related_name="work_entries")
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    deduct_lunch_break = models.BooleanField(default=False)
    is_billable = models.BooleanField(default=True)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-created_at"]

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.project_id and self.workspace_id and self.project.workspace_id != self.workspace_id:
            raise ValidationError({"project": "Projekt musí patřit do aktuálního pracovního prostoru."})

        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValidationError({"end_time": "Konec musí být později než začátek."})

        if self.date and self.start_time and self.end_time and self.duration_hours <= Decimal("0.00"):
            raise ValidationError({"deduct_lunch_break": "Po odečtení oběda musí být délka záznamu větší než 0 hodin."})

        if self.date and self.start_time and self.end_time and self.duration_hours > Decimal("24.00"):
            raise ValidationError({"end_time": "Záznam může mít maximálně 24 hodin."})

    @property
    def duration_hours(self):
        if not self.start_time or not self.end_time:
            return Decimal("0.00")
        start = datetime.combine(self.date, self.start_time)
        end = datetime.combine(self.date, self.end_time)
        seconds = Decimal((end - start).total_seconds())
        hours = seconds / Decimal("3600")
        if self.deduct_lunch_break:
            hours -= Decimal("0.50")
        return hours.quantize(Decimal("0.01"))

    @property
    def hourly_rate_czk(self):
        return (
            self.project.hourly_rate_czk
            or self.project.client.default_hourly_rate_czk
            or self.workspace.default_hourly_rate_czk
            or Decimal("0.00")
        )

    @property
    def invoice_amount_czk(self):
        if not self.is_billable:
            return Decimal("0.00")
        return self.duration_hours * self.hourly_rate_czk

    def __str__(self):
        return f"{self.date} - {self.project} - {self.duration_hours} h"


class RegularPayment(models.Model):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="regular_payments")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="regular_payments")
    name = models.CharField(max_length=160)
    amount_czk = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    account_prefix = models.CharField(max_length=6, blank=True)
    account_number = models.CharField(max_length=10)
    bank_code = models.CharField(max_length=4)
    variable_symbol = models.CharField(max_length=10, blank=True)
    message = models.CharField(max_length=140, blank=True)
    reminder_day = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(31)],
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["reminder_day", "name"]

    def __str__(self):
        return self.name
