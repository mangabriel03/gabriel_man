# CASE_01 — Case Entry Implementation Plan

> **Execution:** Use subagent-driven development to implement this plan task-by-task.

**Goal:** Build the first vertical slice of AirAssist — a public web form that creates a compensation case (`status=NEW`), backed by a Django + DRF API and a React + TS SPA, with airport-catalogue lookup and validated multipart file upload.

**Architecture:** Two-app Django backend (`cases`, `airports`) exposing `POST /api/cases/` (multipart) and `GET /api/airports/`. React SPA built with Vite renders one form with five sections, validates via Zod, submits a single multipart request. Local filesystem storage for uploads; PostgreSQL in prod with SQLite fallback in dev.

**Tech Stack:** Python 3.12+, Django 5.x, Django REST Framework, PostgreSQL 15+ (SQLite dev fallback), pytest / pytest-django / pytest-factoryboy, Vite, React 18, TypeScript, React Hook Form, Zod, CSS Modules, Vitest, React Testing Library.

**Design Spec:** [documentation/spec-driven/specs/2026-07-23-case-01-case-entry-design.md](../specs/2026-07-23-case-01-case-entry-design.md)

---

## Task Ordering

Tasks 1–3 stand up the empty backend project. Tasks 4–8 build backend features. Task 9 seeds the frontend project. Tasks 10–15 build frontend features. Task 16 writes the README and verifies end-to-end. Every backend task before Task 9 can be executed without any frontend context; every frontend task assumes the backend contract from §4 of the spec but does not need backend code to run its unit tests.

---

### Task 1: Repo Scaffolding & Git Hygiene

**Files:**
- Create: `.gitignore`
- Create: `README.md` (stub — full content added in Task 16)
- Create: `backend/` (empty folder placeholder via `.gitkeep`)
- Create: `frontend/` (empty folder placeholder via `.gitkeep`)
- Create: `documentation/spec-driven/plans/.gitkeep` (folder already exists — skip if present)

**Requirements:**
- Ignore Python bytecode, venvs, Django artefacts, node_modules, build outputs, environment files, media uploads, and IDE noise.
- No dependency installation in this task — only file/folder scaffolding.

**Implementation:**

`.gitignore`:

```gitignore
# --- Python ---
__pycache__/
*.py[cod]
*.egg-info/
.venv/
venv/
.pytest_cache/
.mypy_cache/
.ruff_cache/
htmlcov/
.coverage
coverage.xml

# --- Django ---
db.sqlite3
db.sqlite3-journal
backend/media/
backend/staticfiles/
backend/.env
backend/*.log

# --- Node / Vite ---
node_modules/
frontend/dist/
frontend/.vite/
frontend/coverage/
frontend/.env
frontend/.env.local

# --- OS / IDE ---
.DS_Store
Thumbs.db
.idea/
.vscode/*
!.vscode/settings.json
!.vscode/extensions.json
*.swp
```

`README.md` (stub — content expanded in Task 16):

```markdown
# AirAssist

EU 261/2004 flight-compensation claim-management web app.

Setup instructions and architecture notes will be added in Task 16.
```

**Testing:**

No code to test yet.

**Verification:**

```powershell
Get-ChildItem -Force
```

Should list `.gitignore`, `README.md`, `backend/`, `frontend/`, `docs/`, `documentation/`, `.github/`.

---

### Task 2: Backend Project Init (Django + DRF + Settings Split)

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/requirements-dev.txt`
- Create: `backend/.env.example`
- Create: `backend/manage.py`
- Create: `backend/pytest.ini`
- Create: `backend/airassist/__init__.py`
- Create: `backend/airassist/settings/__init__.py`
- Create: `backend/airassist/settings/base.py`
- Create: `backend/airassist/settings/dev.py`
- Create: `backend/airassist/settings/prod.py`
- Create: `backend/airassist/urls.py`
- Create: `backend/airassist/wsgi.py`
- Create: `backend/airassist/asgi.py`

**Requirements:**
- Django project name is `airassist`. Settings split into `base`, `dev`, `prod`.
- Reads `.env` via `python-dotenv`; parses `DATABASE_URL` via `dj-database-url`; empty/absent value → SQLite fallback at `backend/db.sqlite3`.
- DRF installed with defaults for JSON + multipart parsing; `AnonRateThrottle` configured but scope-specific rate set on the view in Task 8.
- `MEDIA_ROOT = <backend>/media`, `MEDIA_URL = "/media/"`.
- Upload limits: `DATA_UPLOAD_MAX_MEMORY_SIZE = 12 * 1024 * 1024`, `FILE_UPLOAD_MAX_MEMORY_SIZE = 6 * 1024 * 1024`.
- Two apps registered but empty for now: `cases`, `airports`. Placeholder `AppConfig`s created in later tasks; for this task register them in `INSTALLED_APPS` **only after** their apps exist. → For Task 2, leave those two lines out; Tasks 3 and 6 will add them.

**Implementation:**

`backend/requirements.txt`:

```
Django>=5.0,<5.2
djangorestframework>=3.15,<4.0
django-cors-headers>=4.3,<5.0
dj-database-url>=2.1
python-dotenv>=1.0
psycopg[binary]>=3.1
requests>=2.31
python-magic-bin==0.4.14; platform_system == "Windows"
python-magic>=0.4.27; platform_system != "Windows"
```

`backend/requirements-dev.txt`:

```
-r requirements.txt
pytest>=8.0
pytest-django>=4.8
pytest-factoryboy>=2.7
factory-boy>=3.3
responses>=0.25
```

`backend/.env.example`:

```
DJANGO_SETTINGS_MODULE=airassist.settings.dev
DJANGO_SECRET_KEY=change-me-in-real-envs
DATABASE_URL=
DJANGO_DEBUG=1
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
AIRPORTGAP_BASE_URL=https://airportgap.com/api
AIRPORTGAP_TOKEN=
```

`backend/manage.py`:

```python
#!/usr/bin/env python
import os
import sys
from pathlib import Path

from dotenv import load_dotenv


def main() -> None:
    load_dotenv(Path(__file__).resolve().parent / ".env")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "airassist.settings.dev")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Activate the venv and install requirements-dev.txt."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
```

`backend/pytest.ini`:

```ini
[pytest]
DJANGO_SETTINGS_MODULE = airassist.settings.dev
python_files = tests.py test_*.py
addopts = -q
```

`backend/airassist/__init__.py`: empty.

`backend/airassist/settings/__init__.py`: empty.

`backend/airassist/settings/base.py`:

```python
"""Base settings shared by dev and prod."""
from __future__ import annotations

import os
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # -> backend/

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "insecure-dev-key")

DEBUG = os.environ.get("DJANGO_DEBUG", "0") == "1"

ALLOWED_HOSTS = [
    h.strip() for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",") if h.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    # Local apps registered in later tasks:
    # "airports",
    # "cases",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "airassist.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "airassist.wsgi.application"

_default_db_url = f"sqlite:///{BASE_DIR / 'db.sqlite3'}"
DATABASES = {
    "default": dj_database_url.parse(
        os.environ.get("DATABASE_URL") or _default_db_url,
        conn_max_age=60,
    )
}

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

DATA_UPLOAD_MAX_MEMORY_SIZE = 12 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 6 * 1024 * 1024

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],  # CSRF-free public API
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",
        "rest_framework.parsers.FormParser",
    ],
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.AnonRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/minute",
        "case_create": "20/hour",
    },
}

CORS_ALLOWED_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]

AIRPORTGAP_BASE_URL = os.environ.get("AIRPORTGAP_BASE_URL", "https://airportgap.com/api")
AIRPORTGAP_TOKEN = os.environ.get("AIRPORTGAP_TOKEN", "")
```

`backend/airassist/settings/dev.py`:

```python
from .base import *  # noqa: F401,F403

DEBUG = True
ALLOWED_HOSTS = ["*"]
```

`backend/airassist/settings/prod.py`:

```python
from .base import *  # noqa: F401,F403

DEBUG = False

if not ALLOWED_HOSTS:  # noqa: F405
    raise RuntimeError("DJANGO_ALLOWED_HOSTS must be set in production.")
```

`backend/airassist/urls.py`:

```python
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path

urlpatterns: list = [
    path("admin/", admin.site.urls),
    # path("api/", include("airports.urls")),  # wired in Task 5
    # path("api/", include("cases.urls")),     # wired in Task 8
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

`backend/airassist/wsgi.py`:

```python
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "airassist.settings.dev")
application = get_wsgi_application()
```

`backend/airassist/asgi.py`:

```python
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "airassist.settings.dev")
application = get_asgi_application()
```

**Testing:**

No behavioural tests yet — this task is verified by Django's `check` command.

**Verification:**

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
Copy-Item .env.example .env
python manage.py check
```

Expected: `System check identified no issues (0 silenced).`

---

### Task 3: Airports App — Model, Admin, Migration

**Files:**
- Create: `backend/airports/__init__.py`
- Create: `backend/airports/apps.py`
- Create: `backend/airports/models.py`
- Create: `backend/airports/admin.py`
- Create: `backend/airports/migrations/__init__.py`
- Modify: `backend/airassist/settings/base.py` — add `"airports"` to `INSTALLED_APPS`.

**Requirements:**
- `Airport` model exactly as specified in §3 of the spec.
- Admin: list display of iata / name / city / country; search on those fields.

**Implementation:**

`backend/airports/__init__.py`: empty.

`backend/airports/apps.py`:

```python
from django.apps import AppConfig


class AirportsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "airports"
```

`backend/airports/models.py`:

```python
from __future__ import annotations

from django.db import models


class Airport(models.Model):
    iata = models.CharField(max_length=3, unique=True, db_index=True)
    icao = models.CharField(max_length=4, unique=True, null=True, blank=True)
    name = models.CharField(max_length=200)
    city = models.CharField(max_length=120)
    country = models.CharField(max_length=120)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["iata"]

    def __str__(self) -> str:
        return f"{self.iata} — {self.name} ({self.city}, {self.country})"
```

`backend/airports/admin.py`:

```python
from django.contrib import admin

from .models import Airport


@admin.register(Airport)
class AirportAdmin(admin.ModelAdmin):
    list_display = ("iata", "icao", "name", "city", "country")
    search_fields = ("iata", "icao", "name", "city", "country")
    ordering = ("iata",)
```

`backend/airports/migrations/__init__.py`: empty (the initial migration is generated by `makemigrations`).

`INSTALLED_APPS` change in `base.py`:

```python
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "airports",
    # "cases",  # added in Task 6
]
```

**Testing:**

No unit tests for a plain model with no custom methods — coverage comes from Task 4 (seed command) and Task 5 (lookup API).

**Verification:**

```powershell
cd backend
python manage.py makemigrations airports
python manage.py migrate
python manage.py shell -c "from airports.models import Airport; print(Airport.objects.count())"
```

Expected output: `0` and a new file `backend/airports/migrations/0001_initial.py` on disk.

---

### Task 4: Airport Sync Management Command + Fixture + Tests

**Files:**
- Create: `backend/airports/management/__init__.py`
- Create: `backend/airports/management/commands/__init__.py`
- Create: `backend/airports/management/commands/sync_airports.py`
- Create: `backend/airports/fixtures/airports_seed.json`
- Create: `backend/airports/tests/__init__.py`
- Create: `backend/airports/tests/test_sync_airports.py`

**Requirements:**
- Command signature: `python manage.py sync_airports [--from-fixture PATH]`.
- Without `--from-fixture`: fetch `GET {AIRPORTGAP_BASE_URL}/airports` (paginated per airportgap.com JSON:API), extract attributes `iata`, `icao`, `name`, `city`, `country`, `latitude`, `longitude`, and upsert via `update_or_create(iata=…)`.
- With `--from-fixture`: load a JSON list of airport dicts (same field names) and upsert. Ship a fixture with **≥5** real airports so tests and offline dev work.
- Idempotent: running twice must not create duplicates.
- Errors: on network failure, print the error and exit with code 2.

**Implementation:**

`backend/airports/management/__init__.py`: empty.
`backend/airports/management/commands/__init__.py`: empty.

`backend/airports/management/commands/sync_airports.py`:

```python
from __future__ import annotations

