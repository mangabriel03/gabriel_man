# CASE_01 — Case Entry: Design Spec

**Project:** AirAssist (EU 261/2004 flight-compensation claim management)
**Story:** CASE_01 — Case Entry (Epic: *Case Register*, Priority 1)
**Date:** 2026-07-23
**Status:** Approved for planning

---

## 1. Purpose & Scope

Deliver the very first vertical slice of AirAssist: a **public web form** that a passenger fills out to create a new compensation case. This slice also stands up the minimum repository skeleton (Django backend, React frontend, Postgres/SQLite config, dev tooling) needed to support this and every subsequent story.

### In scope (CASE_01)

Form parts implemented: **(1) flight itinerary, (4) e-mail & GDPR compliance, (5) flight details, (6) passenger details**.

- Publicly accessible form (no login).
- Case creation API that **persists** a `Case` row with `status = NEW` inside a single atomic transaction, including all flight segments and both uploaded documents.
- Airport catalogue seeded locally from `airportgap.com`; lookup served from Postgres.
- Up to 4 connecting flights beyond the primary segment; exactly one segment must be marked as the "problem flight".
- File upload for Boarding Pass and ID/Passport: PDF / JPEG / PNG, ≤ 5 MB each.
- Mandatory GDPR consent checkbox.
- All fields mandatory, validated client-side (Zod) and server-side (DRF); validation rules mirror each other.
- Repo scaffolding: `backend/` (Django + DRF), `frontend/` (Vite + React + TS), Postgres in prod, SQLite fallback in dev, `.env` config, README with setup steps.
- Automated tests: pytest (backend) + Vitest/React Testing Library (frontend).

### Explicitly out of scope

Deferred to their respective stories — this slice **must not** implement even stubs of:

- Distance & compensation calculation → CASE_02
- Disruption type / motives collection (form parts 2 & 3) → CASE_03
- Eligibility rules & `VALID` status transition → ELIGIBILITY_01 / ELIGIBILITY_02
- Displaying a friendly case reference number, confirmation email, PDF contract → CASE_04 / CASE_COMPLETED_01 / CASE_COMPLETED_02
- Passenger accounts / login → PASSENGER_* stories
- Employee workflows, colleague assignment, `ASSIGNED` / `INVALID` transitions → EMPLOYEE_* stories
- Docker / container orchestration
- Auth beyond Django's built-in `auth` app
- S3 / cloud file storage
- Internationalisation (English only)

---

## 2. Architecture Overview

### Runtime topology (dev)

- Postgres on `localhost:5432` in the target dev setup; **SQLite fallback** is supported via `DJANGO_SETTINGS_MODULE=airassist.settings.dev` and an empty/absent `DATABASE_URL`, so a developer can clone + run without installing Postgres.
- `python manage.py runserver` on `:8000` serves `/api/*` and `/media/*`.
- `npm run dev` on `:5173` serves the SPA; Vite dev-proxy forwards `/api` and `/media` → `:8000`. No CORS needed in dev.

### Stack

| Layer | Choice |
|---|---|
| Backend framework | Django 5.x + Django REST Framework |
| Language | Python 3.12+ |
| Database (prod) | PostgreSQL 15+ |
| Database (dev fallback) | SQLite (bundled with Python) |
| File storage | Local filesystem via Django `FileSystemStorage`, `MEDIA_ROOT = backend/media/` |
| Frontend build | Vite |
| Frontend framework | React 18 + TypeScript |
| Forms & validation | React Hook Form + Zod |
| Styling | CSS Modules (no UI library) |
| Backend tests | pytest, pytest-django, pytest-factoryboy |
| Frontend tests | Vitest + React Testing Library |
| Env config | `python-dotenv` + `dj-database-url` |

### Repo layout

