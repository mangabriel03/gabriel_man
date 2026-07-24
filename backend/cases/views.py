from __future__ import annotations

from decimal import Decimal
from typing import Any, Iterable
import json

from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Case as DbCase, CharField, Count, Exists, OuterRef, Value, When
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.permissions import IsAdminUser
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.authentication import SessionAuthentication
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from .compensation import DistanceUnavailable, compute_for_case, preview_from_legs
from .models import AccountRole, Case, CaseDocument, DocumentKind, PassengerAccount, UserAccountProfile
from .serializers import AdminUserCreateSerializer, CaseCreateSerializer, PreviewRequestSerializer, parse_payload_field
from .validators import validate_upload


class CaseCreateThrottle(AnonRateThrottle):
    scope = "case_create"


DOC_FIELDS = (("boarding_pass", DocumentKind.BOARDING_PASS),
              ("id_document",   DocumentKind.ID_DOCUMENT))


class CaseCreateView(APIView):
    parser_classes = [MultiPartParser]
    throttle_classes = [CaseCreateThrottle]

    def post(self, request, *args, **kwargs):
        # --- Phase A: validate everything, write nothing ---
        raw_payload = request.data.get("payload")
        if raw_payload is None:
            raise DRFValidationError({"payload": ["This field is required."]})
        payload_data = parse_payload_field(raw_payload)

        payload_ser = CaseCreateSerializer(data=payload_data)
        payload_valid = payload_ser.is_valid()

        file_errors: dict[str, list[str]] = {}
        detected_mime: dict[str, str] = {}
        for field, _ in DOC_FIELDS:
            file_obj = request.FILES.get(field)
            if file_obj is None:
                file_errors[field] = ["This file is required."]
                continue
            try:
                detected_mime[field] = validate_upload(file_obj)
            except DjangoValidationError as exc:
                file_errors[field] = list(exc.messages)

        if not payload_valid or file_errors:
            errors: dict = {}
            if not payload_valid:
                errors["payload"] = payload_ser.errors
            errors.update(file_errors)
            raise DRFValidationError(errors)

        # --- Phase B: persist inside a transaction with file-rollback ---
        written_paths: list[str] = []
        compensation_error: str | None = None
        try:
            with transaction.atomic():
                case: Case = payload_ser.save()

                # Compensation calc: never blocks case creation. A
                # DistanceUnavailable leaves the three fields NULL and surfaces
                # a soft error on the response; any other exception uses the
                # existing rollback path below.
                try:
                    compute_for_case(case)
                    case.save(update_fields=[
                        "distance_km",
                        "compensation_amount_eur",
                        "compensation_calculated_at",
                    ])
                except DistanceUnavailable:
                    compensation_error = (
                        "Distance could not be calculated; "
                        "you can review this case later."
                    )

                for field, kind in DOC_FIELDS:
                    file_obj = request.FILES[field]
                    doc = CaseDocument(
                        case=case,
                        kind=kind,
                        original_filename=file_obj.name,
                        content_type=detected_mime[field],
                        size_bytes=file_obj.size,
                    )
                    # Save file first (records path on the instance), then row.
                    doc.file.save(file_obj.name, file_obj, save=False)
                    written_paths.append(doc.file.name)
                    doc.save()
        except Exception:
            _cleanup_files(written_paths)
            raise

        return Response(
            {
                "id": str(case.id),
                "status": case.status,
                "created_at": case.created_at.isoformat(),
                "account_email": case.email,
                "password_change_required": True,
                "distance_km": (
                    str(case.distance_km) if case.distance_km is not None else None
                ),
                "compensation_amount_eur": case.compensation_amount_eur,
                "compensation_error": compensation_error,
                "disruption": _serialize_disruption(case),
            },
            status=status.HTTP_201_CREATED,
        )


def _cleanup_files(paths: Iterable[str]) -> None:
    from django.core.files.storage import default_storage
    for p in paths:
        try:
            if default_storage.exists(p):
                default_storage.delete(p)
        except Exception:  # pragma: no cover
            pass


