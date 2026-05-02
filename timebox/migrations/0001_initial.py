# Generated manually for the initial osvcbox schema.

import decimal
import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Workspace",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                (
                    "default_daily_hours",
                    models.DecimalField(
                        decimal_places=2,
                        default=decimal.Decimal("8.00"),
                        max_digits=4,
                        validators=[
                            django.core.validators.MinValueValidator(decimal.Decimal("0.01")),
                            django.core.validators.MaxValueValidator(decimal.Decimal("24.00")),
                        ],
                    ),
                ),
                ("default_hourly_rate_czk", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name="Client",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=160)),
                ("default_hourly_rate_czk", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("workspace", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="clients", to="timebox.workspace")),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="WorkspaceMembership",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="workspace_memberships", to=settings.AUTH_USER_MODEL)),
                ("workspace", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="memberships", to="timebox.workspace")),
            ],
        ),
        migrations.CreateModel(
            name="Project",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=160)),
                ("hourly_rate_czk", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("client", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="projects", to="timebox.client")),
                ("workspace", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="projects", to="timebox.workspace")),
            ],
            options={"ordering": ["client__name", "name"]},
        ),
        migrations.CreateModel(
            name="WorkEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("date", models.DateField()),
                (
                    "hours",
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=5,
                        validators=[
                            django.core.validators.MinValueValidator(decimal.Decimal("0.01")),
                            django.core.validators.MaxValueValidator(decimal.Decimal("24.00")),
                        ],
                    ),
                ),
                ("is_billable", models.BooleanField(default=True)),
                ("note", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("project", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="work_entries", to="timebox.project")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="work_entries", to=settings.AUTH_USER_MODEL)),
                ("workspace", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="work_entries", to="timebox.workspace")),
            ],
            options={"ordering": ["-date", "-created_at"]},
        ),
        migrations.AddConstraint(
            model_name="client",
            constraint=models.UniqueConstraint(fields=("workspace", "name"), name="unique_client_name_per_workspace"),
        ),
        migrations.AddConstraint(
            model_name="workspacemembership",
            constraint=models.UniqueConstraint(fields=("workspace", "user"), name="unique_workspace_user"),
        ),
        migrations.AddConstraint(
            model_name="project",
            constraint=models.UniqueConstraint(fields=("workspace", "client", "name"), name="unique_project_name_per_client"),
        ),
    ]
