# CASE_02 — Compensation Calculation: Design Spec

**Project:** AirAssist (EU 261/2004 flight-compensation claim management)
**Story:** CASE_02 — Compensation calculation from flight distance (Epic: *Case Register*, Priority 2)
**Date:** 2026-07-23
**Status:** Approved for planning
**Depends on:** [CASE_01 Case Entry design](2026-07-23-case-01-case-entry-design.md) (this spec extends the existing `cases` and `airports` apps built there).

---

## 1. Purpose & Scope

Extend the CASE_01 case-entry flow so that, as the passenger fills the itinerary, the system continuously calculates the total flight distance and the corresponding EU 261 compensation bracket, shows both to the passenger, and — on submit — persists them atomically with the new `Case` row.

### In scope (CASE_02)

- New public endpoint `POST /api/compensation/preview` — returns `distance_km`, `compensation_amount_eur`, and a per-leg breakdown for a list of IATA pairs.
- New backend module `cases.compensation` — pure functions for distance and bracket math.
- Integration with Airport Gap's `POST /airports/distance` endpoint, with a **local Haversine fallback** using the `latitude` / `longitude` columns already seeded on `airports.Airport`.
- Three additive columns on `cases.Case` (`distance_km`, `compensation_amount_eur`, `compensation_calculated_at`), populated inside the existing case-create transaction.
- Additive fields on the `POST /api/cases/` 201 response (`distance_km`, `compensation_amount_eur`, `compensation_error`); no changes to the request shape or the existing validation rules.
- Live in-form compensation summary component on the frontend (debounced preview calls, above the submit button).
- Unit tests for brackets, distance client (both branches), preview endpoint, and case-create side effects.

### Explicitly out of scope

Deferred to their respective stories — this slice **must not** implement even stubs of:

