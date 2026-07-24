from __future__ import annotations

import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import get_random_string

from .models import AccountRole, PassengerAccount, UserAccountProfile


PASSWORD_ALPHABET = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789!@#$%^&*"

logger = logging.getLogger(__name__)


def _send_account_email(
    *,
    first_name: str,
    normalized_email: str,
    temporary_password: str,
    account_label: str,
) -> None:
    try:
        send_mail(
            subject=f"Your AirAssist {account_label} account",
            message=(
                f"Hello {first_name},\n\n"
                f"Your AirAssist {account_label} account is ready.\n"
                f"Sign in with your email address ({normalized_email}) and this temporary password: {temporary_password}\n\n"
                "For security reasons, you must change this password the first time you log in."
            ),
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@airassist.local"),
            recipient_list=[normalized_email],
            fail_silently=False,
        )
    except Exception:
        logger.exception("Account email delivery failed for %s", normalized_email)


def _upsert_account_profile(*, user, assigned_role: str, must_change_password: bool) -> UserAccountProfile:
    profile, _ = UserAccountProfile.objects.get_or_create(
        user=user,
        defaults={
            "assigned_role": assigned_role,
            "must_change_password": must_change_password,
            "password_sent_at": timezone.now() if must_change_password else None,
        },
    )
    profile.assigned_role = assigned_role
    profile.must_change_password = must_change_password
    profile.password_sent_at = timezone.now() if must_change_password else None
    profile.save(update_fields=["assigned_role", "must_change_password", "password_sent_at", "updated_at"])
    return profile


def provision_passenger_account(*, first_name: str, last_name: str, email: str):
    normalized_email = email.strip().lower()
    user_model = get_user_model()
    user = user_model.objects.filter(username__iexact=normalized_email).first()
    temporary_password = get_random_string(14, PASSWORD_ALPHABET)

    if user is None:
        user = user_model.objects.create_user(
            username=normalized_email,
            email=normalized_email,
            first_name=first_name,
            last_name=last_name,
            password=temporary_password,
        )
    else:
        user.email = normalized_email
        user.first_name = first_name
        user.last_name = last_name
        user.set_password(temporary_password)
        user.save(update_fields=["email", "first_name", "last_name", "password"])

    account, _ = PassengerAccount.objects.get_or_create(user=user)
    account.must_change_password = True
    account.save(update_fields=["must_change_password", "updated_at"])
    _upsert_account_profile(
        user=user,
        assigned_role=AccountRole.PASSENGER,
        must_change_password=True,
    )

    transaction.on_commit(
        lambda: _send_account_email(
            first_name=first_name,
            normalized_email=normalized_email,
            temporary_password=temporary_password,
            account_label="passenger",
        )
    )
    return user


def provision_colleague_account(*, first_name: str, last_name: str, email: str, password: str):
    normalized_email = email.strip().lower()
    user_model = get_user_model()
    user = user_model.objects.filter(username__iexact=normalized_email).first()

    if user is None:
        user = user_model.objects.create_user(
            username=normalized_email,
            email=normalized_email,
            first_name=first_name,
            last_name=last_name,
            password=password,
        )
    else:
        user.email = normalized_email
        user.first_name = first_name
        user.last_name = last_name
        user.is_staff = False
        user.is_superuser = False
        user.set_password(password)
        user.save(update_fields=["email", "first_name", "last_name", "is_staff", "is_superuser", "password"])

    _upsert_account_profile(
        user=user,
        assigned_role=AccountRole.COLLEAGUE,
        must_change_password=True,
    )

    transaction.on_commit(
        lambda: _send_account_email(
            first_name=first_name,
            normalized_email=normalized_email,
            temporary_password=password,
            account_label="colleague",
        )
    )
    return user