```
FirstAiTraining/
├── backend/
│   ├── manage.py
│   ├── pyproject.toml
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── .env.example
│   ├── pytest.ini
│   ├── airassist/                  # Django project package
│   │   ├── __init__.py
│   │   ├── settings/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── dev.py              # SQLite fallback OR local Postgres via DATABASE_URL
│   │   │   └── prod.py             # Postgres via DATABASE_URL
│   │   ├── urls.py
│   │   ├── wsgi.py
│   │   └── asgi.py
│   ├── cases/                      # Django app
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   ├── models.py               # Case, FlightSegment, CaseDocument
│   │   ├── serializers.py          # nested payload serializer + file fields
│   │   ├── validators.py           # phone regex, file size/type, DoB<today, problem-flight
│   │   ├── views.py                # CaseCreateView (POST /api/cases/)
│   │   ├── urls.py
│   │   ├── admin.py
│   │   ├── migrations/
│   │   └── tests/
│   │       ├── conftest.py
│   │       ├── factories.py
│   │       ├── test_serializers.py
│   │       ├── test_validators.py
│   │       └── test_api.py
│   ├── airports/                   # Django app
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   ├── models.py               # Airport
│   │   ├── serializers.py
│   │   ├── views.py                # GET /api/airports/
│   │   ├── urls.py
│   │   ├── admin.py
│   │   ├── management/commands/sync_airports.py
│   │   ├── migrations/
│   │   └── tests/
│   │       ├── test_sync_airports.py
│   │       └── test_lookup_api.py
│   └── media/                      # gitignored; MEDIA_ROOT
│
├── frontend/
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts              # dev proxy /api & /media -> :8000
│   ├── index.html
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── api/
│   │   │   ├── client.ts
│   │   │   ├── cases.ts
│   │   │   └── airports.ts
│   │   ├── features/case-entry/
│   │   │   ├── CaseEntryForm.tsx
│   │   │   ├── schema.ts
│   │   │   ├── types.ts
│   │   │   ├── AirportAutocomplete.tsx
│   │   │   └── sections/
│   │   │       ├── FlightItinerarySection.tsx
│   │   │       ├── ConnectingFlightsSection.tsx
│   │   │       ├── PassengerDetailsSection.tsx
│   │   │       ├── DocumentsSection.tsx
│   │   │       └── GdprSection.tsx
│   │   └── styles/
│   └── tests/
│       ├── setup.ts
│       ├── CaseEntryForm.test.tsx
│       ├── AirportAutocomplete.test.tsx
│       └── sections/
│
├── docs/                            # existing (backlog + PPTX)
├── documentation/
│   └── spec-driven/
│       ├── specs/2026-07-23-case-01-case-entry-design.md   # this file
│       └── plans/                                           # created in Phase 2
├── .gitignore
└── README.md                        # setup + run instructions for both apps
```

### Environment variables

`backend/.env` (documented in `backend/.env.example`):

```
DJANGO_SETTINGS_MODULE=airassist.settings.dev
DJANGO_SECRET_KEY=change-me
DATABASE_URL=                        # empty → SQLite fallback; postgres://user:pw@localhost/airassist otherwise
DJANGO_DEBUG=1
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
AIRPORTGAP_BASE_URL=https://airportgap.com/api
AIRPORTGAP_TOKEN=                    # optional; used only by sync_airports if the endpoint requires it
```

---

## 3. Data Model (Django ORM → Postgres)

### `airports.Airport`

Seeded once by the `sync_airports` management command.

| field | type | notes |
|---|---|---|
| `id` | BigAutoField (PK) | |
| `iata` | CharField(3, unique=True, db_index=True) | e.g. `CDG` |
| `icao` | CharField(4, unique=True, null=True, blank=True) | e.g. `LFPG` |
| `name` | CharField(200) | |
| `city` | CharField(120) | |
| `country` | CharField(120) | |
| `latitude` | DecimalField(9, 6) | reserved for CASE_02 |
| `longitude` | DecimalField(9, 6) | reserved for CASE_02 |
| `created_at` | DateTimeField(auto_now_add=True) | |
| `updated_at` | DateTimeField(auto_now=True) | |

### `cases.Case`

| field | type | notes |
|---|---|---|
| `id` | UUIDField (PK, default=uuid4) | non-enumerable URLs |
| `status` | CharField(choices=`NEW`/`VALID`/`ASSIGNED`/`INVALID`, default=`NEW`) | only `NEW` set in this story |
| `created_at` | DateTimeField(auto_now_add=True) | |
| `updated_at` | DateTimeField(auto_now=True) | |
| `first_name` | CharField(80) | |
| `last_name` | CharField(80) | |
| `date_of_birth` | DateField | validator: `< today` |
| `email` | EmailField | Django `EmailValidator` |
| `phone` | CharField(30) | regex `^\+?[0-9\s\-()]{7,30}$` |
| `address` | CharField(200) | |
| `postal_code` | CharField(20) | non-empty |
| `reservation_number` | CharField(30) | |
| `gdpr_consent` | BooleanField | must be `True` to persist |
| `gdpr_consent_at` | DateTimeField(null=True, blank=True) | set server-side on submit |