- Disruption type / motives collection (form parts 2 & 3) → CASE_03
- Eligibility rules & `VALID` status transition (e.g. reduced 50 % compensation for late-arrival relief under Art. 7 §2) → ELIGIBILITY_01 / ELIGIBILITY_02
- Editing airports after case creation / recalculation on stored cases → future story
- Auditable history of past calculations (versioning) → future story
- Displaying a friendly case reference number, confirmation email, PDF contract → CASE_04 / CASE_COMPLETED_*
- Currency conversion (compensation is always EUR)
- Distinguishing intra-EU flights from non-EU (that's an eligibility concern, not a distance concern)

---

## 2. Architecture Overview

### End-to-end flow

1. Passenger fills the CASE_01 form. Whenever the ordered list of segments changes — any airport picked/cleared, a leg added or removed, or a reorder — the frontend debounces (~400 ms) and calls `POST /api/compensation/preview` with the ordered list of `(from, to)` IATA pairs.
2. Backend computes each leg's great-circle distance, sums them, maps the total to a bracket, and returns the total distance, amount, and per-leg breakdown.
3. Frontend renders a **Compensation Summary** component above the submit button. On success it shows the amount and total distance; while pending it shows "Calculating…"; on failure it shows a soft, non-blocking notice.
4. On submit, `POST /api/cases/` runs the **same calculation server-side** (never trusts the client value), and persists `distance_km` / `compensation_amount_eur` / `compensation_calculated_at` on the new `Case` row **inside the existing atomic block**.
5. If the server-side calculation fails, the case is still created (`status=NEW`) with those three fields left `NULL`, and the 201 response carries a `compensation_error` message so the UI can show a warning toast. Case creation must never be blocked by a compensation-math failure.

### Origin / destination definition (confirmed with product)

The total distance is the **sum of the great-circle distances of every consecutive leg**, following the passenger's ordered itinerary (`FlightSegment.order` ascending). Example: for `JFK→LHR→CDG`, `distance_km = great_circle(JFK,LHR) + great_circle(LHR,CDG)`.

> Note — the CASE_02 user-story text as delivered ("*orthodromic distance between the starting and final destination (connecting flights are not considered)*") was **deliberately overridden** by product during design: they want the summed itinerary length. This spec is the source of truth.

### Bracket rule (confirmed with product)

| distance (km) | compensation |
|---|---|
| `d ≤ 1500` | **250 €** |
| `1500 < d ≤ 3500` | **400 €** |
| `d > 3500` | **600 €** |

Boundary values (`1500.00`, `3500.00`) fall into the *lower* bracket. No other amounts are ever emitted.

### Distance source (confirmed with product)

**External Airport Gap API first, local Haversine as fallback.**

- Airport Gap `POST /api/airports/distance` is called per leg with a 3-second timeout, one retry on `ConnectionError` / `Timeout`, honouring `settings.AIRPORTGAP_TOKEN` when non-empty (Airport Gap allows both authenticated and unauthenticated calls to this endpoint per its docs example).
- On any failure — HTTP ≥ 400, network error, malformed body, missing `kilometers` field — the code falls back to a **local Haversine calculation** using the `latitude` / `longitude` already seeded on `airports.Airport`.
- If both fail (e.g. Airport Gap is down *and* one of the leg's airports somehow has null lat/lon), the whole calculation raises `DistanceUnavailable`; the preview endpoint returns `422`, and the case-create view catches it and persists the case with `NULL` compensation fields plus a `compensation_error` on the response.
- Each leg carries a `source: "airportgap" | "haversine"` marker in the preview response so QA can see which branch was used.

### Repo layout changes

Only **additive** files; no CASE_01 file is renamed or split:

```
backend/cases/
    compensation/
        __init__.py                     # re-exports compute_for_case, preview_from_legs
        service.py                      # orchestration: compute_for_case(case), preview_from_legs(legs)
        distance.py                     # compute_leg_km, _haversine_km, _airportgap_km
        brackets.py                     # compensation_for_km(distance_km) -> 250|400|600
        exceptions.py                   # DistanceUnavailable
    migrations/
        0002_case_compensation_fields.py
    tests/
        test_compensation_brackets.py
        test_compensation_distance.py
        test_compensation_preview_api.py
        # test_api.py: extended, not new

frontend/src/
    api/compensation.ts                 # previewCompensation(legs)
    features/case-entry/
        CompensationSummary.tsx         # new component
        # CaseEntryForm.tsx: extended to render <CompensationSummary/>

frontend/tests/
    CompensationSummary.test.tsx
    # CaseEntryForm.test.tsx: extended
```

### Environment variables (additive)

No new required variables. Reuse the existing CASE_01 settings:

- `AIRPORTGAP_BASE_URL` — already set (`https://airportgap.com/api`).
- `AIRPORTGAP_TOKEN` — already optional; if present, sent as `Authorization: Bearer token=<value>` on distance calls.
- New optional setting `COMPENSATION_HTTP_TIMEOUT_S` (default `3.0`) — only overridden in tests.

---

## 3. Data Model Changes

Single Django migration: `cases/migrations/0002_case_compensation_fields.py`.

### `cases.Case` — three new nullable fields

| field | type | notes |
|---|---|---|
| `distance_km` | `DecimalField(max_digits=9, decimal_places=2, null=True, blank=True)` | Total great-circle distance across all legs, rounded to 2 decimals |
| `compensation_amount_eur` | `PositiveSmallIntegerField(null=True, blank=True)` | Constrained to `{250, 400, 600, NULL}` |
| `compensation_calculated_at` | `DateTimeField(null=True, blank=True)` | Server timestamp of the successful calc; `NULL` iff either of the above is `NULL` |

**Constraint:**

```python
models.CheckConstraint(
    check=(
        Q(compensation_amount_eur__isnull=True)
        | Q(compensation_amount_eur__in=[250, 400, 600])
    ),
    name="compensation_amount_eur_valid",
)
```

**Invariant** (enforced in code, not by DB): if any of the three fields is non-null, all three are non-null. Test coverage asserts this.

All three fields are exposed **read-only** in `cases/admin.py`.

No changes to `FlightSegment`, `CaseDocument`, or `Airport`.

---

## 4. API Contract

### `POST /api/compensation/preview` (new)

- `AllowAny`. Throttled at **`60/min` per IP** via a new DRF throttle scope `compensation_preview` (higher than case-create's `20/hour` because the frontend calls this live while typing).
- Content type: `application/json`.

**Request:**

```json
{
  "legs": [
    { "from": "JFK", "to": "LHR" },
    { "from": "LHR", "to": "CDG" }
  ]
}
```

- `legs`: 1–5 items (matches CASE_01's segment cap).
- `from`, `to`: 3-letter IATA codes (case-insensitive; normalised to uppercase server-side).

**Response 200:**

```json
{
  "distance_km": 5884.42,
  "compensation_amount_eur": 600,
  "legs": [
    { "from": "JFK", "to": "LHR", "distance_km": 5540.12, "source": "airportgap" },
    { "from": "LHR", "to": "CDG", "distance_km": 344.30, "source": "haversine" }
  ]
}
```

- `distance_km` fields are rounded to 2 decimals using banker's rounding (`ROUND_HALF_EVEN`).
- `source ∈ { "airportgap", "haversine" }` per leg.

**Response 400** — malformed input:

```json
{ "legs": ["This list must contain between 1 and 5 items."] }
```

Or, for individual bad items:

```json
{ "legs": [{}, { "from": ["IATA codes must be exactly 3 letters."] }] }
```

**Response 422** — well-formed but calculation impossible for at least one leg (unknown IATA in DB, or Airport Gap unreachable and one endpoint lacks lat/lon). No partial success: the whole request fails so the frontend has no ambiguity.

```json
{
  "detail": "Distance could not be calculated for one or more legs.",
  "legs": [
    { "from": "JFK", "to": "LHR", "distance_km": 5540.12, "source": "airportgap", "error": null },
    { "from": "XXX", "to": "CDG", "distance_km": null, "source": null, "error": "Unknown airport code: XXX" }
  ]
}
```

**Response 429** — throttled:

```json
{ "detail": "Request was throttled. Expected available in <n> seconds." }
```

### `POST /api/cases/` (existing) — additive changes only

**Request shape:** unchanged from CASE_01.

**201 response — success case:**

```json
{
  "id": "c8f7c1e0-2a3b-4d1e-9f11-1234567890ab",
  "status": "NEW",
  "created_at": "2026-07-23T14:22:10Z",
  "distance_km": 5884.42,
  "compensation_amount_eur": 600,
  "compensation_error": null
}
```

**201 response — compensation failed but case saved:**

```json
{
  "id": "c8f7c1e0-2a3b-4d1e-9f11-1234567890ab",
  "status": "NEW",
  "created_at": "2026-07-23T14:22:10Z",
  "distance_km": null,
  "compensation_amount_eur": null,
  "compensation_error": "Distance could not be calculated; you can review this case later."
}
```

- `distance_km` / `compensation_amount_eur` are `null` iff the calc raised `DistanceUnavailable`.
- `compensation_error` is `null` iff the calc succeeded.
- The two are strictly correlated: `(amount is null) ⇔ (error is not null)`.

**400 / 429 responses:** unchanged from CASE_01.

### Transactional integrity

The existing `CaseCreateView.post` flow is extended inside the `transaction.atomic()` block, immediately after `payload_ser.save()`:

```python
with transaction.atomic():
    case = payload_ser.save()
    try:
        compute_for_case(case)   # mutates case.distance_km / .compensation_amount_eur / .compensation_calculated_at
        case.save(update_fields=[
            "distance_km", "compensation_amount_eur", "compensation_calculated_at",
        ])
        compensation_error = None
    except DistanceUnavailable as exc:
        compensation_error = str(exc)   # left as NULL; case still committed
    # ... existing file-writing loop (unchanged) ...
```

A `DistanceUnavailable` inside the block **does not** roll back. Any *other* exception (DB error, disk failure during file save) still triggers the existing rollback path from CASE_01, including the on-disk file cleanup.

### URL wiring

`cases/urls.py` gets one new line:

```python
path("compensation/preview/", CompensationPreviewView.as_view(), name="compensation-preview")
```

No changes to `airassist/urls.py`.

### DRF throttle settings

`airassist/settings/base.py` — `REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]` gains one entry:

```python
"compensation_preview": "60/min",
```

---

## 5. Backend Module Design

### `cases.compensation.brackets`

Pure, dependency-free:

```python
from decimal import Decimal

def compensation_for_km(distance_km: Decimal | float | int) -> int:
    d = Decimal(str(distance_km))
    if d <= Decimal("1500"):
        return 250
    if d <= Decimal("3500"):
        return 400
    return 600
```

Table-driven test covers 0, 1499.99, 1500.00, 1500.01, 3499.99, 3500.00, 3500.01, 20000.

### `cases.compensation.distance`

```python
EARTH_RADIUS_KM = Decimal("6371.0088")

def compute_leg_km(from_iata: str, to_iata: str, *, airport_lookup) -> tuple[Decimal, str]:
    """Return (distance_km, source). Tries Airport Gap first, falls back to Haversine.
       Raises DistanceUnavailable if both branches fail."""
```

- `airport_lookup(iata: str) -> Airport | None` is injected so the service can pre-fetch airports (avoids N+1) and so tests can stub it.
- `_airportgap_km(from_iata, to_iata)` uses `requests.post` with `data={"from": from_iata, "to": to_iata}`, `timeout=settings.COMPENSATION_HTTP_TIMEOUT_S`, one retry on `ConnectionError`/`Timeout`. Parses `data.attributes.kilometers` from the JSON:API response. Any HTTP status ≥ 400, missing key, or non-numeric value raises internal `_AirportGapError`.
- `_haversine_km(a: Airport, b: Airport) -> Decimal` uses `Decimal` throughout to keep results stable across CPython/PyPy; returns `Decimal` rounded to 6 decimals (final rounding to 2dp happens in the service).
- If Airport Gap raises **and** either airport is `None` or has null lat/lon → raise `DistanceUnavailable(f"Distance unavailable for {from_iata}-{to_iata}")`.

### `cases.compensation.service`

```python
def preview_from_legs(raw_legs: list[dict]) -> dict:
    """Public API used by the preview view. Returns the response body dict.
       Raises DRF ValidationError(400) or DistanceUnavailable (mapped to 422 by the view)."""

def compute_for_case(case: Case) -> None:
    """Reads case.segments ordered by `order`, computes per-leg distances,
       sums, brackets, and mutates the case in-place (does NOT call .save()).
       Raises DistanceUnavailable on failure — caller decides how to handle."""
```

Both functions share a single `_build_airport_lookup(iatas)` helper that does one `Airport.objects.filter(iata__in=iatas)` query and returns a `dict[str, Airport]`, keeping DB access to one round-trip per calculation.

### `cases.compensation.exceptions`

```python
class DistanceUnavailable(Exception):
    """Raised when a leg's distance cannot be determined by any source."""
```

### `cases.views` — new view

```python
class CompensationPreviewThrottle(AnonRateThrottle):
    scope = "compensation_preview"

class CompensationPreviewView(APIView):
    throttle_classes = [CompensationPreviewThrottle]

    def post(self, request, *args, **kwargs):
        serializer = PreviewRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            body = preview_from_legs(serializer.validated_data["legs"])
        except DistanceUnavailable as exc:
            return Response(exc.payload, status=422)   # exc carries the per-leg dict
        return Response(body, status=200)
```

`DistanceUnavailable` gains a `.payload` attribute (built by the service) so the view can return a structured 422 without knowing internals.

---

## 6. Frontend Design

### Component tree change

Only `CaseEntryForm` is modified; `CompensationSummary` is inserted between the last section and the submit button:

```
CaseEntryForm
├── FlightItinerarySection
├── ConnectingFlightsSection
├── PassengerDetailsSection
├── DocumentsSection
├── GdprSection
├── CompensationSummary          ← NEW
└── <button type="submit">
```

### `CompensationSummary.tsx`

- Uses `useWatch({ control, name: "segments" })` from React Hook Form to reactively observe the ordered segment list.
- Extracts `legs: {from, to}[]` from segments in `order` ascending.
- Ignores legs where either IATA is missing / not yet 3 chars.
- If `legs.length === 0`, renders nothing (silent — no scary "unable to calculate" while the form is still empty).
- Otherwise, debounces 400 ms via a small `useDebouncedValue(legs, 400)` helper (colocated in the same file — YAGNI on a shared hook module), then calls `previewCompensation(legs)`.
- Uses `AbortController` to cancel in-flight requests when `legs` changes; guards against out-of-order responses.
- Rendered states:
  - **Loading** — `Calculating compensation…`
  - **Success (200)** — bold amount (`400 €`) + `Total flight distance: 3 210 km across 2 leg(s).` Distance shown as an integer km (rounded from the 2dp response), grouped with a non-breaking narrow space.
  - **Soft failure (422 or network)** — `We couldn't calculate compensation yet — check that all airport codes are valid.` No form-level error, submit stays enabled.
  - **429 throttled** — `Too many attempts; retrying shortly.` Component schedules an automatic retry after the `Retry-After` (or 5s default). Submit stays enabled.

Component is presentation-only — it does not put anything into form state (server is the single source of truth on submit).

### `api/compensation.ts`

```ts
export interface CompensationLeg { from: string; to: string; }
export interface CompensationBreakdownLeg {
  from: string; to: string;
  distance_km: number | null;
  source: "airportgap" | "haversine" | null;
  error?: string | null;
}
export interface CompensationPreview {
  distance_km: number;
  compensation_amount_eur: 250 | 400 | 600;
  legs: CompensationBreakdownLeg[];
}
export async function previewCompensation(
  legs: CompensationLeg[], signal?: AbortSignal
): Promise<CompensationPreview> { /* fetch POST /api/compensation/preview */ }
```

Errors are surfaced as typed rejections (`CompensationUnavailable` for 422, `HttpError` otherwise) so the component can branch cleanly.

### `CaseEntryForm.tsx` changes

- Renders `<CompensationSummary />` above the submit button.
- Extends the submit-success handler: reads `distance_km`, `compensation_amount_eur`, `compensation_error` from the 201 body and dispatches a toast — success (`Compensation of 400 € registered for your case.`) or warning (`Case created, but compensation could not be calculated. Our team will review it.`).

No other CASE_01 files change.

---

## 7. Validation Rules (server-side)

| # | rule | enforced by |
|---|---|---|
| P1 | `legs` present, 1–5 items | `PreviewRequestSerializer` |
| P2 | each `from`/`to` is 3 letters | serializer per-item |
| P3 | IATA codes normalised to upper-case | serializer `to_internal_value` |
| P4 | every IATA in `legs` exists in `Airport` | `service._build_airport_lookup` (missing → `DistanceUnavailable` with per-leg error) |
| P5 | `from != to` on a single leg | serializer per-item (a 0-km leg is legal but almost certainly a UI bug; reject with 400) |

Case-create keeps its CASE_01 rules unchanged; the compensation calc is *side-effectful* only — never blocks case creation.

---

## 8. Testing Strategy

### Backend (pytest, pytest-django)

- `test_compensation_brackets.py` — table-driven boundary tests (0, 1499.99, 1500, 1500.01, 3499.99, 3500, 3500.01, 20000).
- `test_compensation_distance.py`
  - Haversine correctness: JFK↔LHR ≈ 5540 km (±1 km), CDG↔OTP ≈ 1874 km (±1 km), same-airport = 0.
  - Airport Gap happy path (mocked with `responses`).
  - Fallback: Airport Gap raises `Timeout` → Haversine result returned, `source="haversine"`.
  - Both fail: raises `DistanceUnavailable`.
  - Retry: one `ConnectionError` then success = one retry consumed.
- `test_compensation_preview_api.py`
  - 200 happy path with two legs, distance summed, correct bracket.
  - 400 on empty `legs`, 6-item `legs`, malformed IATA (`"JF"`, `"jfkk"`, non-string).
  - 422 on unknown IATA with per-leg error structure.
  - 422 when service raises after simulated dual failure.
  - 429 after 61 requests inside a minute (throttle asserted with `RequestFactory` + patched cache).
- `test_api.py` — extended:
  - Successful submit returns `distance_km`, `compensation_amount_eur`, `compensation_error: null`; case row has the persisted values.
  - Failed calc (monkeypatched to raise `DistanceUnavailable`) still returns 201 with nulls + `compensation_error` message; case row has NULLs.
  - Check constraint rejects a raw ORM insert of `compensation_amount_eur=123`.

### Frontend (Vitest + React Testing Library)

- `CompensationSummary.test.tsx`
  - Renders nothing when no legs.
  - Renders `Calculating compensation…` while the mocked fetch is pending.
  - Renders `400 €` and `3 210 km across 2 leg(s)` on success.
  - Renders the soft-error copy on 422 and on network error; submit button remains enabled.
  - Debouncing: rapid IATA typing yields **one** fetch call after 400 ms (fake timers).
  - Aborts the in-flight request when legs change.
- `CaseEntryForm.test.tsx` — extended:
  - `<CompensationSummary/>` is present above the submit button.
  - Success toast fires when the 201 response carries `compensation_amount_eur`.
  - Warning toast fires when it carries `compensation_error`.

### Manual QA checklist (documented in the plan, not the spec)

- Pick two European airports (`OTP`→`CDG`) → expect 400 €.
- Pick a short leg (`CDG`→`AMS`) → expect 250 €.
- Pick a long leg (`JFK`→`SFO`) → expect 600 €.
- Add a bogus IATA → soft error, submit remains enabled, backend still creates the case with `compensation_error`.

---

## 9. Non-Functional Constraints

- **Latency budget** — preview endpoint should respond in < 500 ms P95 on cache miss (3 s Airport Gap timeout × up-to-5 legs is a worst case only when the external API is degraded; Haversine fallback is < 1 ms).
- **Per-process cache** — `_airportgap_km` results are memoised for the request's lifetime keyed by `frozenset({from, to})`, so re-ordering `JFK→LHR` and `LHR→JFK` shares a cache entry.
- **Determinism** — Haversine uses `Decimal` and `EARTH_RADIUS_KM = 6371.0088`; tests assert exact values.
- **No PII leaves the process** — the preview endpoint receives only IATA codes; the case-create path continues to protect PII as in CASE_01.
- **Rollback discipline** — a `DistanceUnavailable` never rolls back; any other exception uses the existing CASE_01 rollback (including on-disk file cleanup).
- **YAGNI** — no historical compensation log, no recalculation-after-submit endpoint, no per-leg persistence, no currency conversion. Add them in follow-up stories if actually needed.