import json
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from airports.models import Airport


class Command(BaseCommand):
    help = "Seed or refresh the Airport table from airportgap.com or a local fixture."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--from-fixture",
            type=str,
            default=None,
            help="Path to a JSON file with an array of airport objects.",
        )

    def handle(self, *args, **options) -> None:
        fixture_path = options.get("from_fixture")
        if fixture_path:
            records = self._load_fixture(Path(fixture_path))
        else:
            records = self._fetch_from_api()

        created, updated = self._upsert(records)
        self.stdout.write(
            self.style.SUCCESS(f"Airports synced: {created} created, {updated} updated.")
        )

    def _load_fixture(self, path: Path) -> list[dict]:
        if not path.exists():
            raise CommandError(f"Fixture not found: {path}")
        with path.open(encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, list):
            raise CommandError("Fixture must be a JSON array of airport objects.")
        return data

    def _fetch_from_api(self) -> list[dict]:
        base = settings.AIRPORTGAP_BASE_URL.rstrip("/")
        url = f"{base}/airports"
        headers = {}
        if settings.AIRPORTGAP_TOKEN:
            headers["Authorization"] = f"Bearer token={settings.AIRPORTGAP_TOKEN}"

        records: list[dict] = []
        while url:
            try:
                resp = requests.get(url, headers=headers, timeout=15)
                resp.raise_for_status()
            except requests.RequestException as exc:
                self.stderr.write(self.style.ERROR(f"airportgap.com request failed: {exc}"))
                sys.exit(2)
            body = resp.json()
            for item in body.get("data", []):
                attrs = item.get("attributes", {})
                records.append(
                    {
                        "iata": attrs.get("iata"),
                        "icao": attrs.get("icao") or None,
                        "name": attrs.get("name", ""),
                        "city": attrs.get("city", ""),
                        "country": attrs.get("country", ""),
                        "latitude": attrs.get("latitude"),
                        "longitude": attrs.get("longitude"),
                    }
                )
            url = (body.get("links") or {}).get("next")
        return records

    @transaction.atomic
    def _upsert(self, records: Iterable[dict]) -> tuple[int, int]:
        created_count = 0
        updated_count = 0
        for rec in records:
            iata = (rec.get("iata") or "").strip().upper()
            if not iata:
                continue
            try:
                lat = Decimal(str(rec["latitude"]))
                lng = Decimal(str(rec["longitude"]))
            except (InvalidOperation, KeyError, TypeError):
                continue
            defaults = {
                "icao": (rec.get("icao") or None),
                "name": rec.get("name") or "",
                "city": rec.get("city") or "",
                "country": rec.get("country") or "",
                "latitude": lat,
                "longitude": lng,
            }
            _, created = Airport.objects.update_or_create(iata=iata, defaults=defaults)
            if created:
                created_count += 1
            else:
                updated_count += 1
        return created_count, updated_count
```

`backend/airports/fixtures/airports_seed.json`:

```json
[
  {"iata": "OTP", "icao": "LROP", "name": "Henri Coandă International Airport", "city": "Bucharest", "country": "Romania", "latitude": "44.5711", "longitude": "26.0850"},
  {"iata": "CDG", "icao": "LFPG", "name": "Charles de Gaulle Airport", "city": "Paris", "country": "France", "latitude": "49.0097", "longitude": "2.5479"},
  {"iata": "FRA", "icao": "EDDF", "name": "Frankfurt Airport", "city": "Frankfurt", "country": "Germany", "latitude": "50.0379", "longitude": "8.5622"},
  {"iata": "LHR", "icao": "EGLL", "name": "London Heathrow Airport", "city": "London", "country": "United Kingdom", "latitude": "51.4700", "longitude": "-0.4543"},
  {"iata": "AMS", "icao": "EHAM", "name": "Amsterdam Schiphol Airport", "city": "Amsterdam", "country": "Netherlands", "latitude": "52.3105", "longitude": "4.7683"},
  {"iata": "MAD", "icao": "LEMD", "name": "Adolfo Suárez Madrid–Barajas Airport", "city": "Madrid", "country": "Spain", "latitude": "40.4936", "longitude": "-3.5668"}
]
```

`backend/airports/tests/__init__.py`: empty.

`backend/airports/tests/test_sync_airports.py`:

```python
from __future__ import annotations

import json
from io import StringIO
from pathlib import Path

import pytest
import responses
from django.conf import settings
from django.core.management import call_command

from airports.models import Airport


@pytest.fixture
def fixture_path(tmp_path) -> Path:
    data = [
        {"iata": "CDG", "icao": "LFPG", "name": "Charles de Gaulle",
         "city": "Paris", "country": "France",
         "latitude": "49.0097", "longitude": "2.5479"},
        {"iata": "OTP", "icao": "LROP", "name": "Henri Coanda",
         "city": "Bucharest", "country": "Romania",
         "latitude": "44.5711", "longitude": "26.0850"},
    ]
    path = tmp_path / "airports.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


@pytest.mark.django_db
def test_sync_from_fixture_creates_rows(fixture_path: Path) -> None:
    call_command("sync_airports", "--from-fixture", str(fixture_path), stdout=StringIO())
    assert Airport.objects.count() == 2
    cdg = Airport.objects.get(iata="CDG")
    assert cdg.city == "Paris"


@pytest.mark.django_db
def test_sync_from_fixture_is_idempotent(fixture_path: Path) -> None:
    call_command("sync_airports", "--from-fixture", str(fixture_path), stdout=StringIO())
    call_command("sync_airports", "--from-fixture", str(fixture_path), stdout=StringIO())
    assert Airport.objects.count() == 2


@pytest.mark.django_db
@responses.activate
def test_sync_from_api_paginates_and_upserts() -> None:
    base = settings.AIRPORTGAP_BASE_URL.rstrip("/")
    responses.add(
        responses.GET,
        f"{base}/airports",
        json={
            "data": [
                {"id": "CDG", "type": "airport",
                 "attributes": {"iata": "CDG", "icao": "LFPG",
                                "name": "Charles de Gaulle", "city": "Paris",
                                "country": "France",
                                "latitude": "49.0097", "longitude": "2.5479"}}
            ],
            "links": {"next": f"{base}/airports?page=2"},
        },
        status=200,
    )
    responses.add(
        responses.GET,
        f"{base}/airports?page=2",
        json={
            "data": [
                {"id": "OTP", "type": "airport",
                 "attributes": {"iata": "OTP", "icao": "LROP",
                                "name": "Henri Coanda", "city": "Bucharest",
                                "country": "Romania",
                                "latitude": "44.5711", "longitude": "26.0850"}}
            ],
            "links": {"next": None},
        },
        status=200,
    )
    call_command("sync_airports", stdout=StringIO())
    assert Airport.objects.count() == 2
```

**Verification:**

```powershell
cd backend
pytest airports/tests/test_sync_airports.py -q
python manage.py sync_airports --from-fixture airports/fixtures/airports_seed.json
python manage.py shell -c "from airports.models import Airport; print(Airport.objects.count())"
```

Expected: pytest reports 3 passed; final print shows `6`.

---

### Task 5: Airports Lookup API

**Files:**
- Create: `backend/airports/serializers.py`
- Create: `backend/airports/views.py`
- Create: `backend/airports/urls.py`
- Modify: `backend/airassist/urls.py` — enable the `airports` include line.
- Create: `backend/airports/tests/test_lookup_api.py`

**Requirements:**
- `GET /api/airports/?q=<query>&limit=<int>`; `AllowAny`.
- Empty `q` returns `[]`. Non-empty `q`: match `iata iexact` OR `name icontains` OR `city icontains`. Order: exact-IATA-match first, then name asc.
- `limit` default 20, hard-capped at 50.
- Response format matches spec §4 (iata, icao, name, city, country).

**Implementation:**

`backend/airports/serializers.py`:

```python
from rest_framework import serializers

from .models import Airport


class AirportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Airport
        fields = ("iata", "icao", "name", "city", "country")
```

`backend/airports/views.py`:

```python
from __future__ import annotations

from django.db.models import Case, IntegerField, Q, Value, When
from rest_framework import generics

from .models import Airport
from .serializers import AirportSerializer

MAX_LIMIT = 50
DEFAULT_LIMIT = 20