def _serialize_disruption(case: Case) -> dict:
    return {
        "disruption_type": case.disruption_type,
        "cancellation_notice": case.cancellation_notice,
        "delay_duration": case.delay_duration,
        "denied_boarding_voluntary": (
            None if case.denied_boarding_voluntary is None
            else ("YES" if case.denied_boarding_voluntary else "NO")
        ),
        "denied_boarding_reason": case.denied_boarding_reason,
        "airline_motive_mentioned": case.airline_motive_mentioned,
        "airline_motive": case.airline_motive,
        "incident_description": case.incident_description,
    }


class CompensationPreviewThrottle(AnonRateThrottle):
    scope = "compensation_preview"


def _decimals_to_str(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {k: _decimals_to_str(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_decimals_to_str(v) for v in value]
    return value


class CompensationPreviewView(APIView):
    parser_classes = [JSONParser]
    throttle_classes = [CompensationPreviewThrottle]

    def post(self, request, *args, **kwargs):
        serializer = PreviewRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            body = preview_from_legs(serializer.validated_data["legs"])
        except DistanceUnavailable as exc:
            payload = exc.payload if exc.payload is not None else {
                "detail": str(exc),
                "legs": [],
            }
            return Response(
                _decimals_to_str(payload),
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        return Response(_decimals_to_str(body), status=status.HTTP_200_OK)


def _json_body(request) -> dict:
    try:
        return json.loads(request.body or b"{}")
    except json.JSONDecodeError as exc:
        raise DRFValidationError({"detail": f"Invalid JSON: {exc}"})


def _get_authenticated_user(request):
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        return user
    return None


def _role_for_user(*, is_staff: bool, has_passenger_account: bool, has_cases: bool) -> str:
    if is_staff:
        return AccountRole.SYSTEM_ADMIN
    if has_passenger_account or has_cases:
        return AccountRole.PASSENGER
    return AccountRole.COLLEAGUE


def _must_change_password_for_user(user) -> bool:
    profile = getattr(user, "account_profile", None)
    if profile is not None:
        return profile.must_change_password

    account = getattr(user, "passenger_account", None)
    if account is not None:
        return account.must_change_password
    return False


class LoginView(APIView):
    authentication_classes: list = []
    permission_classes: list = []
    throttle_classes = [AnonRateThrottle]

    def post(self, request, *args, **kwargs):
        payload = _json_body(request)
        email = str(payload.get("email", "")).strip().lower()
        password = str(payload.get("password", ""))

        if not email or not password:
            raise DRFValidationError({
                "email": ["Email is required."],
                "password": ["Password is required."],
            })

        user = authenticate(request=request._request, username=email, password=password)
        if user is None:
            return JsonResponse(
                {"detail": "Invalid email or password."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        login(request._request, user)
        has_cases = user.cases.exists()
        account = PassengerAccount.objects.filter(user=user).first()
        role = _role_for_user(
            is_staff=user.is_staff,
            has_passenger_account=account is not None,
            has_cases=has_cases,
        )

        must_change_password = _must_change_password_for_user(user)
        if role == AccountRole.PASSENGER:
            if account is None:
                account = PassengerAccount.objects.create(user=user)
            if not must_change_password:
                must_change_password = account.must_change_password

        return JsonResponse(
            {
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "role": role,
                "must_change_password": must_change_password,
            },
            status=status.HTTP_200_OK,
        )


class AdminUserListView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAdminUser]

    def get(self, request, *args, **kwargs):
        user_model = get_user_model()
        passenger_accounts = PassengerAccount.objects.filter(user_id=OuterRef("pk"))
        account_profiles = UserAccountProfile.objects.filter(user_id=OuterRef("pk"))
        users = (
            user_model.objects
            .annotate(
                assigned_case_count=Count("cases", distinct=True),
                has_passenger_account=Exists(passenger_accounts),
                has_account_profile=Exists(account_profiles),
            )
            .annotate(
                role=DbCase(
                    When(is_staff=True, then=Value(AccountRole.SYSTEM_ADMIN)),
                    When(has_passenger_account=True, then=Value(AccountRole.PASSENGER)),
                    When(assigned_case_count__gt=0, then=Value(AccountRole.PASSENGER)),
                    default=Value(AccountRole.COLLEAGUE),
                    output_field=CharField(),
                )
            )
            .order_by("first_name", "last_name", "email", "id")
        )
        payload = [
            {
                "id": user.id,
                "name": f"{user.first_name} {user.last_name}".strip(),
                "email": user.email,
                "role": user.role,
                "assigned_case_count": user.assigned_case_count,
            }
            for user in users
        ]
        return Response(payload, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        serializer = AdminUserCreateSerializer(data=_json_body(request))
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {
                "id": user.id,
                "name": f"{user.first_name} {user.last_name}".strip(),
                "email": user.email,
                "role": AccountRole.COLLEAGUE,
                "assigned_case_count": 0,
                "detail": f"Account created for {user.email}. The temporary password was emailed to the colleague.",
            },
            status=status.HTTP_201_CREATED,
        )


class AdminNavigationView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAdminUser]

    def get(self, request, *args, **kwargs):
        return Response(
            {
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
            },
            status=status.HTTP_200_OK,
        )


class AdminCaseListView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAdminUser]

    def get(self, request, *args, **kwargs):
        cases = (
            Case.objects
            .prefetch_related("segments")
            .order_by("-created_at", "id")
        )
        payload = [
            {
                "id": str(case.id),
                "case_date": case.created_at.date().isoformat(),
                "flight_number": _problem_segment(case).flight_number if _problem_segment(case) else None,
                "flight_date": _problem_segment(case).flight_date.isoformat() if _problem_segment(case) else None,
                "status": case.status,
            }
            for case in cases
        ]
        return Response(payload, status=status.HTTP_200_OK)


class AdminCaseDetailView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAdminUser]

    def delete(self, request, case_id, *args, **kwargs):
        case = get_object_or_404(Case, pk=case_id)
        case.delete()
        return Response(
            {"detail": f"Case {case_id} deleted successfully."},
            status=status.HTTP_200_OK,
        )


def _problem_segment(case: Case):
    for segment in case.segments.all():
        if segment.is_problem_flight:
            return segment
    return None


class LogoutView(APIView):
    authentication_classes: list = []
    permission_classes: list = []

    def post(self, request, *args, **kwargs):
        logout(request._request)
        return JsonResponse({}, status=status.HTTP_204_NO_CONTENT)


class ChangePasswordView(APIView):
    authentication_classes: list = []
    permission_classes: list = []

    def post(self, request, *args, **kwargs):
        payload = _json_body(request)
        email = str(payload.get("email", "")).strip().lower()
        current_password = str(payload.get("current_password", ""))
        new_password = str(payload.get("new_password", ""))
        user = _get_authenticated_user(request._request)

        errors: dict[str, list[str]] = {}
        if user is None and not email:
            errors["email"] = ["Email is required."]
        if not current_password:
            errors["current_password"] = ["Current password is required."]
        if not new_password:
            errors["new_password"] = ["New password is required."]
        elif len(new_password) < 12:
            errors["new_password"] = ["New password must be at least 12 characters."]
        if errors:
            raise DRFValidationError(errors)

        if user is None:
            user = authenticate(
                request=request._request,
                username=email,
                password=current_password,
            )
            if user is None:
                return JsonResponse(
                    {"detail": "Authentication required."},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
        elif not user.check_password(current_password):
            raise DRFValidationError({"current_password": ["Current password is incorrect."]})

        user.set_password(new_password)
        user.save(update_fields=["password"])
        profile, _ = UserAccountProfile.objects.get_or_create(
            user=user,
            defaults={"assigned_role": _role_for_user(
                is_staff=user.is_staff,
                has_passenger_account=hasattr(user, "passenger_account"),
                has_cases=user.cases.exists(),
            )},
        )
        profile.must_change_password = False
        profile.save(update_fields=["must_change_password", "updated_at"])
        has_passenger_account = hasattr(user, "passenger_account")
        if has_passenger_account or user.cases.exists():
            account, _ = PassengerAccount.objects.get_or_create(user=user)
            account.must_change_password = False
            account.save(update_fields=["must_change_password", "updated_at"])
        update_session_auth_hash(request._request, user)
        return JsonResponse({"must_change_password": False}, status=status.HTTP_200_OK)
