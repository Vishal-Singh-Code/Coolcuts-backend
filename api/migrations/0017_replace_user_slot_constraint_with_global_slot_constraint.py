from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0016_appointment_unique_user_appointment_slot"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="appointment",
            name="unique_user_appointment_slot",
        ),
        migrations.AddConstraint(
            model_name="appointment",
            constraint=models.UniqueConstraint(
                fields=("appointment_date", "appointment_time"),
                name="unique_appointment_slot",
            ),
        ),
    ]