class AirportSearchView(generics.ListAPIView):
    serializer_class = AirportSerializer

    def get_queryset(self):
        q = (self.request.query_params.get("q") or "").strip()
        if not q:
            return Airport.objects.none()

        try:
            limit = int(self.request.query_params.get("limit", DEFAULT_LIMIT))
        except (TypeError, ValueError):
            limit = DEFAULT_LIMIT
        limit = max(1, min(limit, MAX_LIMIT))

        q_upper = q.upper()
        qs = Airport.objects.filter(
            Q(iata__iexact=q) | Q(name__icontains=q) | Q(city__icontains=q)
        )
        qs = qs.annotate(
            is_iata_exact=Case(
                When(iata=q_upper, then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            )
        ).order_by("is_iata_exact", "name")
        return qs[:limit]
```

`backend/airports/urls.py`:

```python
from django.urls import path

from .views import AirportSearchView

urlpatterns = [
    path("airports/", AirportSearchView.as_view(), name="airport-search"),
]
```

`backend/airassist/urls.py` — replace `urlpatterns`:

```python
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns: list = [
    path("admin/", admin.site.urls),
    path("api/", include("airports.urls")),
    # path("api/", include("cases.urls")),  # wired in Task 8
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

`backend/airports/tests/test_lookup_api.py`:

```python
from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from airports.models import Airport


@pytest.fixture
def airports(db):
    Airport.objects.create(iata="CDG", icao="LFPG", name="Charles de Gaulle",
                           city="Paris", country="France",
                           latitude="49.0097", longitude="2.5479")
    Airport.objects.create(iata="OTP", icao="LROP", name="Henri Coanda",
                           city="Bucharest", country="Romania",
                           latitude="44.5711", longitude="26.0850")
    Airport.objects.create(iata="FRA", icao="EDDF", name="Frankfurt Airport",
                           city="Frankfurt", country="Germany",
                           latitude="50.0379", longitude="8.5622")


def test_empty_q_returns_empty_list(airports):
    resp = APIClient().get("/api/airports/")
    assert resp.status_code == 200
    assert resp.json() == []


def test_iata_exact_match_first(airports):
    resp = APIClient().get("/api/airports/?q=CDG")
    body = resp.json()
    assert body[0]["iata"] == "CDG"


def test_city_icontains(airports):
    resp = APIClient().get("/api/airports/?q=Paris")
    iatas = [row["iata"] for row in resp.json()]
    assert "CDG" in iatas


def test_limit_is_capped(airports):
    resp = APIClient().get("/api/airports/?q=a&limit=999")
    assert resp.status_code == 200
    assert len(resp.json()) <= 50
```

**Verification:**

```powershell
cd backend
pytest airports/tests/test_lookup_api.py -q
python manage.py runserver
# In another shell:
curl "http://localhost:8000/api/airports/?q=CDG"
```

Expected: 4 tests pass; curl returns a JSON array containing `"iata": "CDG"`.

---

### Task 6: Cases App — Models, Constraints, Migration, Admin

**Files:**
- Create: `backend/cases/__init__.py`
- Create: `backend/cases/apps.py`
- Create: `backend/cases/models.py`
- Create: `backend/cases/admin.py`
- Create: `backend/cases/migrations/__init__.py`
- Modify: `backend/airassist/settings/base.py` — add `"cases"` to `INSTALLED_APPS`.

**Requirements:**
- Models `Case`, `FlightSegment`, `CaseDocument` exactly as specified in spec §3.
- Postgres-only partial-unique index for one-problem-flight-per-case; skipped on SQLite via a conditional migration (a hand-edited migration step in Task 8's migration or here — we add it here in the initial migration file after autogeneration).
- Admin registrations with inline for segments and documents.

**Implementation:**

`backend/cases/__init__.py`: empty.

`backend/cases/apps.py`:

```python
from django.apps import AppConfig


class CasesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "cases"
```

`backend/cases/models.py`:

```python
from __future__ import annotations

import uuid
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone


PHONE_REGEX = r"^\+?[0-9\s\-()]{7,30}$"


def case_document_upload_to(instance: "CaseDocument", filename: str) -> str:
    ext = Path(filename).suffix.lower().lstrip(".") or "bin"
    return f"cases/{instance.case_id}/{instance.kind}_{uuid.uuid4().hex}.{ext}"


class CaseStatus(models.TextChoices):
    NEW = "NEW", "New"
    VALID = "VALID", "Valid"
    ASSIGNED = "ASSIGNED", "Assigned"
    INVALID = "INVALID", "Invalid"


class Case(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    status = models.CharField(max_length=10, choices=CaseStatus.choices,
                              default=CaseStatus.NEW)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    date_of_birth = models.DateField()
    email = models.EmailField()
    phone = models.CharField(
        max_length=30, validators=[RegexValidator(regex=PHONE_REGEX)]
    )
    address = models.CharField(max_length=200)
    postal_code = models.CharField(max_length=20)

    reservation_number = models.CharField(max_length=30)

    gdpr_consent = models.BooleanField(default=False)
    gdpr_consent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def clean(self) -> None:
        if self.date_of_birth and self.date_of_birth >= timezone.now().date():
            raise ValidationError({"date_of_birth": "Date of birth must be before today."})
        if not self.gdpr_consent:
            raise ValidationError({"gdpr_consent": "GDPR consent is required."})

    def __str__(self) -> str:
        return f"Case {self.id} ({self.status})"


class FlightSegment(models.Model):
    case = models.ForeignKey(Case, related_name="segments", on_delete=models.CASCADE)
    order = models.PositiveSmallIntegerField()
    flight_date = models.DateField()
    flight_number = models.CharField(max_length=10)
    airline = models.CharField(max_length=80)
    departure_airport = models.ForeignKey(
        "airports.Airport", related_name="+", on_delete=models.PROTECT
    )
    arrival_airport = models.ForeignKey(
        "airports.Airport", related_name="+", on_delete=models.PROTECT
    )
    planned_departure_time = models.DateTimeField()
    planned_arrival_time = models.DateTimeField()
    is_problem_flight = models.BooleanField(default=False)

    class Meta:
        ordering = ["case", "order"]
        constraints = [
            models.UniqueConstraint(
                fields=["case", "order"], name="uniq_case_segment_order"
            ),
            models.CheckConstraint(
                check=Q(order__lte=4), name="segment_order_max_4"
            ),
            # Partial unique constraint added by a data-migration in Task 6b/inside
            # the initial migration for Postgres only. Kept out of Meta.constraints
            # so SQLite tests do not blow up.
        ]

    def clean(self) -> None:
        if (
            self.planned_departure_time
            and self.planned_arrival_time
            and self.planned_arrival_time <= self.planned_departure_time
        ):
            raise ValidationError(
                {"planned_arrival_time": "Arrival time must be after departure time."}
            )

    def __str__(self) -> str:
        return f"Segment {self.order} of {self.case_id} — {self.flight_number}"


class DocumentKind(models.TextChoices):
    BOARDING_PASS = "BOARDING_PASS", "Boarding pass"
    ID_DOCUMENT = "ID_DOCUMENT", "ID / Passport"


class CaseDocument(models.Model):
    case = models.ForeignKey(Case, related_name="documents", on_delete=models.CASCADE)
    kind = models.CharField(max_length=20, choices=DocumentKind.choices)
    file = models.FileField(upload_to=case_document_upload_to)
    original_filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=80)
    size_bytes = models.PositiveIntegerField()
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["case", "kind"], name="uniq_case_document_kind"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.kind} for {self.case_id}"
```

`backend/cases/admin.py`:

```python
from django.contrib import admin

from .models import Case, CaseDocument, FlightSegment


class FlightSegmentInline(admin.TabularInline):
    model = FlightSegment
    extra = 0


class CaseDocumentInline(admin.TabularInline):
    model = CaseDocument
    extra = 0
    readonly_fields = ("file", "original_filename", "content_type",
                       "size_bytes", "uploaded_at")


@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    list_display = ("id", "status", "last_name", "email", "created_at")
    list_filter = ("status",)
    search_fields = ("last_name", "email", "reservation_number")
    inlines = [FlightSegmentInline, CaseDocumentInline]
    readonly_fields = ("id", "created_at", "updated_at")
```

`backend/cases/migrations/__init__.py`: empty.

Update `INSTALLED_APPS` in `backend/airassist/settings/base.py`:

```python
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "airports",
    "cases",
]
```

After autogenerating `0001_initial.py` with `python manage.py makemigrations cases`, **edit it** to add a Postgres-only partial-unique index at the bottom of `operations`:

```python
from django.db import connection, migrations, models
from django.db.models import Q


def add_partial_unique_index(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(
        "CREATE UNIQUE INDEX one_problem_flight_per_case "
        "ON cases_flightsegment (case_id) WHERE is_problem_flight;"
    )


def drop_partial_unique_index(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("DROP INDEX IF EXISTS one_problem_flight_per_case;")


class Migration(migrations.Migration):
    # ... generated dependencies & operations above ...

    operations = [
        # ... generated CreateModel operations ...
        migrations.RunPython(add_partial_unique_index, drop_partial_unique_index),
    ]
```

**Testing:**

Model tests are exercised by Tasks 7–8 (serializer + API tests).

**Verification:**

```powershell
cd backend
python manage.py makemigrations cases
# Manually add the RunPython op as shown above.
python manage.py migrate
python manage.py check
```

Expected: `System check identified no issues (0 silenced).` and a migration file exists at `backend/cases/migrations/0001_initial.py`.

---

### Task 7: Cases Validators & Serializers

**Files:**
- Create: `backend/cases/validators.py`
- Create: `backend/cases/serializers.py`
- Create: `backend/cases/tests/__init__.py`
- Create: `backend/cases/tests/conftest.py`
- Create: `backend/cases/tests/factories.py`
- Create: `backend/cases/tests/test_validators.py`
- Create: `backend/cases/tests/test_serializers.py`

**Requirements:**
- File validators enforce spec §4 rules 11–12 (size ≤ 5 MB; content type ∈ {pdf, jpeg, png}) by inspecting both file extension and magic bytes.
- `CaseCreateSerializer` accepts the exact `payload` JSON structure from spec §4 and returns a persisted `Case` on `.save()`; it does **not** save files — the view does that in Task 8 so rollback semantics stay in one place.
- All 13 validation rules from spec §4 covered by tests.

**Implementation:**

`backend/cases/validators.py`:

```python
from __future__ import annotations

from django.core.exceptions import ValidationError

try:
    import magic  # python-magic or python-magic-bin
except ImportError:  # pragma: no cover
    magic = None


MAX_FILE_BYTES = 5 * 1024 * 1024

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
}

ALLOWED_EXTENSIONS = {"pdf", "jpg", "jpeg", "png"}


def _detect_mime_from_magic(chunk: bytes) -> str | None:
    if magic is None:
        return None
    try:
        return magic.from_buffer(chunk, mime=True)
    except Exception:  # pragma: no cover
        return None


def validate_upload(file_obj) -> str:
    """Validate an in-memory or streamed upload; return the detected MIME type.

    Raises DRF-compatible ValidationError on failure.
    """
    if file_obj is None:
        raise ValidationError("File is required.")

    size = getattr(file_obj, "size", None)
    if size is None:
        # Fall back to seek/tell for streams
        pos = file_obj.tell()
        file_obj.seek(0, 2)
        size = file_obj.tell()
        file_obj.seek(pos)

    if size > MAX_FILE_BYTES:
        raise ValidationError("File exceeds 5 MB.")

    name = getattr(file_obj, "name", "") or ""
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError("Unsupported file type; allowed: PDF, JPG, PNG.")

    file_obj.seek(0)
    head = file_obj.read(4096)
    file_obj.seek(0)

    declared = (getattr(file_obj, "content_type", "") or "").lower()
    detected = _detect_mime_from_magic(head)

    # Normalise jpg -> jpeg
    if ext == "jpg":
        ext_mime = "image/jpeg"
    elif ext == "jpeg":
        ext_mime = "image/jpeg"
    elif ext == "png":
        ext_mime = "image/png"
    else:
        ext_mime = "application/pdf"

    if detected and detected not in ALLOWED_MIME_TYPES:
        raise ValidationError("Unsupported file type; allowed: PDF, JPG, PNG.")
    if detected and detected != ext_mime:
        raise ValidationError("File contents do not match its extension.")

    if declared and declared not in ALLOWED_MIME_TYPES:
        raise ValidationError("Unsupported file type; allowed: PDF, JPG, PNG.")

    return detected or ext_mime
```

`backend/cases/serializers.py`:

```python
from __future__ import annotations

import json
from datetime import date

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from airports.models import Airport

from .models import Case, CaseDocument, DocumentKind, FlightSegment


PHONE_REGEX = r"^\+?[0-9\s\-()]{7,30}$"


class PassengerSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=80)
    last_name = serializers.CharField(max_length=80)
    date_of_birth = serializers.DateField()
    email = serializers.EmailField()
    phone = serializers.RegexField(regex=PHONE_REGEX, max_length=30)
    address = serializers.CharField(max_length=200)
    postal_code = serializers.CharField(max_length=20)

    def validate_date_of_birth(self, value: date) -> date:
        if value >= timezone.now().date():
            raise serializers.ValidationError("Date of birth must be before today.")
        return value


class FlightSegmentSerializer(serializers.Serializer):
    order = serializers.IntegerField(min_value=0, max_value=4)
    flight_date = serializers.DateField()
    flight_number = serializers.CharField(max_length=10)
    airline = serializers.CharField(max_length=80)
    departure_airport_iata = serializers.CharField(max_length=3, min_length=3)
    arrival_airport_iata = serializers.CharField(max_length=3, min_length=3)
    planned_departure_time = serializers.DateTimeField()
    planned_arrival_time = serializers.DateTimeField()
    is_problem_flight = serializers.BooleanField()

    def validate(self, attrs):
        if attrs["planned_arrival_time"] <= attrs["planned_departure_time"]:
            raise serializers.ValidationError(
                {"planned_arrival_time": "Arrival time must be after departure time."}
            )
        return attrs


class CaseCreateSerializer(serializers.Serializer):
    passenger = PassengerSerializer()
    reservation_number = serializers.CharField(max_length=30)
    segments = FlightSegmentSerializer(many=True)
    gdpr_consent = serializers.BooleanField()

    def validate_gdpr_consent(self, value: bool) -> bool:
        if not value:
            raise serializers.ValidationError(
                "You must accept the GDPR policy to submit."
            )
        return value

    def validate_segments(self, value: list[dict]) -> list[dict]:
        if not (1 <= len(value) <= 5):
            raise serializers.ValidationError("Between 1 and 5 segments are required.")

        orders = [s["order"] for s in value]
        if len(set(orders)) != len(orders):
            raise serializers.ValidationError("Segment order values must be unique.")

        problems = [s for s in value if s["is_problem_flight"]]
        if len(problems) != 1:
            raise serializers.ValidationError(
                "Exactly one segment must be marked as the problem flight."
            )

        iatas = {s["departure_airport_iata"].upper() for s in value} | {
            s["arrival_airport_iata"].upper() for s in value
        }
        known = set(Airport.objects.filter(iata__in=iatas).values_list("iata", flat=True))
        unknown = iatas - known
        if unknown:
            raise serializers.ValidationError(
                f"Unknown airport code(s): {', '.join(sorted(unknown))}."
            )

        return value

    @transaction.atomic
    def create(self, validated_data: dict) -> Case:
        passenger = validated_data["passenger"]
        segments = validated_data["segments"]

        case = Case.objects.create(
            first_name=passenger["first_name"],
            last_name=passenger["last_name"],
            date_of_birth=passenger["date_of_birth"],
            email=passenger["email"],
            phone=passenger["phone"],
            address=passenger["address"],
            postal_code=passenger["postal_code"],
            reservation_number=validated_data["reservation_number"],
            gdpr_consent=True,
            gdpr_consent_at=timezone.now(),
        )

        airports_by_iata = {
            a.iata: a
            for a in Airport.objects.filter(
                iata__in={s["departure_airport_iata"].upper() for s in segments}
                | {s["arrival_airport_iata"].upper() for s in segments}
            )
        }
        for seg in segments:
            FlightSegment.objects.create(
                case=case,
                order=seg["order"],
                flight_date=seg["flight_date"],
                flight_number=seg["flight_number"],
                airline=seg["airline"],
                departure_airport=airports_by_iata[seg["departure_airport_iata"].upper()],
                arrival_airport=airports_by_iata[seg["arrival_airport_iata"].upper()],
                planned_departure_time=seg["planned_departure_time"],
                planned_arrival_time=seg["planned_arrival_time"],
                is_problem_flight=seg["is_problem_flight"],
            )
        return case


def parse_payload_field(raw: str) -> dict:
    """Parse the multipart 'payload' field, raising DRF ValidationError on bad JSON."""
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError) as exc:
        raise serializers.ValidationError({"payload": f"Invalid JSON: {exc}"})
```

`backend/cases/tests/__init__.py`: empty.

`backend/cases/tests/conftest.py`:

```python
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone as tz

import pytest

from airports.models import Airport


@pytest.fixture
def two_airports(db):
    otp = Airport.objects.create(
        iata="OTP", icao="LROP", name="Henri Coanda", city="Bucharest",
        country="Romania", latitude="44.5711", longitude="26.0850",
    )
    cdg = Airport.objects.create(
        iata="CDG", icao="LFPG", name="Charles de Gaulle", city="Paris",
        country="France", latitude="49.0097", longitude="2.5479",
    )
    return otp, cdg


@pytest.fixture
def valid_payload():
    return {
        "passenger": {
            "first_name": "Ana",
            "last_name": "Popescu",
            "date_of_birth": (date.today() - timedelta(days=365 * 30)).isoformat(),
            "email": "ana@example.com",
            "phone": "+40 712 345 678",
            "address": "Str. Exemplu 1",
            "postal_code": "010101",
        },
        "reservation_number": "ABC123",
        "segments": [
            {
                "order": 0,
                "flight_date": (date.today() + timedelta(days=7)).isoformat(),
                "flight_number": "AF1234",
                "airline": "Air France",
                "departure_airport_iata": "OTP",
                "arrival_airport_iata": "CDG",
                "planned_departure_time": datetime.now(tz.utc).replace(microsecond=0).isoformat(),
                "planned_arrival_time":   (datetime.now(tz.utc).replace(microsecond=0) + timedelta(hours=3)).isoformat(),
                "is_problem_flight": True,
            }
        ],
        "gdpr_consent": True,
    }
```

`backend/cases/tests/factories.py`:

```python
from __future__ import annotations

from datetime import date, timedelta

import factory
from django.utils import timezone

from airports.models import Airport

from cases.models import Case, CaseDocument, DocumentKind, FlightSegment


class AirportFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Airport

    iata = factory.Sequence(lambda n: f"A{n:02d}")
    icao = None
    name = factory.Faker("city")
    city = factory.Faker("city")
    country = factory.Faker("country")
    latitude = "0.000000"
    longitude = "0.000000"


class CaseFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Case

    first_name = "Ana"
    last_name = "Popescu"
    date_of_birth = date.today() - timedelta(days=365 * 25)
    email = "ana@example.com"
    phone = "+40 712 345 678"
    address = "Str. Exemplu 1"
    postal_code = "010101"
    reservation_number = "ABC123"
    gdpr_consent = True
    gdpr_consent_at = factory.LazyFunction(timezone.now)


class FlightSegmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = FlightSegment

    case = factory.SubFactory(CaseFactory)
    order = 0
    flight_date = date.today() + timedelta(days=7)
    flight_number = "AF1234"
    airline = "Air France"
    departure_airport = factory.SubFactory(AirportFactory)
    arrival_airport = factory.SubFactory(AirportFactory)
    planned_departure_time = factory.LazyFunction(timezone.now)
    planned_arrival_time = factory.LazyAttribute(lambda o: o.planned_departure_time + timedelta(hours=3))
    is_problem_flight = True
```

`backend/cases/tests/test_validators.py`:

```python
from __future__ import annotations

import base64
from io import BytesIO

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from cases.validators import MAX_FILE_BYTES, validate_upload


# Minimal valid 1x1 PNG (with IHDR + IDAT + IEND chunks) — libmagic requires
# more than the 8-byte signature to reliably detect image/png.
PNG_MAGIC = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
)
JPEG_MAGIC = b"\xff\xd8\xff\xe0" + b"\x00" * 32
PDF_MAGIC = b"%PDF-1.4\n" + b"\x00" * 32


def _uploaded(name: str, content: bytes, content_type: str) -> SimpleUploadedFile:
    return SimpleUploadedFile(name, content, content_type=content_type)


def test_accepts_valid_pdf():
    validate_upload(_uploaded("id.pdf", PDF_MAGIC, "application/pdf"))


def test_accepts_valid_png():
    validate_upload(_uploaded("bp.png", PNG_MAGIC, "image/png"))


def test_accepts_valid_jpeg():
    validate_upload(_uploaded("bp.jpg", JPEG_MAGIC, "image/jpeg"))


def test_rejects_oversized_file():
    big = b"\x00" * (MAX_FILE_BYTES + 1)
    with pytest.raises(ValidationError):
        validate_upload(_uploaded("id.pdf", big, "application/pdf"))


def test_rejects_bad_extension():
    with pytest.raises(ValidationError):
        validate_upload(_uploaded("id.exe", PDF_MAGIC, "application/pdf"))


def test_rejects_extension_content_mismatch():
    # Extension says PNG but magic bytes are PDF
    with pytest.raises(ValidationError):
        validate_upload(_uploaded("id.png", PDF_MAGIC, "image/png"))
```

`backend/cases/tests/test_serializers.py`:

```python
from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta

import pytest

from cases.models import Case
from cases.serializers import CaseCreateSerializer


@pytest.mark.django_db
def test_happy_path_creates_case(two_airports, valid_payload):
    ser = CaseCreateSerializer(data=valid_payload)
    assert ser.is_valid(), ser.errors
    case = ser.save()
    assert Case.objects.count() == 1
    assert case.status == "NEW"
    assert case.segments.count() == 1


@pytest.mark.django_db
def test_dob_today_rejected(two_airports, valid_payload):
    valid_payload["passenger"]["date_of_birth"] = date.today().isoformat()
    ser = CaseCreateSerializer(data=valid_payload)
    assert not ser.is_valid()
    assert "date_of_birth" in ser.errors["passenger"]


@pytest.mark.django_db
def test_gdpr_false_rejected(two_airports, valid_payload):
    valid_payload["gdpr_consent"] = False
    ser = CaseCreateSerializer(data=valid_payload)
    assert not ser.is_valid()
    assert "gdpr_consent" in ser.errors


@pytest.mark.django_db
def test_zero_problem_flights_rejected(two_airports, valid_payload):
    valid_payload["segments"][0]["is_problem_flight"] = False
    ser = CaseCreateSerializer(data=valid_payload)
    assert not ser.is_valid()
    assert "segments" in ser.errors


@pytest.mark.django_db
def test_two_problem_flights_rejected(two_airports, valid_payload):
    extra = deepcopy(valid_payload["segments"][0])
    extra["order"] = 1
    valid_payload["segments"].append(extra)
    ser = CaseCreateSerializer(data=valid_payload)
    assert not ser.is_valid()
    assert "segments" in ser.errors


@pytest.mark.django_db
def test_unknown_iata_rejected(two_airports, valid_payload):
    valid_payload["segments"][0]["arrival_airport_iata"] = "XYZ"
    ser = CaseCreateSerializer(data=valid_payload)
    assert not ser.is_valid()
    assert "segments" in ser.errors


@pytest.mark.django_db
def test_bad_phone_rejected(two_airports, valid_payload):
    valid_payload["passenger"]["phone"] = "not-a-phone!"
    ser = CaseCreateSerializer(data=valid_payload)
    assert not ser.is_valid()
    assert "phone" in ser.errors["passenger"]


@pytest.mark.django_db
def test_arrival_not_after_departure_rejected(two_airports, valid_payload):
    seg = valid_payload["segments"][0]
    seg["planned_arrival_time"] = seg["planned_departure_time"]
    ser = CaseCreateSerializer(data=valid_payload)
    assert not ser.is_valid()


@pytest.mark.django_db
def test_six_segments_rejected(two_airports, valid_payload):
    base = valid_payload["segments"][0]
    valid_payload["segments"] = [
        {**deepcopy(base), "order": i, "is_problem_flight": (i == 0)}
        for i in range(6)
    ]
    ser = CaseCreateSerializer(data=valid_payload)
    assert not ser.is_valid()
    assert "segments" in ser.errors
```

**Verification:**

```powershell
cd backend
pytest cases/tests/test_validators.py cases/tests/test_serializers.py -q
```

Expected: all tests pass.

---

### Task 8: Cases Create API — View, URL, Rollback, Throttling, Tests

**Files:**
- Create: `backend/cases/views.py`
- Create: `backend/cases/urls.py`
- Modify: `backend/airassist/urls.py` — enable the `cases` include.
- Create: `backend/cases/tests/test_api.py`

**Requirements:**
- `POST /api/cases/` accepts `multipart/form-data`; `AllowAny`; throttle scope `case_create` (20/hour).
- Phase A: parse `payload` JSON, validate everything (payload serializer + both file validators + both files present), return `400` on any failure.
- Phase B: `transaction.atomic()` — create Case + segments (via serializer.save), then create the two `CaseDocument` rows and save their files. On exception inside the atomic block, delete any files that landed on disk and re-raise.
- Response 201: `{ "id", "status", "created_at" }`.
- Both file field names required in the multipart: `boarding_pass`, `id_document`.

**Implementation:**

`backend/cases/views.py`:

```python
from __future__ import annotations

from typing import Iterable

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import status
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from .models import Case, CaseDocument, DocumentKind
from .serializers import CaseCreateSerializer, parse_payload_field
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
        try:
            with transaction.atomic():
                case: Case = payload_ser.save()
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
```

`backend/cases/urls.py`:

```python
from django.urls import path

from .views import CaseCreateView

urlpatterns = [
    path("cases/", CaseCreateView.as_view(), name="case-create"),
]
```

Update `backend/airassist/urls.py` — enable the `cases` include:

```python
urlpatterns: list = [
    path("admin/", admin.site.urls),
    path("api/", include("airports.urls")),
    path("api/", include("cases.urls")),
]
```

`backend/cases/tests/test_api.py`:

```python
from __future__ import annotations

import base64
import json
from io import BytesIO
from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.storage import default_storage
from rest_framework.test import APIClient

from cases.models import Case, CaseDocument


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
    resp = client.post("/api/cases/", _make_multipart(valid_payload), format="multipart")
    assert resp.status_code == 201, resp.content
    body = resp.json()
    assert "id" in body and body["status"] == "NEW"

    case = Case.objects.get(id=body["id"])
    assert case.segments.count() == 1
    assert case.documents.count() == 2
    for doc in case.documents.all():
        assert Path(default_storage.path(doc.file.name)).exists()


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
```

**Verification:**

```powershell
cd backend
pytest cases/tests/test_api.py -q
```

Expected: all tests pass.

Manual smoke:

```powershell
python manage.py runserver
# In another shell:
curl.exe -X POST "http://localhost:8000/api/cases/" `
  -F "payload=@payload.json" `
  -F "boarding_pass=@bp.png" `
  -F "id_document=@id.pdf"
```

---

### Task 9: Frontend Project Init (Vite + React + TS)

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tsconfig.node.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/styles/global.css`
- Create: `frontend/tests/setup.ts`

**Requirements:**
- Vite 5.x, React 18, TypeScript 5.x.
- Dev server on `:5173`; `/api` and `/media` proxied to `http://localhost:8000`.
- Vitest configured for `jsdom` environment; `@testing-library/react` + `@testing-library/jest-dom` set up in `tests/setup.ts`.
- App.tsx renders `<CaseEntryForm />` (component created in Task 14; for this task, use a temporary placeholder `<div>Loading…</div>` — Task 14 will replace it).

**Implementation:**

`frontend/package.json`:

```json
{
  "name": "airassist-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "test": "vitest run",
    "test:watch": "vitest",
    "lint": "tsc --noEmit"
  },
  "dependencies": {
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "react-hook-form": "^7.51.0",
    "@hookform/resolvers": "^3.3.4",
    "zod": "^3.23.0"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "^6.4.0",
    "@testing-library/react": "^15.0.0",
    "@testing-library/user-event": "^14.5.0",
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.0",
    "jsdom": "^24.0.0",
    "typescript": "^5.5.0",
    "vite": "^5.3.0",
    "vitest": "^1.6.0"
  }
}
```

`frontend/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "useDefineForClassFields": true,
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "jsx": "react-jsx",
    "esModuleInterop": true,
    "skipLibCheck": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "types": ["vitest/globals", "@testing-library/jest-dom"]
  },
  "include": ["src", "tests"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

`frontend/tsconfig.node.json`:

```json
{
  "compilerOptions": {
    "composite": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true
  },
  "include": ["vite.config.ts"]
}
```

`frontend/vite.config.ts`:

```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:8000",
      "/media": "http://localhost:8000",
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./tests/setup.ts"],
    css: false,
  },
});
```

`frontend/index.html`:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>AirAssist — File a claim</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

`frontend/src/main.tsx`:

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./styles/global.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
```

