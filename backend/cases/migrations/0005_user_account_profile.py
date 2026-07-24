from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cases", "0004_passenger_accounts"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="UserAccountProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("assigned_role", models.CharField(choices=[("SYSTEM_ADMIN", "System Admin"), ("COLLEAGUE", "Colleague"), ("PASSENGER", "Passenger")], max_length=20)),
                ("must_change_password", models.BooleanField(default=False)),
                ("password_sent_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.OneToOneField(on_delete=models.CASCADE, related_name="account_profile", to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]