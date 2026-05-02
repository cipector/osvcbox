from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("timebox", "0002_workentry_time_interval"),
    ]

    operations = [
        migrations.AddField(
            model_name="workentry",
            name="deduct_lunch_break",
            field=models.BooleanField(default=False),
        ),
    ]