`frontend/src/App.tsx` (temporary; replaced in Task 14):

```tsx
export default function App() {
  return <div>Loading…</div>;
}
```

`frontend/src/styles/global.css`:

```css
:root { font-family: system-ui, sans-serif; color-scheme: light; }
body { margin: 0; padding: 0; background: #f7f7fa; }
* { box-sizing: border-box; }
```

`frontend/tests/setup.ts`:

```ts
import "@testing-library/jest-dom/vitest";
```

**Verification:**

```powershell
cd frontend
npm install
npm run lint
npm run test
npm run dev
```

Expected: `npm run lint` and `npm run test` exit 0 (no tests yet is fine); `npm run dev` serves `http://localhost:5173/` and the page shows *Loading…*.

---

### Task 10: Frontend — API Client, Types, and Airport Query

**Files:**
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/api/airports.ts`
- Create: `frontend/src/api/cases.ts`
- Create: `frontend/src/features/case-entry/types.ts`

**Requirements:**
- Thin `fetch` wrapper with JSON + multipart helpers; throws typed errors for 400/413/415/429/5xx.
- `searchAirports(q, signal)` returns `AirportOption[]`.
- `createCase(payload, files)` posts multipart and returns `{ id, status, created_at }` on success or throws `ApiValidationError` (whose `.fieldErrors` is the DRF-shaped tree) on 400.
- Shared TS types match spec §4 payload shape exactly.

**Implementation:**

`frontend/src/features/case-entry/types.ts`:

```ts
export interface PassengerInput {
  first_name: string;
  last_name: string;
  date_of_birth: string;      // YYYY-MM-DD
  email: string;
  phone: string;
  address: string;
  postal_code: string;
}

