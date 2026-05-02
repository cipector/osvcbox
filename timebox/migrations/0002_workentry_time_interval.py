import datetime

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("timebox", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="workentry",
            name="start_time",
            field=models.TimeField(default=datetime.time(9, 0)),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="workentry",
            name="end_time",
            field=models.TimeField(default=datetime.time(17, 0)),
            preserve_default=False,
        ),
        migrations.RemoveField(
            model_name="workentry",
            name="hours",
        ),
    ]
