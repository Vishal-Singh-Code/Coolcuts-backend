from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("user", "0003_emailotp"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="profile",
            name="role",
        ),
    ]