export interface FlightSegmentInput {
  order: number;
  flight_date: string;                 // YYYY-MM-DD
  flight_number: string;
  airline: string;
  departure_airport_iata: string;
  arrival_airport_iata: string;
  planned_departure_time: string;      // ISO datetime
  planned_arrival_time: string;        // ISO datetime
  is_problem_flight: boolean;
}

export interface CasePayload {
  passenger: PassengerInput;
  reservation_number: string;
  segments: FlightSegmentInput[];
  // Runtime schema (`caseFormSchema`) enforces this must be `true` before submit;
  // typed as `boolean` here to match the RHF form value shape.
  gdpr_consent: boolean;
}

export interface CaseCreateResponse {
  id: string;
  status: "NEW" | "VALID" | "ASSIGNED" | "INVALID";
  created_at: string;
}

export interface AirportOption {
  iata: string;
  icao: string | null;
  name: string;
  city: string;
  country: string;
}
```

`frontend/src/api/client.ts`:

```ts
export class ApiError extends Error {
  readonly status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export class ApiValidationError extends ApiError {
  readonly fieldErrors: Record<string, unknown>;
  constructor(fieldErrors: Record<string, unknown>) {
    super(400, "Validation failed");
    this.fieldErrors = fieldErrors;
  }
}

export class ApiThrottledError extends ApiError {
  constructor() {
    super(429, "Too many attempts. Please wait a moment and try again.");
  }
}

export async function getJson<T>(url: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(url, { ...init, headers: { Accept: "application/json", ...(init?.headers ?? {}) } });
  if (!resp.ok) throw new ApiError(resp.status, `GET ${url} failed with ${resp.status}`);
  return (await resp.json()) as T;
}

export async function postMultipart<T>(url: string, form: FormData): Promise<T> {
  const resp = await fetch(url, { method: "POST", body: form });
  if (resp.status === 429) throw new ApiThrottledError();
  if (resp.status === 400) {
    const errBody = await safeJson(resp);
    throw new ApiValidationError(errBody ?? {});
  }
  if (!resp.ok) throw new ApiError(resp.status, `POST ${url} failed with ${resp.status}`);
  return (await resp.json()) as T;
}

async function safeJson(resp: Response): Promise<Record<string, unknown> | null> {
  try { return (await resp.json()) as Record<string, unknown>; }
  catch { return null; }
}
```

`frontend/src/api/airports.ts`:

```ts
import { getJson } from "./client";
import type { AirportOption } from "../features/case-entry/types";

export function searchAirports(q: string, signal?: AbortSignal): Promise<AirportOption[]> {
  const params = new URLSearchParams({ q });
  return getJson<AirportOption[]>(`/api/airports/?${params.toString()}`, { signal });
}
```

`frontend/src/api/cases.ts`:

```ts
import { postMultipart } from "./client";
import type { CasePayload, CaseCreateResponse } from "../features/case-entry/types";

export function createCase(
  payload: CasePayload,
  files: { boarding_pass: File; id_document: File },
): Promise<CaseCreateResponse> {
  const form = new FormData();
  form.append("payload", JSON.stringify(payload));
  form.append("boarding_pass", files.boarding_pass);
  form.append("id_document", files.id_document);
  return postMultipart<CaseCreateResponse>("/api/cases/", form);
}
```

**Verification:**

```powershell
cd frontend
npm run lint
```

Expected: exit 0 (no type errors).

---

### Task 11: Frontend — Zod Schema

**Files:**
- Create: `frontend/src/features/case-entry/schema.ts`

**Requirements:**
- Mirror every server-side rule (spec §4 rules 1–13) client-side. Same phone regex string as backend.
- Export a single `caseFormSchema` (whole-form Zod schema) plus per-section sub-schemas so section tests can reuse them.
- `boarding_pass` and `id_document` are `File` instances with size/type checks.

**Implementation:**

`frontend/src/features/case-entry/schema.ts`:

```ts
import { z } from "zod";

const PHONE_REGEX = /^\+?[0-9\s\-()]{7,30}$/;
const IATA_REGEX = /^[A-Z]{3}$/;
const MAX_FILE_BYTES = 5 * 1024 * 1024;
const ALLOWED_MIMES = new Set(["application/pdf", "image/jpeg", "image/png"]);

function fileValidator() {
  return z
    .instanceof(File, { message: "File is required." })
    .refine((f) => f.size <= MAX_FILE_BYTES, "File exceeds 5 MB.")
    .refine(
      (f) => ALLOWED_MIMES.has(f.type),
      "Unsupported file type; allowed: PDF, JPG, PNG.",
    );
}

const isoDate = z
  .string()
  .regex(/^\d{4}-\d{2}-\d{2}$/, "Expected date as YYYY-MM-DD.");

const isoDatetime = z
  .string()
  .refine((s) => !Number.isNaN(Date.parse(s)), "Expected a valid datetime.");

export const passengerSchema = z.object({
  first_name: z.string().min(1, "Required."),
  last_name: z.string().min(1, "Required."),
  date_of_birth: isoDate.refine(
    (s) => new Date(s) < new Date(new Date().toDateString()),
    "Date of birth must be before today.",
  ),
  email: z.string().email("Enter a valid email address."),
  phone: z.string().regex(PHONE_REGEX, "Enter a valid phone number."),
  address: z.string().min(1, "Required."),
  postal_code: z.string().min(1, "Required.").max(20),
});

export const segmentSchema = z
  .object({
    order: z.number().int().min(0).max(4),
    flight_date: isoDate,
    flight_number: z.string().min(1, "Required.").max(10),
    airline: z.string().min(1, "Required.").max(80),
    departure_airport_iata: z.string().regex(IATA_REGEX, "Pick an airport."),
    arrival_airport_iata: z.string().regex(IATA_REGEX, "Pick an airport."),
    planned_departure_time: isoDatetime,
    planned_arrival_time: isoDatetime,
    is_problem_flight: z.boolean(),
  })
  .refine(
    (s) => Date.parse(s.planned_arrival_time) > Date.parse(s.planned_departure_time),
    { path: ["planned_arrival_time"], message: "Arrival must be after departure." },
  );

export const caseFormSchema = z
  .object({
    passenger: passengerSchema,
    reservation_number: z.string().min(1, "Required.").max(30),
    segments: z.array(segmentSchema).min(1).max(5),
    gdpr_consent: z
      .boolean()
      .refine((v) => v === true, {
        message: "You must accept the GDPR policy to submit.",
      }),
    boarding_pass: fileValidator(),
    id_document: fileValidator(),
  })
  .refine(
    (v) => v.segments.filter((s) => s.is_problem_flight).length === 1,
    {
      path: ["segments"],
      message: "Exactly one segment must be marked as the problem flight.",
    },
  );

export type CaseFormValues = z.infer<typeof caseFormSchema>;
```

**Verification:**

```powershell
cd frontend
npm run lint
```

Expected: exit 0.

---

### Task 12: Frontend — AirportAutocomplete Component + Test

**Files:**
- Create: `frontend/src/features/case-entry/AirportAutocomplete.tsx`
- Create: `frontend/src/features/case-entry/AirportAutocomplete.module.css`
- Create: `frontend/tests/AirportAutocomplete.test.tsx`

**Requirements:**
- Debounced (250 ms) call to `searchAirports(q)`.
- Renders a dropdown; keyboard-accessible; selecting an option writes the IATA string to the form value.
- Shows "Loading…", "No matches", and error states.
- Test: typing "CDG" (with fetch mocked) results in one option rendered; selecting it calls the passed `onChange` with `"CDG"`.

**Implementation:**

`frontend/src/features/case-entry/AirportAutocomplete.tsx`:

```tsx
import { useEffect, useRef, useState } from "react";

import { searchAirports } from "../../api/airports";
import type { AirportOption } from "./types";
import styles from "./AirportAutocomplete.module.css";

interface Props {
  id: string;
  label: string;
  value: string;                    // IATA
  onChange: (iata: string) => void;
  error?: string;
}

export function AirportAutocomplete({ id, label, value, onChange, error }: Props) {
  const [query, setQuery] = useState(value);
  const [options, setOptions] = useState<AirportOption[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const debounceRef = useRef<number | null>(null);
  const controllerRef = useRef<AbortController | null>(null);

  useEffect(() => setQuery(value), [value]);

  useEffect(() => {
    if (debounceRef.current) window.clearTimeout(debounceRef.current);
    if (!query || query.length < 2) {
      setOptions([]);
      return;
    }
    debounceRef.current = window.setTimeout(() => {
      controllerRef.current?.abort();
      const ctrl = new AbortController();
      controllerRef.current = ctrl;
      setLoading(true);
      setFetchError(null);
      searchAirports(query, ctrl.signal)
        .then((rows) => setOptions(rows))
        .catch((err) => {
          if ((err as { name?: string }).name !== "AbortError") {
            setFetchError("Could not load airports.");
          }
        })
        .finally(() => setLoading(false));
    }, 250);
    return () => {
      if (debounceRef.current) window.clearTimeout(debounceRef.current);
    };
  }, [query]);

  return (
    <div className={styles.wrapper}>
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        type="text"
        value={query}
        onChange={(e) => {
          setQuery(e.target.value.toUpperCase());
          setOpen(true);
        }}
        onBlur={() => setTimeout(() => setOpen(false), 100)}
        onFocus={() => setOpen(true)}
        aria-invalid={!!error}
        aria-describedby={error ? `${id}-err` : undefined}
        autoComplete="off"
      />
      {open && query.length >= 2 && (
        <ul className={styles.dropdown} role="listbox">
          {loading && <li className={styles.hint}>Loading…</li>}
          {!loading && !fetchError && options.length === 0 && (
            <li className={styles.hint}>No matches</li>
          )}
          {fetchError && <li className={styles.hint}>{fetchError}</li>}
          {options.map((opt) => (
            <li
              key={opt.iata}
              role="option"
              aria-selected={value === opt.iata}
              className={styles.option}
              onMouseDown={(e) => {
                e.preventDefault();
                onChange(opt.iata);
                setQuery(opt.iata);
                setOpen(false);
              }}
            >
              <strong>{opt.iata}</strong> — {opt.name} ({opt.city}, {opt.country})
            </li>
          ))}
        </ul>
      )}
      {error && (
        <p id={`${id}-err`} className={styles.error}>
          {error}
        </p>
      )}
    </div>
  );
}
```

`frontend/src/features/case-entry/AirportAutocomplete.module.css`:

```css
.wrapper { position: relative; display: flex; flex-direction: column; gap: 0.25rem; }
.dropdown {
  position: absolute; top: 100%; left: 0; right: 0;
  background: #fff; border: 1px solid #ccc; margin: 0; padding: 0;
  list-style: none; z-index: 10; max-height: 12rem; overflow-y: auto;
}
.option { padding: 0.4rem 0.6rem; cursor: pointer; }
.option:hover { background: #eef; }
.hint { padding: 0.4rem 0.6rem; color: #666; font-style: italic; }
.error { color: #b00020; font-size: 0.875rem; }
```

`frontend/tests/AirportAutocomplete.test.tsx`:

```tsx
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AirportAutocomplete } from "../src/features/case-entry/AirportAutocomplete";

const fetchMock = vi.fn();
beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal("fetch", fetchMock);
});

describe("AirportAutocomplete", () => {
  it("queries the API after debounce and calls onChange on selection", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => [
        { iata: "CDG", icao: "LFPG", name: "Charles de Gaulle",
          city: "Paris", country: "France" },
      ],
    });

    const onChange = vi.fn();
    render(
      <AirportAutocomplete id="dep" label="From" value="" onChange={onChange} />,
    );

    const input = screen.getByLabelText("From");
    await userEvent.type(input, "CDG");

    const option = await waitFor(() => screen.getByRole("option"));
    expect(option).toHaveTextContent("Charles de Gaulle");

    await userEvent.click(option);
    expect(onChange).toHaveBeenCalledWith("CDG");
  });
});
```

**Verification:**

```powershell
cd frontend
npm run test -- tests/AirportAutocomplete.test.tsx
```

Expected: 1 test passes.

---

### Task 13: Frontend — Section Components

**Files:**
- Create: `frontend/src/features/case-entry/sections/FlightItinerarySection.tsx`
- Create: `frontend/src/features/case-entry/sections/ConnectingFlightsSection.tsx`
- Create: `frontend/src/features/case-entry/sections/PassengerDetailsSection.tsx`
- Create: `frontend/src/features/case-entry/sections/DocumentsSection.tsx`
- Create: `frontend/src/features/case-entry/sections/GdprSection.tsx`
- Create: `frontend/src/features/case-entry/sections/sections.module.css`

**Requirements:**
- Each section uses `useFormContext<CaseFormValues>()`; no local form state.
- `FlightItinerarySection` binds all fields of `segments.0`.
- `ConnectingFlightsSection` uses `useFieldArray({ name: "segments" })`; add/remove buttons for indices 1..4; a radio group at the top listing every current segment as the problem-flight marker (setting it clears the flag on other segments).
- `PassengerDetailsSection` binds `passenger.*` + `reservation_number`.
- `DocumentsSection` renders two file inputs writing to `boarding_pass` and `id_document`.
- `GdprSection` renders one checkbox writing to `gdpr_consent`.

**Implementation:**

`frontend/src/features/case-entry/sections/sections.module.css`:

```css
.section { background: #fff; border: 1px solid #ddd; border-radius: 6px; padding: 1rem 1.25rem; margin-bottom: 1rem; }
.section h2 { margin-top: 0; font-size: 1.05rem; }
.grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0.75rem 1rem; }
.field { display: flex; flex-direction: column; gap: 0.25rem; }
.error { color: #b00020; font-size: 0.875rem; }
.actions { display: flex; gap: 0.5rem; margin-top: 0.5rem; }
```

`frontend/src/features/case-entry/sections/PassengerDetailsSection.tsx`:

```tsx
import { useFormContext } from "react-hook-form";

import type { CaseFormValues } from "../schema";
import styles from "./sections.module.css";


export function PassengerDetailsSection() {
  const { register, formState: { errors } } = useFormContext<CaseFormValues>();
  const perr = errors.passenger;
  return (
    <section className={styles.section} aria-labelledby="passenger-heading">
      <h2 id="passenger-heading">Passenger details</h2>
      <div className={styles.grid}>
        <label className={styles.field}>
          First name
          <input {...register("passenger.first_name")} />
          {perr?.first_name && <span className={styles.error}>{perr.first_name.message}</span>}
        </label>
        <label className={styles.field}>
          Last name
          <input {...register("passenger.last_name")} />
          {perr?.last_name && <span className={styles.error}>{perr.last_name.message}</span>}
        </label>
        <label className={styles.field}>
          Date of birth
          <input type="date" {...register("passenger.date_of_birth")} />
          {perr?.date_of_birth && <span className={styles.error}>{perr.date_of_birth.message}</span>}
        </label>
        <label className={styles.field}>
          Email
          <input type="email" {...register("passenger.email")} />
          {perr?.email && <span className={styles.error}>{perr.email.message}</span>}
        </label>
        <label className={styles.field}>
          Phone
          <input type="tel" {...register("passenger.phone")} />
          {perr?.phone && <span className={styles.error}>{perr.phone.message}</span>}
        </label>
        <label className={styles.field}>
          Address
          <input {...register("passenger.address")} />
          {perr?.address && <span className={styles.error}>{perr.address.message}</span>}
        </label>
        <label className={styles.field}>
          Postal code
          <input {...register("passenger.postal_code")} />
          {perr?.postal_code && <span className={styles.error}>{perr.postal_code.message}</span>}
        </label>
        <label className={styles.field}>
          Reservation number
          <input {...register("reservation_number")} />
          {errors.reservation_number && (
            <span className={styles.error}>{errors.reservation_number.message}</span>
          )}
        </label>
      </div>
    </section>
  );
}
```

`frontend/src/features/case-entry/sections/FlightItinerarySection.tsx`:

```tsx
import { Controller, useFormContext } from "react-hook-form";

import { AirportAutocomplete } from "../AirportAutocomplete";
import type { CaseFormValues } from "../schema";
import styles from "./sections.module.css";


export function FlightItinerarySection() {
  const { register, control, formState: { errors } } = useFormContext<CaseFormValues>();
  const segErr = errors.segments?.[0];
  return (
    <section className={styles.section} aria-labelledby="itinerary-heading">
      <h2 id="itinerary-heading">Primary flight itinerary</h2>
      <div className={styles.grid}>
        <label className={styles.field}>
          Flight date
          <input type="date" {...register("segments.0.flight_date")} />
          {segErr?.flight_date && <span className={styles.error}>{segErr.flight_date.message}</span>}
        </label>
        <label className={styles.field}>
          Flight number
          <input {...register("segments.0.flight_number")} />
          {segErr?.flight_number && <span className={styles.error}>{segErr.flight_number.message}</span>}
        </label>
        <label className={styles.field}>
          Airline
          <input {...register("segments.0.airline")} />
          {segErr?.airline && <span className={styles.error}>{segErr.airline.message}</span>}
        </label>
        <Controller
          control={control}
          name="segments.0.departure_airport_iata"
          render={({ field, fieldState }) => (
            <AirportAutocomplete
              id="dep-0"
              label="Departing airport"
              value={field.value}
              onChange={field.onChange}
              error={fieldState.error?.message}
            />
          )}
        />
        <Controller
          control={control}
          name="segments.0.arrival_airport_iata"
          render={({ field, fieldState }) => (
            <AirportAutocomplete
              id="arr-0"
              label="Destination airport"
              value={field.value}
              onChange={field.onChange}
              error={fieldState.error?.message}
            />
          )}
        />
        <label className={styles.field}>
          Planned departure time
          <input type="datetime-local" {...register("segments.0.planned_departure_time")} />
          {segErr?.planned_departure_time && (
            <span className={styles.error}>{segErr.planned_departure_time.message}</span>
          )}
        </label>
        <label className={styles.field}>
          Planned arrival time
          <input type="datetime-local" {...register("segments.0.planned_arrival_time")} />
          {segErr?.planned_arrival_time && (
            <span className={styles.error}>{segErr.planned_arrival_time.message}</span>
          )}
        </label>
      </div>
    </section>
  );
}
```

`frontend/src/features/case-entry/sections/ConnectingFlightsSection.tsx`:

```tsx
import { Controller, useFieldArray, useFormContext } from "react-hook-form";

import { AirportAutocomplete } from "../AirportAutocomplete";
import type { CaseFormValues } from "../schema";
import styles from "./sections.module.css";


export function ConnectingFlightsSection() {
  const { control, register, watch, setValue, formState: { errors } } =
    useFormContext<CaseFormValues>();
  const { fields, append, remove } = useFieldArray({ control, name: "segments" });
  const segments = watch("segments");

  const canAdd = fields.length < 5;

  const problemIndex = segments.findIndex((s) => s.is_problem_flight);

  const setProblem = (idx: number) => {
    segments.forEach((_, i) => {
      setValue(`segments.${i}.is_problem_flight`, i === idx, { shouldValidate: true });
    });
  };

  return (
    <section className={styles.section} aria-labelledby="connecting-heading">
      <h2 id="connecting-heading">Connecting flights &amp; problem-flight marker</h2>

      <fieldset>
        <legend>Which segment is the problem flight?</legend>
        {fields.map((f, i) => (
          <label key={f.id} style={{ display: "block" }}>
            <input
              type="radio"
              name="problem-flight"
              checked={problemIndex === i}
              onChange={() => setProblem(i)}
            />
            {i === 0 ? "Primary segment" : `Connecting ${i}`} — {segments[i]?.flight_number || "?"}
          </label>
        ))}
      </fieldset>
      {errors.segments && typeof errors.segments.message === "string" && (
        <p className={styles.error}>{errors.segments.message}</p>
      )}

      {fields.slice(1).map((f, offset) => {
        const idx = offset + 1;
        return (
          <div key={f.id} className={styles.section}>
            <h3>Connecting flight {idx}</h3>
            <div className={styles.grid}>
              <label className={styles.field}>
                Flight date
                <input type="date" {...register(`segments.${idx}.flight_date`)} />
              </label>
              <label className={styles.field}>
                Flight number
                <input {...register(`segments.${idx}.flight_number`)} />
              </label>
              <label className={styles.field}>
                Airline
                <input {...register(`segments.${idx}.airline`)} />
              </label>
              <Controller
                control={control}
                name={`segments.${idx}.departure_airport_iata`}
                render={({ field, fieldState }) => (
                  <AirportAutocomplete
                    id={`dep-${idx}`}
                    label="From"
                    value={field.value}
                    onChange={field.onChange}
                    error={fieldState.error?.message}
                  />
                )}
              />
              <Controller
                control={control}
                name={`segments.${idx}.arrival_airport_iata`}
                render={({ field, fieldState }) => (
                  <AirportAutocomplete
                    id={`arr-${idx}`}
                    label="To"
                    value={field.value}
                    onChange={field.onChange}
                    error={fieldState.error?.message}
                  />
                )}
              />
              <label className={styles.field}>
                Departure time
                <input type="datetime-local" {...register(`segments.${idx}.planned_departure_time`)} />
              </label>
              <label className={styles.field}>
                Arrival time
                <input type="datetime-local" {...register(`segments.${idx}.planned_arrival_time`)} />
              </label>
            </div>
            <div className={styles.actions}>
              <button type="button" onClick={() => remove(idx)}>Remove</button>
            </div>
          </div>
        );
      })}

      <div className={styles.actions}>
        <button
          type="button"
          disabled={!canAdd}
          onClick={() =>
            append({
              order: fields.length,
              flight_date: "",
              flight_number: "",
              airline: "",
              departure_airport_iata: "",
              arrival_airport_iata: "",
              planned_departure_time: "",
              planned_arrival_time: "",
              is_problem_flight: false,
            })
          }
        >
          Add connecting flight
        </button>
      </div>
    </section>
  );
}
```

`frontend/src/features/case-entry/sections/DocumentsSection.tsx`:

```tsx
import { Controller, useFormContext } from "react-hook-form";

import type { CaseFormValues } from "../schema";
import styles from "./sections.module.css";


function FileField(props: {
  id: string;
  label: string;
  name: "boarding_pass" | "id_document";
}) {
  const { control, formState: { errors } } = useFormContext<CaseFormValues>();
  return (
    <Controller
      control={control}
      name={props.name}
      render={({ field }) => (
        <label className={styles.field} htmlFor={props.id}>
          {props.label}
          <input
            id={props.id}
            type="file"
            accept="application/pdf,image/jpeg,image/png"
            onChange={(e) => field.onChange(e.target.files?.[0] ?? undefined)}
          />
          {errors[props.name] && (
            <span className={styles.error}>{String(errors[props.name]?.message)}</span>
          )}
        </label>
      )}
    />
  );
}


export function DocumentsSection() {
  return (
    <section className={styles.section} aria-labelledby="docs-heading">
      <h2 id="docs-heading">Documents</h2>
      <div className={styles.grid}>
        <FileField id="bp" label="Boarding pass (PDF / JPG / PNG, ≤ 5 MB)" name="boarding_pass" />
        <FileField id="id" label="ID or passport (PDF / JPG / PNG, ≤ 5 MB)" name="id_document" />
      </div>
    </section>
  );
}
```

`frontend/src/features/case-entry/sections/GdprSection.tsx`:

```tsx
import { useFormContext } from "react-hook-form";

import type { CaseFormValues } from "../schema";
import styles from "./sections.module.css";


export function GdprSection() {
  const { register, formState: { errors } } = useFormContext<CaseFormValues>();
  return (
    <section className={styles.section} aria-labelledby="gdpr-heading">
      <h2 id="gdpr-heading">E-mail &amp; GDPR compliance</h2>
      <label>
        <input type="checkbox" {...register("gdpr_consent")} />
        I agree to the GDPR policy and consent to processing of my personal data
        for the purpose of this compensation claim.
      </label>
      {errors.gdpr_consent && (
        <p className={styles.error}>{errors.gdpr_consent.message}</p>
      )}
    </section>
  );
}
```

**Verification:**

```powershell
cd frontend
npm run lint
```

Expected: exit 0. (These sections are exercised by Task 14/15 tests.)

---

### Task 14: Frontend — CaseEntryForm Assembly & Submit

**Files:**
- Create: `frontend/src/features/case-entry/CaseEntryForm.tsx`
- Create: `frontend/src/features/case-entry/CaseEntryForm.module.css`
- Modify: `frontend/src/App.tsx` — render `<CaseEntryForm />`.

**Requirements:**
- Single `useForm` with `zodResolver(caseFormSchema)` and initial values providing exactly one segment (`order: 0`, `is_problem_flight: true`).
- `onSubmit` calls `createCase(payload, files)` where `payload` is the form values minus the two file fields.
- On `ApiValidationError`, walk the DRF error tree and call `setError` per leaf; scroll to the first errored field.
- On `201`, replace the form with a success screen showing `id` and `status`.
- On `ApiThrottledError`, show a top banner. On generic `ApiError`, show a "please try again" banner.
- Submit button is `disabled` while form is invalid or submitting.

**Implementation:**

`frontend/src/features/case-entry/CaseEntryForm.tsx`:

```tsx
import { useState } from "react";
import { FormProvider, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import { createCase } from "../../api/cases";
import { ApiError, ApiThrottledError, ApiValidationError } from "../../api/client";
import type { CaseCreateResponse } from "./types";
import { caseFormSchema, type CaseFormValues } from "./schema";
import { ConnectingFlightsSection } from "./sections/ConnectingFlightsSection";
import { DocumentsSection } from "./sections/DocumentsSection";
import { FlightItinerarySection } from "./sections/FlightItinerarySection";
import { GdprSection } from "./sections/GdprSection";
import { PassengerDetailsSection } from "./sections/PassengerDetailsSection";
import styles from "./CaseEntryForm.module.css";


const emptyValues: CaseFormValues = {
  passenger: {
    first_name: "",
    last_name: "",
    date_of_birth: "",
    email: "",
    phone: "",
    address: "",
    postal_code: "",
  },
  reservation_number: "",
  segments: [
    {
      order: 0,
      flight_date: "",
      flight_number: "",
      airline: "",
      departure_airport_iata: "",
      arrival_airport_iata: "",
      planned_departure_time: "",
      planned_arrival_time: "",
      is_problem_flight: true,
    },
  ],
  gdpr_consent: false,
  // Files are required at submit time; RHF starts with `undefined` and the
  // Zod resolver reports "File is required." until the user picks one.
  boarding_pass: undefined as unknown as File,
  id_document: undefined as unknown as File,
};


function applyServerErrors(
  errors: unknown,
  path: string,
  setError: (name: string, err: { message: string }) => void,
): void {
  if (Array.isArray(errors)) {
    // Leaf: list of message strings for the current field.
    if (errors.length > 0 && typeof errors[0] === "string") {
      setError(path, { message: errors[0] as string });
      return;
    }
    // Per-item errors for `many=True` serializers, e.g. segments[3].
    errors.forEach((item, idx) => {
      applyServerErrors(item, `${path}.${idx}`, setError);
    });
    return;
  }
  if (errors && typeof errors === "object") {
    for (const [key, value] of Object.entries(errors as Record<string, unknown>)) {
      const nextPath = path ? `${path}.${key}` : key;
      // DRF uses "non_field_errors" for cross-field errors — surface on the parent.
      if (key === "non_field_errors") {
        applyServerErrors(value, path, setError);
      } else {
        applyServerErrors(value, nextPath, setError);
      }
    }
  }
}


export function CaseEntryForm() {
  const [banner, setBanner] = useState<string | null>(null);
  const [created, setCreated] = useState<CaseCreateResponse | null>(null);

  const methods = useForm<CaseFormValues>({
    resolver: zodResolver(caseFormSchema),
    defaultValues: emptyValues,
    mode: "onTouched",
  });

  const {
    handleSubmit,
    setError,
    formState: { isValid, isSubmitting },
  } = methods;

  const onSubmit = async (values: CaseFormValues) => {
    setBanner(null);
    const { boarding_pass, id_document, ...payload } = values;
    try {
      const resp = await createCase(payload, { boarding_pass, id_document });
      setCreated(resp);
    } catch (err) {
      if (err instanceof ApiValidationError) {
        applyServerErrors(err.fieldErrors, "", (name, e) =>
          // RHF setError accepts a name string with dotted paths for nested fields.
          setError(name as never, e),
        );
        setBanner("Please fix the highlighted fields.");
      } else if (err instanceof ApiThrottledError) {
        setBanner("Too many attempts. Please wait a minute and try again.");
      } else if (err instanceof ApiError) {
        setBanner("Could not submit. Please try again.");
      } else {
        setBanner("Unexpected error. Please try again.");
      }
    }
  };

  if (created) {
    return (
      <main className={styles.wrapper}>
        <div className={styles.success} role="status">
          <h1>Case created</h1>
          <p>Reference: <code>{created.id}</code></p>
          <p>Status: <strong>{created.status}</strong></p>
        </div>
      </main>
    );
  }

  return (
    <main className={styles.wrapper}>
      <h1>File a compensation claim</h1>
      {banner && <div className={styles.banner} role="alert">{banner}</div>}
      <FormProvider {...methods}>
        <form onSubmit={handleSubmit(onSubmit)} noValidate>
          <FlightItinerarySection />
          <ConnectingFlightsSection />
          <PassengerDetailsSection />
          <DocumentsSection />
          <GdprSection />
          <button
            type="submit"
            disabled={!isValid || isSubmitting}
            className={styles.submit}
          >
            {isSubmitting ? "Submitting…" : "Submit claim"}
          </button>
        </form>
      </FormProvider>
    </main>
  );
}
```

`frontend/src/features/case-entry/CaseEntryForm.module.css`:

```css
.wrapper { max-width: 780px; margin: 2rem auto; padding: 0 1rem; }
.banner {
  background: #fdecea; color: #611a15; border: 1px solid #f5c6c1;
  padding: 0.6rem 0.9rem; border-radius: 4px; margin-bottom: 1rem;
}
.success {
  background: #e7f3e9; color: #1b3a1e; border: 1px solid #b5d8ba;
  padding: 1rem 1.25rem; border-radius: 6px;
}
.submit {
  background: #0d47a1; color: #fff; border: none; border-radius: 4px;
  padding: 0.6rem 1.2rem; font-size: 1rem; cursor: pointer;
}
.submit:disabled { opacity: 0.6; cursor: not-allowed; }
```

`frontend/src/App.tsx`:

```tsx
import { CaseEntryForm } from "./features/case-entry/CaseEntryForm";

export default function App() {
  return <CaseEntryForm />;
}
```

**Verification:**

```powershell
cd frontend
npm run lint
npm run dev
# Open http://localhost:5173/ and verify all five sections render.
```

Expected: `npm run lint` exits 0; browser shows a form with all sections and a disabled Submit button.

---

### Task 15: Frontend — CaseEntryForm Integration Tests

**Files:**
- Create: `frontend/tests/CaseEntryForm.test.tsx`

**Requirements:**
- Test: form renders all five sections.
- Test: Submit is disabled until GDPR checked *and* all required fields valid.
- Test: unchecking GDPR after filling everything else keeps submit disabled and surfaces the GDPR error on blur.
- Test: selecting the problem-flight radio on a newly-added connecting flight clears the flag on the primary segment.
- Test: server 400 response is mapped into per-field messages.

**Implementation:**

`frontend/tests/CaseEntryForm.test.tsx`:

```tsx
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CaseEntryForm } from "../src/features/case-entry/CaseEntryForm";


const fetchMock = vi.fn();
beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal("fetch", fetchMock);
});


