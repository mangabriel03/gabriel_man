from __future__ import annotations

import base64
import copy
import json
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.storage import default_storage
from django.core import mail
from django.utils import timezone
from rest_framework.test import APIClient

from cases.compensation.exceptions import DistanceUnavailable
from cases.models import AccountRole, Case, CaseDocument, FlightSegment, PassengerAccount, UserAccountProfile


# Minimal valid 1x1 PNG (with IHDR + IDAT + IEND chunks) — libmagic requires
# more than the 8-byte signature to reliably detect image/png.
PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
)
PDF_BYTES = b"%PDF-1.4\n" + b"\x00" * 32


def _make_multipart(payload: dict) -> dict:
    return {
        "payload": json.dumps(payload),
        "boarding_pass": SimpleUploadedFile(
            "bp.png", PNG_BYTES, content_type="image/png"
        ),
        "id_document": SimpleUploadedFile(
            "id.pdf", PDF_BYTES, content_type="application/pdf"
        ),
    }


@pytest.mark.django_db
def test_happy_path_creates_case_with_files(two_airports, valid_payload, settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    client = APIClient()
    # Force the Airport Gap primary source to fail so the deterministic
    # Haversine fallback runs against the seeded lat/lon in ``two_airports``.
    # This keeps the test hermetic (no network) while still exercising the
    # real compensation pipeline end-to-end.
    from cases.compensation.distance import _AirportGapError
    with patch(
        "cases.compensation.distance._airportgap_km",
        side_effect=_AirportGapError("forced fallback in test"),
    ), patch(
        "cases.account_service.transaction.on_commit",
        side_effect=lambda callback: callback(),
    ):
        resp = client.post("/api/cases/", _make_multipart(valid_payload), format="multipart")
    assert resp.status_code == 201, resp.content
    body = resp.json()
    assert "id" in body and body["status"] == "NEW"
    assert body["compensation_error"] is None
    assert body["compensation_amount_eur"] in {250, 400, 600}
    assert body["distance_km"] is not None

    case = Case.objects.get(id=body["id"])
    user = get_user_model().objects.get(email=valid_payload["passenger"]["email"])
    assert case.segments.count() == 1
    assert case.documents.count() == 2
    assert case.user == user
    assert user.passenger_account.must_change_password is True
    assert case.compensation_amount_eur == body["compensation_amount_eur"]
    assert case.compensation_calculated_at is not None
    assert len(mail.outbox) == 1
    assert valid_payload["passenger"]["email"] in mail.outbox[0].to
    assert "temporary password" in mail.outbox[0].body.lower()
    for doc in case.documents.all():
        assert Path(default_storage.path(doc.file.name)).exists()


@pytest.mark.django_db
def test_passenger_can_log_in_then_must_change_password(
    two_airports, valid_payload, settings, tmp_path,
):
    settings.MEDIA_ROOT = str(tmp_path)
    client = APIClient()
    from cases.compensation.distance import _AirportGapError
    with patch(
        "cases.compensation.distance._airportgap_km",
        side_effect=_AirportGapError("forced fallback in test"),
    ), patch(
        "cases.account_service.transaction.on_commit",
        side_effect=lambda callback: callback(),
    ):
        create_resp = client.post(
            "/api/cases/", _make_multipart(valid_payload), format="multipart",
        )
    assert create_resp.status_code == 201, create_resp.content
    email_body = mail.outbox[0].body
    marker = "temporary password: "
    start = email_body.index(marker) + len(marker)
    temporary_password = email_body[start:].splitlines()[0].strip()

    login_resp = client.post(
        "/api/auth/login/",
        {"email": valid_payload["passenger"]["email"], "password": temporary_password},
        format="json",
    )
    assert login_resp.status_code == 200, login_resp.content
    assert login_resp.json()["must_change_password"] is True

    change_resp = client.post(
        "/api/auth/change-password/",
        {
            "email": valid_payload["passenger"]["email"],
            "current_password": temporary_password,
            "new_password": "EvenBetterPass123!",
        },
        format="json",
    )
    assert change_resp.status_code == 200, change_resp.content
    assert change_resp.json()["must_change_password"] is False

    second_login_resp = client.post(
        "/api/auth/login/",
        {"email": valid_payload["passenger"]["email"], "password": "EvenBetterPass123!"},
        format="json",
    )
    assert second_login_resp.status_code == 200, second_login_resp.content
    assert second_login_resp.json()["must_change_password"] is False
    assert second_login_resp.json()["role"] == "PASSENGER"


@pytest.mark.django_db
def test_admin_login_returns_admin_role_without_creating_passenger_account():
    user = get_user_model().objects.create_user(
        username="admin@example.com",
        email="admin@example.com",
        password="AdminPass123!",
        first_name="Ada",
        last_name="Admin",
        is_staff=True,
    )
    client = APIClient()

    resp = client.post(
        "/api/auth/login/",
        {"email": user.email, "password": "AdminPass123!"},
        format="json",
    )

    assert resp.status_code == 200, resp.content
    assert resp.json()["role"] == "SYSTEM_ADMIN"
    assert resp.json()["must_change_password"] is False
    assert PassengerAccount.objects.filter(user=user).exists() is False


@pytest.mark.django_db
def test_admin_user_list_returns_roles_and_assigned_case_counts(two_airports):
    user_model = get_user_model()
    admin_user = user_model.objects.create_user(
        username="admin@example.com",
        email="admin@example.com",
        password="AdminPass123!",
        first_name="Ada",
        last_name="Admin",
        is_staff=True,
    )
    colleague = user_model.objects.create_user(
        username="colleague@example.com",
        email="colleague@example.com",
        password="ColleaguePass123!",
        first_name="Cole",
        last_name="League",
    )
    passenger = user_model.objects.create_user(
        username="passenger@example.com",
        email="passenger@example.com",
        password="PassengerPass123!",
        first_name="Pia",
        last_name="Passenger",
    )
    PassengerAccount.objects.create(user=passenger, must_change_password=False)
    Case.objects.create(
        first_name="Pia",
        last_name="Passenger",
        date_of_birth="1990-01-01",
        email=passenger.email,
        user=passenger,
        phone="+40 712 345 678",
        address="Example 1",
        postal_code="010101",
        reservation_number="ABC123",
        gdpr_consent=True,
        gdpr_consent_at=timezone.now(),
        disruption_type="DELAY",
        delay_duration="MORE_THAN_3H",
        airline_motive_mentioned="DONT_KNOW",
        incident_description="Delayed flight.",
    )
    Case.objects.create(
        first_name="Pia",
        last_name="Passenger",
        date_of_birth="1990-01-01",
        email=passenger.email,
        user=passenger,
        phone="+40 712 345 678",
        address="Example 2",
        postal_code="010101",
        reservation_number="DEF456",
        gdpr_consent=True,
        gdpr_consent_at=timezone.now(),
        disruption_type="DELAY",
        delay_duration="MORE_THAN_3H",
        airline_motive_mentioned="DONT_KNOW",
        incident_description="Another delayed flight.",
    )

    client = APIClient()
    client.force_authenticate(user=admin_user)
    resp = client.get("/api/admin/users/")

    assert resp.status_code == 200, resp.content
    body = resp.json()
    assert body == [
        {
            "id": admin_user.id,
            "name": "Ada Admin",
            "email": "admin@example.com",
            "role": "SYSTEM_ADMIN",
            "assigned_case_count": 0,
        },
        {
            "id": colleague.id,
            "name": "Cole League",
            "email": "colleague@example.com",
            "role": "COLLEAGUE",
            "assigned_case_count": 0,
        },
        {
            "id": passenger.id,
            "name": "Pia Passenger",
            "email": "passenger@example.com",
            "role": "PASSENGER",
            "assigned_case_count": 2,
        },
    ]


@pytest.mark.django_db
def test_admin_user_list_rejects_non_admin():
    user = get_user_model().objects.create_user(
        username="user@example.com",
        email="user@example.com",
        password="UserPass123!",
    )
    client = APIClient()
    client.force_authenticate(user=user)

    resp = client.get("/api/admin/users/")

    assert resp.status_code == 403


@pytest.mark.django_db
def test_admin_navigation_returns_expected_links():
    admin_user = get_user_model().objects.create_user(
        username="admin@example.com",
        email="admin@example.com",
        password="AdminPass123!",
        first_name="Ada",
        last_name="Admin",
        is_staff=True,
    )
    client = APIClient()
    client.force_authenticate(user=admin_user)

    resp = client.get("/api/admin/navigation/")

    assert resp.status_code == 200, resp.content
    assert resp.json() == {
        "actions": [
            {
                "key": "new-user",
                "label": "New User View",
                "href": "/admin/users#create-user",
                "description": "Create colleague accounts with a temporary password.",
            },
            {
                "key": "user-view",
                "label": "User View",
                "href": "/admin/users",
                "description": "Review all accounts, roles, and assigned case volume.",
            },
            {
                "key": "case-view",
                "label": "Case View",
                "href": "/admin/cases",
                "description": "Open the full case directory and manage stored records.",
            },
            {
                "key": "system-view",
                "label": "System View",
                "href": "/admin/system",
                "description": "Open system options and configuration placeholders.",
            },
        ],
    }


@pytest.mark.django_db
def test_admin_navigation_rejects_non_admin():
    user = get_user_model().objects.create_user(
        username="user@example.com",
        email="user@example.com",
        password="UserPass123!",
    )
    client = APIClient()
    client.force_authenticate(user=user)

    resp = client.get("/api/admin/navigation/")

    assert resp.status_code == 403


@pytest.mark.django_db
def test_admin_can_create_colleague_account(settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    user_model = get_user_model()
    admin_user = user_model.objects.create_user(
        username="admin@example.com",
        email="admin@example.com",
        password="AdminPass123!",
        first_name="Ada",
        last_name="Admin",
        is_staff=True,
    )
    client = APIClient()
    client.force_authenticate(user=admin_user)

    with patch(
        "cases.account_service.transaction.on_commit",
        side_effect=lambda callback: callback(),
    ):
        resp = client.post(
            "/api/admin/users/",
            {
                "first_name": "Cole",
                "last_name": "League",
                "email": "colleague@example.com",
                "password": "ColleaguePass123!",
            },
            format="json",
        )

    assert resp.status_code == 201, resp.content
    assert resp.json()["detail"] == (
        "Account created for colleague@example.com. "
        "The temporary password was emailed to the colleague."
    )

    colleague = user_model.objects.get(email="colleague@example.com")
    profile = UserAccountProfile.objects.get(user=colleague)
    assert colleague.first_name == "Cole"
    assert colleague.last_name == "League"
    assert colleague.is_staff is False
    assert profile.assigned_role == AccountRole.COLLEAGUE
    assert profile.must_change_password is True
    assert profile.password_sent_at is not None
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["colleague@example.com"]
    assert "temporary password" in mail.outbox[0].body.lower()

    login_resp = client.post(
        "/api/auth/login/",
        {"email": "colleague@example.com", "password": "ColleaguePass123!"},
        format="json",
    )
    assert login_resp.status_code == 200, login_resp.content
    assert login_resp.json()["role"] == AccountRole.COLLEAGUE
    assert login_resp.json()["must_change_password"] is True


@pytest.mark.django_db
def test_admin_user_create_rejects_non_admin():
    user = get_user_model().objects.create_user(
        username="user@example.com",
        email="user@example.com",
        password="UserPass123!",
    )
    client = APIClient()
    client.force_authenticate(user=user)

    resp = client.post(
        "/api/admin/users/",
        {
            "first_name": "Cole",
            "last_name": "League",
            "email": "colleague@example.com",
            "password": "ColleaguePass123!",
        },
        format="json",
    )

    assert resp.status_code == 403


@pytest.mark.django_db
def test_admin_case_list_returns_case_summary(two_airports):
    user_model = get_user_model()
    admin_user = user_model.objects.create_user(
        username="admin@example.com",
        email="admin@example.com",
        password="AdminPass123!",
        is_staff=True,
    )
    case = Case.objects.create(
        first_name="Ana",
        last_name="Popescu",
        date_of_birth="1990-01-01",
        email="ana@example.com",
        phone="+40 712 345 678",
        address="Example 1",
        postal_code="010101",
        reservation_number="ABC123",
        gdpr_consent=True,
        gdpr_consent_at=timezone.now(),
        disruption_type="DELAY",
        delay_duration="MORE_THAN_3H",
        airline_motive_mentioned="DONT_KNOW",
        incident_description="Delayed flight.",
        status="ASSIGNED",
    )
    otp, cdg = two_airports
    FlightSegment.objects.create(
        case=case,
        order=0,
        flight_date=timezone.now().date(),
        flight_number="AF1234",
        airline="Air France",
        departure_airport=otp,
        arrival_airport=cdg,
        planned_departure_time=timezone.now(),
        planned_arrival_time=timezone.now() + timezone.timedelta(hours=3),
        is_problem_flight=True,
    )

    client = APIClient()
    client.force_authenticate(user=admin_user)
    resp = client.get("/api/admin/cases/")

    assert resp.status_code == 200, resp.content
    assert resp.json() == [
        {
            "id": str(case.id),
            "case_date": case.created_at.date().isoformat(),
            "flight_number": "AF1234",
            "flight_date": timezone.now().date().isoformat(),
            "status": "ASSIGNED",
        }
    ]


@pytest.mark.django_db
def test_admin_can_delete_case_and_uploaded_files(two_airports, valid_payload, settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    user_model = get_user_model()
    admin_user = user_model.objects.create_user(
        username="admin@example.com",
        email="admin@example.com",
        password="AdminPass123!",
        is_staff=True,
    )
    client = APIClient()

    from cases.compensation.distance import _AirportGapError
    with patch(
        "cases.compensation.distance._airportgap_km",
        side_effect=_AirportGapError("forced fallback in test"),
    ), patch(
        "cases.account_service.transaction.on_commit",
        side_effect=lambda callback: callback(),
    ):
        create_resp = client.post(
            "/api/cases/",
            _make_multipart(valid_payload),
            format="multipart",
        )

    case = Case.objects.get(id=create_resp.json()["id"])
    stored_paths = [Path(default_storage.path(doc.file.name)) for doc in case.documents.all()]

    client.force_authenticate(user=admin_user)
    delete_resp = client.delete(f"/api/admin/cases/{case.id}/")

    assert delete_resp.status_code == 200, delete_resp.content
    assert delete_resp.json()["detail"] == f"Case {case.id} deleted successfully."
    assert Case.objects.filter(id=case.id).exists() is False
    assert FlightSegment.objects.filter(case_id=case.id).exists() is False
    assert CaseDocument.objects.filter(case_id=case.id).exists() is False
    for stored_path in stored_paths:
        assert stored_path.exists() is False


@pytest.mark.django_db
def test_admin_case_endpoints_reject_non_admin(two_airports, valid_payload, settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    user_model = get_user_model()
    user = user_model.objects.create_user(
        username="user@example.com",
        email="user@example.com",
        password="UserPass123!",
    )
    client = APIClient()
    from cases.compensation.distance import _AirportGapError
    with patch(
        "cases.compensation.distance._airportgap_km",
        side_effect=_AirportGapError("forced fallback in test"),
    ), patch(
        "cases.account_service.transaction.on_commit",
        side_effect=lambda callback: callback(),
    ):
        create_resp = client.post(
            "/api/cases/",
            _make_multipart(valid_payload),
            format="multipart",
        )
    case_id = create_resp.json()["id"]

    client.force_authenticate(user=user)

    assert client.get("/api/admin/cases/").status_code == 403
    assert client.delete(f"/api/admin/cases/{case_id}/").status_code == 403


@pytest.mark.django_db
def test_colleague_can_change_password_without_becoming_passenger():
    user_model = get_user_model()
    colleague = user_model.objects.create_user(
        username="colleague@example.com",
        email="colleague@example.com",
        password="ColleaguePass123!",
        first_name="Cole",
        last_name="League",
    )
    UserAccountProfile.objects.create(
        user=colleague,
        assigned_role=AccountRole.COLLEAGUE,
        must_change_password=True,
    )
    client = APIClient()

    resp = client.post(
        "/api/auth/change-password/",
        {
            "email": colleague.email,
            "current_password": "ColleaguePass123!",
            "new_password": "EvenBetterPass123!",
        },
        format="json",
    )

    assert resp.status_code == 200, resp.content
    colleague.refresh_from_db()
    assert colleague.account_profile.must_change_password is False
    assert PassengerAccount.objects.filter(user=colleague).exists() is False

    login_resp = client.post(
        "/api/auth/login/",
        {"email": colleague.email, "password": "EvenBetterPass123!"},
        format="json",
    )
    assert login_resp.status_code == 200, login_resp.content
    assert login_resp.json()["role"] == AccountRole.COLLEAGUE
    assert login_resp.json()["must_change_password"] is False


@pytest.mark.django_db
def test_missing_boarding_pass_rejected(two_airports, valid_payload):
    client = APIClient()
    data = _make_multipart(valid_payload)
    del data["boarding_pass"]
    resp = client.post("/api/cases/", data, format="multipart")
    assert resp.status_code == 400
    assert "boarding_pass" in resp.json()
    assert Case.objects.count() == 0


@pytest.mark.django_db
def test_bad_payload_returns_field_errors(two_airports, valid_payload):
    valid_payload["gdpr_consent"] = False
    client = APIClient()
    resp = client.post("/api/cases/", _make_multipart(valid_payload), format="multipart")
    assert resp.status_code == 400
    assert "gdpr_consent" in resp.json()["payload"]
    assert Case.objects.count() == 0


@pytest.mark.django_db
def test_oversized_file_causes_full_rollback(two_airports, valid_payload, settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    client = APIClient()
    data = _make_multipart(valid_payload)
    huge = SimpleUploadedFile(
        "bp.pdf", b"\x00" * (5 * 1024 * 1024 + 1), content_type="application/pdf"
    )
    data["boarding_pass"] = huge
    resp = client.post("/api/cases/", data, format="multipart")
    assert resp.status_code == 400
    assert Case.objects.count() == 0
    assert CaseDocument.objects.count() == 0


@pytest.mark.django_db
def test_case_created_even_when_compensation_fails(
    two_airports, valid_payload, settings, tmp_path,
):
    settings.MEDIA_ROOT = str(tmp_path)
    client = APIClient()
    with patch(
        "cases.views.compute_for_case",
        side_effect=DistanceUnavailable("simulated failure"),
    ):
        resp = client.post(
            "/api/cases/", _make_multipart(valid_payload), format="multipart",
        )
    assert resp.status_code == 201, resp.content
    body = resp.json()
    assert body["compensation_amount_eur"] is None
    assert body["distance_km"] is None
    assert body["compensation_error"] == (
        "Distance could not be calculated; you can review this case later."
    )

    case = Case.objects.get(id=body["id"])
    assert case.distance_km is None
    assert case.compensation_amount_eur is None
    assert case.compensation_calculated_at is None
    assert case.documents.count() == 2


@pytest.mark.django_db
def test_case_created_even_when_account_email_delivery_fails(
    two_airports, valid_payload, settings, tmp_path,
):
    settings.MEDIA_ROOT = str(tmp_path)
    client = APIClient()
    from cases.compensation.distance import _AirportGapError

    with patch(
        "cases.compensation.distance._airportgap_km",
        side_effect=_AirportGapError("forced fallback in test"),
    ), patch(
        "cases.account_service.send_mail",
        side_effect=ConnectionRefusedError("smtp unavailable"),
    ):
        resp = client.post(
            "/api/cases/", _make_multipart(valid_payload), format="multipart",
        )

    assert resp.status_code == 201, resp.content
    body = resp.json()
    case = Case.objects.get(id=body["id"])
    assert case.email == valid_payload["passenger"]["email"]
    assert case.documents.count() == 2


@pytest.mark.django_db
def test_case_response_carries_compensation_on_success(
    two_airports, valid_payload, settings, tmp_path,
):
    settings.MEDIA_ROOT = str(tmp_path)
    client = APIClient()

    def _fake(case):
        case.distance_km = Decimal("1874.00")
        case.compensation_amount_eur = 400
        case.compensation_calculated_at = timezone.now()

    with patch("cases.views.compute_for_case", side_effect=_fake):
        resp = client.post(
            "/api/cases/", _make_multipart(valid_payload), format="multipart",
        )
    assert resp.status_code == 201, resp.content
    body = resp.json()
    assert body["compensation_amount_eur"] == 400
    assert body["distance_km"] == "1874.00"
    assert body["compensation_error"] is None


@pytest.mark.django_db
def test_missing_disruption_block_rejected(two_airports, valid_payload):
    payload = copy.deepcopy(valid_payload)
    del payload["disruption"]
    client = APIClient()
    resp = client.post("/api/cases/", _make_multipart(payload), format="multipart")
    assert resp.status_code == 400
    assert "disruption" in resp.json()["payload"]
    assert Case.objects.count() == 0


@pytest.mark.django_db
def test_disruption_round_trip_cancellation(
    two_airports, valid_payload, settings, tmp_path,
):
    settings.MEDIA_ROOT = str(tmp_path)
    payload = copy.deepcopy(valid_payload)
    payload["disruption"] = {
        "disruption_type": "CANCELLATION",
        "cancellation_notice": "LESS_THAN_14_DAYS",
        "airline_motive_mentioned": "YES",
        "airline_motive": "WEATHER",
        "incident_description": "Cancelled the morning of.",
    }
    client = APIClient()
    from cases.compensation.distance import _AirportGapError
    with patch(
        "cases.compensation.distance._airportgap_km",
        side_effect=_AirportGapError("forced fallback in test"),
    ):
        resp = client.post("/api/cases/", _make_multipart(payload), format="multipart")
    assert resp.status_code == 201, resp.content
    body = resp.json()
    assert body["disruption"] == {
        "disruption_type": "CANCELLATION",
        "cancellation_notice": "LESS_THAN_14_DAYS",
        "delay_duration": None,
        "denied_boarding_voluntary": None,
        "denied_boarding_reason": None,
        "airline_motive_mentioned": "YES",
        "airline_motive": "WEATHER",
        "incident_description": "Cancelled the morning of.",
    }
    case = Case.objects.get(id=body["id"])
    assert case.disruption_type == "CANCELLATION"
    assert case.cancellation_notice == "LESS_THAN_14_DAYS"
    assert case.airline_motive == "WEATHER"
    assert case.delay_duration is None
    assert case.denied_boarding_voluntary is None


@pytest.mark.django_db
def test_disruption_round_trip_denied_boarding_involuntary(
    two_airports, valid_payload, settings, tmp_path,
):
    settings.MEDIA_ROOT = str(tmp_path)
    payload = copy.deepcopy(valid_payload)
    payload["disruption"] = {
        "disruption_type": "DENIED_BOARDING",
        "denied_boarding_voluntary": "NO",
        "denied_boarding_reason": "OVERBOOKED",
        "incident_description": "Denied at the gate — overbooking.",
    }
    client = APIClient()
    from cases.compensation.distance import _AirportGapError
    with patch(
        "cases.compensation.distance._airportgap_km",
        side_effect=_AirportGapError("forced fallback in test"),
    ):
        resp = client.post("/api/cases/", _make_multipart(payload), format="multipart")
    assert resp.status_code == 201, resp.content
    body = resp.json()
    assert body["disruption"]["denied_boarding_voluntary"] == "NO"
    assert body["disruption"]["denied_boarding_reason"] == "OVERBOOKED"
    assert body["disruption"]["airline_motive_mentioned"] is None
    case = Case.objects.get(id=body["id"])
    assert case.denied_boarding_voluntary is False
    assert case.denied_boarding_reason == "OVERBOOKED"


@pytest.mark.django_db
def test_existing_happy_path_now_persists_disruption(
    two_airports, valid_payload, settings, tmp_path,
):
    """Sanity-check that the shared happy-path fixture writes disruption too."""
    settings.MEDIA_ROOT = str(tmp_path)
    client = APIClient()
    from cases.compensation.distance import _AirportGapError
    with patch(
        "cases.compensation.distance._airportgap_km",
        side_effect=_AirportGapError("forced fallback in test"),
    ):
        resp = client.post("/api/cases/", _make_multipart(valid_payload), format="multipart")
    assert resp.status_code == 201, resp.content
    body = resp.json()
    assert body["disruption"]["disruption_type"] == "DELAY"
    assert body["disruption"]["delay_duration"] == "MORE_THAN_3H"