Model-level `clean()` rejects `gdpr_consent=False`.

### `cases.FlightSegment`

1 to 5 rows per Case.

| field | type | notes |
|---|---|---|
| `id` | BigAutoField (PK) | |
| `case` | FK → `Case`, related_name=`segments`, on_delete=CASCADE | |
| `order` | PositiveSmallIntegerField | 0 = primary segment; 1..4 = connecting |
| `flight_date` | DateField | |
| `flight_number` | CharField(10) | |
| `airline` | CharField(80) | |
| `departure_airport` | FK → `Airport`, on_delete=PROTECT | |
| `arrival_airport` | FK → `Airport`, on_delete=PROTECT | |
| `planned_departure_time` | DateTimeField | |
| `planned_arrival_time` | DateTimeField | model validator: `> planned_departure_time` |
| `is_problem_flight` | BooleanField(default=False) | |

Constraints (`Meta.constraints`):

- `UniqueConstraint(fields=['case', 'order'], name='uniq_case_segment_order')`
- `UniqueConstraint(fields=['case'], condition=Q(is_problem_flight=True), name='one_problem_flight_per_case')` — Postgres partial-unique index (skipped in SQLite tests via a migration guard; serializer still enforces the rule in-process).
- `CheckConstraint(check=Q(order__lte=4), name='segment_order_max_4')`

### `cases.CaseDocument`

Exactly 2 rows per Case (one `BOARDING_PASS`, one `ID_DOCUMENT`).

| field | type | notes |
|---|---|---|
| `id` | BigAutoField (PK) | |
| `case` | FK → `Case`, related_name=`documents`, on_delete=CASCADE | |
| `kind` | CharField(choices=`BOARDING_PASS`/`ID_DOCUMENT`) | |
| `file` | FileField(upload_to=`cases/<case_id>/`) | |
| `original_filename` | CharField(255) | |
| `content_type` | CharField(80) | one of `application/pdf`, `image/jpeg`, `image/png` |
| `size_bytes` | PositiveIntegerField | |
| `uploaded_at` | DateTimeField(auto_now_add=True) | |

Constraint: `UniqueConstraint(fields=['case', 'kind'], name='uniq_case_document_kind')`.

Stored path format: `cases/<case_uuid>/<kind>_<uuid4>.<ext>` (original filename kept only in the DB column; on-disk names are sanitised).

---

## 4. API Contract

### `GET /api/airports/`

- Query params: `q` (string, optional), `limit` (int, optional, default 20, max 50).
- Behaviour: if `q` is empty, returns `[]`. Otherwise matches `iata` (exact, case-insensitive) OR `name` / `city` (icontains). Ordered by exact-IATA-match first, then name asc.
- `AllowAny`. Cached in-process for the process lifetime (Airport table is static-ish).

**Response 200** — `application/json`:

```json
[
  {
    "iata": "CDG",
    "icao": "LFPG",
    "name": "Charles de Gaulle",
    "city": "Paris",
    "country": "France"
  }
]
```

### `POST /api/cases/`

- Content type: `multipart/form-data`. `AllowAny`.
- Multipart fields:
  - `payload` — a **JSON string** carrying passenger, segments, reservation_number, gdpr_consent.
  - `boarding_pass` — file.
  - `id_document` — file.

`payload` JSON shape:

```json
{
  "passenger": {
    "first_name": "Ana",
    "last_name": "Popescu",
    "date_of_birth": "1990-05-14",
    "email": "ana@example.com",
    "phone": "+40 712 345 678",
    "address": "Str. Exemplu 1",
    "postal_code": "010101"
  },
  "reservation_number": "ABC123",
  "segments": [
    {
      "order": 0,
      "flight_date": "2026-08-01",
      "flight_number": "AF1234",
      "airline": "Air France",
      "departure_airport_iata": "OTP",
      "arrival_airport_iata": "CDG",
      "planned_departure_time": "2026-08-01T09:00:00Z",
      "planned_arrival_time":   "2026-08-01T11:30:00Z",
      "is_problem_flight": true
    }
  ],
  "gdpr_consent": true
}
```

**Response 201 — success**:

```json
{
  "id": "c8f7c1e0-2a3b-4d1e-9f11-1234567890ab",
  "status": "NEW",
  "created_at": "2026-07-23T14:22:10Z"
}
```