function makeSmallFile(name: string, mime: string): File {
  return new File([new Uint8Array([0, 1, 2, 3])], name, { type: mime });
}


describe("CaseEntryForm", () => {
  it("renders all five sections", () => {
    render(<CaseEntryForm />);
    expect(screen.getByRole("heading", { name: /primary flight itinerary/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /connecting flights/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /passenger details/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /documents/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /gdpr/i })).toBeInTheDocument();
  });

  it("keeps submit disabled until form is valid", () => {
    render(<CaseEntryForm />);
    expect(screen.getByRole("button", { name: /submit claim/i })).toBeDisabled();
  });

  it("maps server 400 field errors into inline messages", async () => {
    fetchMock.mockImplementation(async (url: string) => {
      if (String(url).includes("/api/airports/")) {
        return {
          ok: true,
          json: async () => [
            { iata: "OTP", icao: "LROP", name: "Henri Coanda",
              city: "Bucharest", country: "Romania" },
            { iata: "CDG", icao: "LFPG", name: "Charles de Gaulle",
              city: "Paris", country: "France" },
          ],
        };
      }
      // POST /api/cases/ → 400
      return {
        ok: false,
        status: 400,
        json: async () => ({
          payload: { passenger: { email: ["Enter a valid email address."] } },
        }),
      };
    });

    render(<CaseEntryForm />);
    // Fill in valid-looking values so the client-side Zod resolver accepts submit.
    const user = userEvent.setup();
    await user.type(screen.getByLabelText(/first name/i), "Ana");
    await user.type(screen.getByLabelText(/last name/i), "Popescu");
    await user.type(screen.getByLabelText(/date of birth/i), "1990-05-14");
    await user.type(screen.getByLabelText(/^email/i), "invalid-but-passes-client@example.com");
    await user.type(screen.getByLabelText(/phone/i), "+40 712 345 678");
    await user.type(screen.getByLabelText(/address/i), "Str. Exemplu 1");
    await user.type(screen.getByLabelText(/postal code/i), "010101");
    await user.type(screen.getByLabelText(/reservation number/i), "ABC123");
    await user.type(screen.getByLabelText(/^flight date/i), "2026-08-01");
    await user.type(screen.getByLabelText(/^flight number/i), "AF1234");
    await user.type(screen.getByLabelText(/^airline/i), "Air France");
    // Depart / arrive airports via autocomplete
    const dep = screen.getByLabelText(/departing airport/i);
    await user.type(dep, "OT");
    await user.click(await screen.findByRole("option", { name: /OTP/i }));
    const arr = screen.getByLabelText(/destination airport/i);
    await user.type(arr, "CD");
    await user.click(await screen.findByRole("option", { name: /CDG/i }));
    await user.type(screen.getByLabelText(/planned departure time/i), "2026-08-01T09:00");
    await user.type(screen.getByLabelText(/planned arrival time/i), "2026-08-01T11:30");
    await user.upload(
      screen.getByLabelText(/boarding pass/i),
      makeSmallFile("bp.pdf", "application/pdf"),
    );
    await user.upload(
      screen.getByLabelText(/id or passport/i),
      makeSmallFile("id.pdf", "application/pdf"),
    );
    await user.click(screen.getByLabelText(/i agree to the gdpr/i));

    await user.click(screen.getByRole("button", { name: /submit claim/i }));

    await waitFor(() =>
      expect(screen.getByText(/enter a valid email address/i)).toBeInTheDocument(),
    );
  });
});
```

**Verification:**

```powershell
cd frontend
npm run test
```

Expected: all tests pass.

---

### Task 16: README, End-to-End Smoke Verification

**Files:**
- Modify: `README.md` (replaces the stub from Task 1)

**Requirements:**
- Prerequisite list: Python 3.12+, Node 20+, optionally PostgreSQL 15+.
- Backend setup: venv, install requirements-dev, copy `.env.example` → `.env`, migrate, seed airports from fixture, run tests, run server.
- Frontend setup: `npm install`, `npm run test`, `npm run dev`.
- End-to-end manual smoke: fill form → submit → check DB.
- What is NOT implemented yet (out-of-scope list).

**Implementation:**

`README.md`:

````markdown
# AirAssist

EU 261/2004 flight-compensation claim-management web app.

This repository currently implements the CASE_01 vertical slice: a public
case-entry form that creates a `Case` (with `status = NEW`), flight segments,
uploaded documents, and enforces GDPR + full-field validation.

## Prerequisites

- **Python 3.12+**
- **Node.js 20+** (with `npm`)
- **PostgreSQL 15+** — optional; without it, the backend falls back to SQLite
  (`backend/db.sqlite3`).
- **Windows only:** `python-magic-bin` ships the required `libmagic.dll` — no
  extra install needed.

## Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt

Copy-Item .env.example .env
# Optionally set DATABASE_URL=postgres://user:pw@localhost:5432/airassist in .env

python manage.py migrate
python manage.py sync_airports --from-fixture airports/fixtures/airports_seed.json
python manage.py createsuperuser  # optional, for /admin

pytest -q                          # run all backend tests
python manage.py runserver         # http://localhost:8000
```

