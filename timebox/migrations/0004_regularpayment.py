import django.core.validators
import django.db.models.deletion
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("timebox", "0003_workentry_deduct_lunch_break"),
    ]

    operations = [
        migrations.CreateModel(
            name="RegularPayment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=160)),
                (
                    "amount_czk",
                    models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal("0.01"))]),
                ),
                ("account_prefix", models.CharField(blank=True, max_length=6)),
                ("account_number", models.CharField(max_length=10)),
                ("bank_code", models.CharField(max_length=4)),
                ("variable_symbol", models.CharField(blank=True, max_length=10)),
                ("message", models.CharField(blank=True, max_length=140)),
                ("reminder_day", models.PositiveSmallIntegerField(validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(31)])),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="regular_payments", to=settings.AUTH_USER_MODEL)),
                ("workspace", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="regular_payments", to="timebox.workspace")),
            ],
            options={"ordering": ["reminder_day", "name"]},
        ),
    ]