**Response 400 — validation failure** (DRF field-error shape; mirrors the payload's own shape so the client can map errors mechanically):

```json
{
  "payload": {
    "passenger": { "email": ["Enter a valid email address."] },
    "segments":  { "non_field_errors": ["Exactly one segment must be marked as the problem flight."] },
    "gdpr_consent": ["You must accept the GDPR policy to submit."]
  },
  "boarding_pass": ["File exceeds 5 MB."],
  "id_document":   ["Unsupported file type; allowed: PDF, JPG, PNG."]
}
```

**Response 429 — rate limit exceeded**:

```json
{ "detail": "Request was throttled. Expected available in <n> seconds." }
```

**Transactional integrity — write order and rollback**:

1. **Phase A — validate everything, write nothing.** The serializer's `is_valid()` runs all field, cross-field, file, and DB-lookup validators (IATA existence, DoB, phone regex, file size, magic bytes, exactly-one-problem-flight, both files present). If anything fails, return `400` — no rows, no files.
2. **Phase B — persist inside `transaction.atomic()`.** Inside the atomic block, in order: `Case` → `FlightSegment` rows → `CaseDocument` rows (each `CaseDocument.file.save(...)` writes to `MEDIA_ROOT`).
3. **Rollback discipline.** The view wraps the atomic block in `try` / `except`. On any exception, it (a) collects the disk paths of any `CaseDocument` files already written in the same request, (b) lets `transaction.atomic()` roll back the DB, and (c) deletes those on-disk files in the `except` handler before re-raising into DRF's exception handler. Net result: either every row **and** every file exists, or none do.

### URL wiring

```
airassist/urls.py:
    path("admin/", admin.site.urls)
    path("api/", include("cases.urls"))
    path("api/", include("airports.urls"))
```

### Validation rules (server-side, mirrored client-side)

| # | rule | enforced by |
|---|---|---|
| 1 | all fields present | serializer `required=True` |
| 2 | `date_of_birth < today` | field validator |
| 3 | `email` matches RFC-5322-ish | `EmailValidator` |
| 4 | `phone` matches `^\+?[0-9\s\-()]{7,30}$` | `RegexValidator` |
| 5 | `postal_code` non-empty, ≤20 chars | field |
| 6 | 1–5 segments; `order` unique 0..N | serializer |
| 7 | exactly one `is_problem_flight=True` | serializer + Postgres partial-unique index |
| 8 | each segment's `planned_arrival_time > planned_departure_time` | serializer |
| 9 | airport IATA codes exist in DB | serializer (`.get()` lookup) |
| 10 | `gdpr_consent === true` | field validator |
| 11 | each file ≤ 5 MB | file validator |
| 12 | each file's `content_type` ∈ {pdf, jpeg, png} — **verified by extension AND magic bytes** | file validator |
| 13 | both `boarding_pass` and `id_document` present | view-level check |

### Rate limiting

DRF `AnonRateThrottle` at `20/hour` on `POST /api/cases/`. Configurable via `DEFAULT_THROTTLE_RATES`.

---

## 5. Frontend Design

### Component tree

```
App
└── CaseEntryForm                       // form provider, submit handler, top-level error banner
    ├── FlightItinerarySection          // segment[0]: date, flight_number, airline, from/to, times
    ├── ConnectingFlightsSection        // useFieldArray "segments" 1..4; +/− buttons
    ├── PassengerDetailsSection         // first/last name, DoB, email, phone, address, postal_code, reservation_number
    ├── DocumentsSection                // two file inputs; client-side size/type checks
    └── GdprSection                     // single checkbox; submit stays disabled until it is checked AND form is valid
```

- One shared `useForm({ resolver: zodResolver(caseSchema) })` context; sections access it via `useFormContext()`.
- **Problem-flight marker**: a single radio group at the top of `ConnectingFlightsSection` whose options are every segment currently in the form (`Segment 0 — AF1234`, `Connecting 1 — LH567`, …). Selecting one sets `is_problem_flight=true` on that segment and clears it on all others. The UI cannot produce zero or two problem flights.

### `AirportAutocomplete`

- Debounced 250 ms `GET /api/airports/?q=<query>`.
- Renders `IATA — Name (City, Country)` in the dropdown.
- Form value stored as the IATA string, not the full object.
- Loading, empty, and error states surfaced inline.

### Zod schema (client mirror of DRF)

`schema.ts` exports:

- `passengerSchema` — names non-empty, `date_of_birth` refined `< new Date()`, `email()`, phone regex identical to backend, address, postal_code.
- `segmentSchema` — `flight_date` (ISO date), `flight_number`/`airline` non-empty, `*_airport_iata` length 3, ISO datetime strings, `is_problem_flight` boolean.
- `caseSchema` — combines the above; `segments: z.array(segmentSchema).min(1).max(5).refine(exactlyOneProblemFlight)`; `gdpr_consent: z.literal(true)`; `boarding_pass`, `id_document` via `fileSchema`.
- `fileSchema` — `instanceof(File)`, `size <= 5 * 1024 * 1024`, `type ∈ {application/pdf, image/jpeg, image/png}`.

### Submit flow

1. Client Zod passes → build `FormData`: `payload = JSON.stringify({ passenger, reservation_number, segments, gdpr_consent })`, `boarding_pass = file`, `id_document = file`.
2. `POST /api/cases/` (no `Content-Type` header — the browser sets the multipart boundary).
3. On `201`: replace form with a success screen showing the returned `id` and `status`. No email / friendly reference number (deferred to CASE_04).
4. On `400`: walk the DRF error tree and call `setError(path, { message })` on RHF; scroll to the first error. Banner reads *"Please fix the highlighted fields."*.
5. On `413 / 415`: banner + focus the offending file input.
6. On network / 5xx: banner *"Could not submit. Please try again."* — form values preserved.
7. On `429`: banner *"Too many attempts. Please wait a minute and try again."*.

---

## 6. Security & Operational Notes

- **File upload safety**: verify content type via **both** file-extension and magic-byte inspection (`python-magic-bin` on Windows, `python-magic` elsewhere). Reject anything that mismatches.
- **Filename sanitisation**: `django.utils.text.get_valid_filename` + rewrite on save to `cases/<case_uuid>/<kind>_<uuid4>.<ext>`. Original filename retained only in DB.
- **Path traversal**: `FileField.upload_to` always uses the sanitised, UUID-based path — no user input is ever concatenated into filesystem paths.
- **CSRF**: DRF endpoints declare `SessionAuthentication` disabled and use `JSONParser` / `MultiPartParser` only, so Django's CSRF middleware does not fire on the API. The admin retains CSRF.
- **Rate limiting**: `AnonRateThrottle` at `20/hour` on the create endpoint.
- **Upload size caps**: `DATA_UPLOAD_MAX_MEMORY_SIZE = 12 MB`, `FILE_UPLOAD_MAX_MEMORY_SIZE = 6 MB` (streams to disk above threshold).
- **Secrets**: `DJANGO_SECRET_KEY`, `DATABASE_URL`, `AIRPORTGAP_TOKEN` (if needed) all come from `.env`. `.env.example` is checked in; real `.env` is git-ignored.
- **Debug / prod**: `settings/dev.py` sets `DEBUG=True`; `settings/prod.py` sets `DEBUG=False`, requires `ALLOWED_HOSTS`, and forces Postgres.
- **PII in logs**: on rejected uploads, log the reason + a hash of the filename, never the passenger's email or the file contents.
- **OWASP Top-10 coverage**: A01 access control (public endpoint by design, no IDOR because response only returns the new UUID), A03 injection (ORM only, no raw SQL), A05 misconfig (settings split, secrets in env), A08 integrity failures (magic-byte checking on uploads).

---

## 7. Testing Plan

### Backend — pytest + pytest-django

Location: `backend/cases/tests/`, `backend/airports/tests/`.

**Serializer unit tests** (`test_serializers.py`, `test_validators.py`):

- Valid payload passes.
- `date_of_birth == today` and future dates → rejected.
- Malformed email → rejected.
- Malformed phone → rejected.
- Zero problem flights → rejected.
- Two problem flights → rejected (serializer level).
- Unknown IATA → rejected with clear message.
- `gdpr_consent = false` → rejected.
- 6+ segments → rejected.
- `planned_arrival_time <= planned_departure_time` → rejected.

**File-validator unit tests** (parametrised): oversized, wrong extension, wrong magic bytes.

**API integration tests** (`test_api.py`, uses `APIClient`):

- Happy path: `POST /api/cases/` with two tiny fixture files → `201`; Case + N segments + 2 documents persisted; files exist on disk.
- One file too large → `400`; **no** rows written (transaction rollback assertion).
- Airport search: `GET /api/airports/?q=CDG` and `?q=Paris` return the fixture rows; empty `q` returns `[]`; `limit` capped at 50.

**Management command test** (`airports/tests/test_sync_airports.py`): given a mocked airportgap response, the command upserts rows idempotently.

### Frontend — Vitest + React Testing Library

Location: `frontend/tests/`.

- `<CaseEntryForm />` renders all five sections.
- Submit button is disabled until GDPR is checked **and** all required fields are valid.
- Zod errors surface under the correct labels (ARIA-linked via RHF).
- Selecting the problem-flight radio on segment B clears it on segment A.
- `AirportAutocomplete` calls `/api/airports/?q=` with debounce and renders returned items (`fetch` mocked with MSW or vitest mocks).
- A mocked `400` response from the server maps into per-field messages.

### Manual smoke test (definition of done)

1. Fresh clone → follow `README.md` → both apps start, DB migrated, airports seeded.
2. Open `http://localhost:5173/`, fill the form with valid data, upload a small PDF and a small JPG.
3. Submit → success screen shows a UUID.
4. `python manage.py shell` → `Case.objects.count() == 1`, `FlightSegment.objects.count() == segments_submitted`, `CaseDocument.objects.count() == 2`; files present under `backend/media/cases/<uuid>/`.
5. Deliberately break one field (e.g. remove GDPR, oversize a file) → submission blocked with the right message; no new rows created.

---

## 8. Definition of Done

- All server-side validation rules 1–13 (§4) implemented and covered by tests.
- All frontend validation mirrors server rules.
- `POST /api/cases/` returns `201` for a happy-path case and persists Case + segments + documents transactionally.
- Airport catalogue can be re-seeded with `python manage.py sync_airports`.
- `README.md` explains how to install prerequisites, create the venv, install Python deps, install npm deps, seed airports, run migrations, start both dev servers, and run all tests.
- `pytest` and `npm test` both pass on a clean checkout.
- No feature from the "out of scope" list has been implemented, even in stub form.
- `.env.example` present; real `.env` git-ignored; `media/` git-ignored; `db.sqlite3` git-ignored.

---

## 9. Risks & Assumptions

- **Assumption:** `airportgap.com`'s `/airports` endpoint is reachable at build/seed time from the dev machine. If it isn't, `sync_airports` accepts a `--from-fixture <path.json>` flag as a fallback for offline development. A tiny fixture (~5 airports) is shipped for tests.
- **Risk:** Postgres partial-unique index on `is_problem_flight` is not portable to SQLite; the migration guards it behind a `connection.vendor == 'postgresql'` check, and the same rule is enforced in the serializer so SQLite-based dev/test still catches violations.
- **Risk:** `python-magic` requires a `libmagic` binary. On Windows we pin `python-magic-bin` which ships the DLL. Documented in `README.md`.
- **Assumption:** English-only UI. i18n hooks are not installed; text lives directly in components.
- **Assumption:** Two-file limit (Boarding Pass + ID) is fixed by the story; multi-file per kind is out of scope.

---

## 10. Story ↔ Task Mapping (informational; the actual Phase-2 plan will re-slice these)

| Backlog task | Where it lives in this spec |
|---|---|
| Case creation API | §4 `POST /api/cases/` |
| Airport code lookup integration | §4 `GET /api/airports/`, §3 `Airport` model, seed command |
| Connecting-flight logic | §3 `FlightSegment`, §5 `ConnectingFlightsSection` |
| Problem-flight validation | §4 rule 7 (serializer + partial-unique index) |
| File upload validation | §4 rules 11–13, §6 magic-byte check |
| GDPR consent enforcement | §3 `Case.gdpr_consent`, §4 rule 10 |
| Case status workflow (NEW only) | §3 `Case.status` choices + default |
| Case entry form (React) | §5 |
| Passenger details section | §5 `PassengerDetailsSection` |
| Flight details section | §5 `FlightItinerarySection` |
| Connecting flights UI | §5 `ConnectingFlightsSection` |
| Document upload UI | §5 `DocumentsSection` |
| GDPR checkbox UI | §5 `GdprSection` |
| Required-field validation | §5 Zod schema + §4 rule 1 |
| Case table/model | §3 `Case` |
| Passenger data fields | §3 `Case` (passenger fields) |
| Flight/connection records | §3 `FlightSegment` |
| Uploaded document metadata | §3 `CaseDocument` |
| GDPR consent fields | §3 `Case.gdpr_consent`, `gdpr_consent_at` |
| Case status field | §3 `Case.status` |