Key backend endpoints:

- `GET  /api/airports/?q=<query>`  — lookup (max 50 rows)
- `POST /api/cases/`               — multipart submit (see spec §4)
- `/admin/`                        — Django admin

## Frontend

```powershell
cd frontend
npm install
npm run test                       # Vitest + React Testing Library
npm run dev                        # http://localhost:5173 with proxy to :8000
```

The Vite dev server proxies `/api` and `/media` to `http://localhost:8000`, so
you do not need CORS during development. Run **both** servers side by side.

## End-to-end smoke test

1. Start Postgres or leave `DATABASE_URL` empty for the SQLite fallback.
2. Run `python manage.py migrate` and `sync_airports --from-fixture …`.
3. Start `python manage.py runserver` and `npm run dev`.
4. Open <http://localhost:5173/>. Fill the form with valid data; upload a
   small PDF and a small JPG (each ≤ 5 MB).
5. Submit. A success screen appears with a UUID reference and `status = NEW`.
6. Verify in a shell:

   ```powershell
   cd backend
   python manage.py shell -c "from cases.models import Case; print(Case.objects.count())"
   ```

   It should print `1`. Files live under `backend/media/cases/<uuid>/`.

## Explicitly NOT implemented yet

- Distance & compensation calculation (CASE_02)
- Disruption type / motives collection (CASE_03)
- Eligibility rules & `VALID` status transitions (ELIGIBILITY_01/02)
- Friendly case reference number, confirmation email, PDF contract
  (CASE_04, CASE_COMPLETED_*)
- Passenger or employee accounts / login
- Docker/container orchestration
- S3 / cloud file storage
- Internationalisation

## Repository layout

```
backend/         Django project (airassist) with two apps: cases, airports
frontend/        Vite + React + TypeScript SPA
docs/            Source PPTX + XLSX backlog and their extracted XML
documentation/   Design specs and implementation plans
```

## Design & plan documents

- Design spec: [documentation/spec-driven/specs/2026-07-23-case-01-case-entry-design.md](documentation/spec-driven/specs/2026-07-23-case-01-case-entry-design.md)
- Implementation plan: [documentation/spec-driven/plans/2026-07-23-case-01-case-entry-plan.md](documentation/spec-driven/plans/2026-07-23-case-01-case-entry-plan.md)
````

**Verification:**

Run the full stack once end-to-end:

```powershell
# Terminal 1 — backend
cd backend
.\.venv\Scripts\Activate.ps1
python manage.py migrate
python manage.py sync_airports --from-fixture airports/fixtures/airports_seed.json
pytest -q
python manage.py runserver

# Terminal 2 — frontend
cd frontend
npm install
npm run test
npm run dev
```

Then follow the "End-to-end smoke test" steps above. Expected: all tests pass; a case is created; row visible via `python manage.py shell`; files exist under `backend/media/cases/<uuid>/`.

---

## Spec Coverage Matrix (self-review)

| Spec rule / requirement | Covered by task(s) |
|---|---|
| §2 Repo layout — `backend/`, `frontend/`, settings split | Tasks 1, 2, 9 |
| §2 SQLite fallback via empty `DATABASE_URL` | Task 2 (`base.py` `_default_db_url`) |
| §3 `Airport` model | Task 3 |
| §3 `Case` model incl. `status`, GDPR fields | Task 6 |
| §3 `FlightSegment` incl. all constraints | Task 6 (partial-unique in migration) |
| §3 `CaseDocument` incl. unique kind/case | Task 6 |
| §4 `GET /api/airports/` search + limit | Task 5 |
| §4 `POST /api/cases/` multipart contract | Task 8 |
| §4 rule 1 all fields present | Task 7 (serializers `required=True`) |
| §4 rule 2 DoB < today | Tasks 6 (model.clean), 7 (serializer test) |
| §4 rule 3 email | Task 7 |
| §4 rule 4 phone regex | Tasks 6 (model), 7 (serializer) |
| §4 rule 5 postal_code | Task 7 |
| §4 rule 6 1–5 segments, unique order | Task 7 |
| §4 rule 7 exactly one problem flight | Tasks 6 (partial idx), 7 (serializer), 13 (UI radio) |
| §4 rule 8 arrival > departure | Tasks 6 (model.clean), 7 (serializer.validate) |
| §4 rule 9 IATA exists | Task 7 |
| §4 rule 10 GDPR = true | Tasks 6, 7 |
| §4 rules 11–12 file size + type + magic bytes | Task 7 (validators + tests) |
| §4 rule 13 both files present | Task 8 (view-level) |
| §4 transactional rollback + file cleanup | Task 8 |
| §4 throttling `case_create` 20/hour | Tasks 2 (setting), 8 (view scope) |
| §5 Zod schema mirrors §4 | Task 11 |
| §5 Section components | Task 13 |
| §5 AirportAutocomplete | Task 12 |
| §5 Form assembly, submit, error mapping | Task 14 |
| §6 Security notes (magic bytes, filenames, CSRF-free API) | Tasks 2 (settings), 6 (upload_to), 7 (validators), 8 (view) |
| §7 Backend tests | Tasks 4, 5, 7, 8 |
| §7 Frontend tests | Tasks 12, 15 |
| §7 Manual smoke checklist | Task 16 |
| §8 DoD — README with setup, tests pass | Task 16 |

No spec requirement is unmapped.

---

## Post-Plan Handoff

Plan saved to `documentation/spec-driven/plans/2026-07-23-case-01-case-entry-plan.md`. Ready to begin subagent-driven implementation.
