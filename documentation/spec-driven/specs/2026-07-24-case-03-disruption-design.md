# CASE_03 — Disruption Info: Design Spec

**Project:** AirAssist (EU 261/2004 flight-compensation claim management)
**Story:** CASE_03 — Disruption motive & incident description (Epic: *Case Register*, Priority 3)
**Date:** 2026-07-24
**Status:** Approved for planning
**Depends on:**
- [CASE_01 Case Entry design](2026-07-23-case-01-case-entry-design.md)
- [CASE_02 Compensation design](2026-07-23-case-02-compensation-design.md)

---

## 1. Purpose & Scope

Extend the CASE_01 case-entry flow so the passenger must describe **what happened** to their flight — the disruption type, the type-specific sub-answers, whether the airline stated a motive, and a free-text description of the incident. The information is persisted on the same `Case` row inside the existing atomic create transaction. Without it, the case cannot be submitted.

### In scope (CASE_03)

- New **required** `disruption` block on `POST /api/cases/` — nested object inside the existing `payload` field, alongside `passenger` / `segments` / `gdpr_consent`.
- Three disruption types with distinct required sub-answers: `CANCELLATION`, `DELAY`, `DENIED_BOARDING`.
- Server-side enforcement of the enum option sets and the conditional-required matrix. Cross-branch contamination (e.g. `delay_duration` sent with `CANCELLATION`) is rejected with a 400.
- Free-text `incident_description`, 1–2000 characters, always required.
- Additive **DB migration** `cases/0003_disruption_fields.py` — 8 new columns on `Case`, one `CheckConstraint`.
- Additive fields on the `POST /api/cases/` 201 response (nested `disruption` object mirroring the persisted values).
- New **frontend section** `DisruptionSection.tsx` — dropdown-driven, mounted after Connecting flights, with conditional field rendering.
- Zod schema: discriminated union on `disruption_type`.
- Backend admin: all 8 fields exposed read-only.
- Tests: new pytest module for the disruption serializer + extensions to `test_api.py`; new Vitest suite for `DisruptionSection` + extension to `CaseEntryForm.test.tsx`.

### Explicitly out of scope

Deferred to their respective stories — this slice **must not** implement even stubs of:

- Eligibility rules that use disruption values to accept/reject/reduce compensation (e.g. weather/strike as "extraordinary circumstances", `LESS_THAN_3H` delay disqualifying the claim, `MORE_THAN_14_DAYS` cancellation notice disqualifying the claim, voluntary denied boarding disqualifying the claim) → ELIGIBILITY_01 / ELIGIBILITY_02.
- Any change to the CASE_02 compensation amount based on disruption type — the compensation-preview endpoint and the persisted amount are unchanged.
- Validation of the motive against the airline's own official statement — the AC explicitly says passenger answers are not judged for correctness.
- Editing disruption fields after case creation → future story.
- Attachments related to disruption (e.g. delay certificate) → future story.
- Displaying disruption on any downstream artefact (confirmation email, PDF contract) → CASE_COMPLETED_*.
- I18n; strings stay English.

---

## 2. Architecture Overview

### End-to-end flow

1. Passenger fills the CASE_01 form. After the Connecting-flights section they hit the new **Disruption** section.
2. They pick a `disruption_type` from a dropdown. The rest of the section renders **conditionally**:
   - `CANCELLATION` → notice window + airline-motive block.
   - `DELAY` → delay duration + airline-motive block.
   - `DENIED_BOARDING` → voluntary yes/no; if no, the reason dropdown appears.
3. All three branches show the free-text `incident_description` textarea with a live `n / 2000` character counter.
4. Zod (`disruptionSchema`, a `z.discriminatedUnion` on `disruption_type`) blocks submission until every required field for the chosen type is filled. Error rendering follows the existing `sections.module.css` pattern.
5. On submit, the frontend serialises the disruption object under `payload.disruption` in the existing multipart request. No new HTTP endpoint.
6. Backend `CaseCreateSerializer` validates the nested `DisruptionSerializer`, then `create()` copies the 8 disruption fields onto the new `Case` row inside the **existing** atomic block. CASE_02 compensation calc runs immediately after, unchanged.
7. The 201 response mirrors the persisted disruption values back under `"disruption": {...}`.

### Design principles

- **Additive only.** No CASE_01 or CASE_02 file is renamed, split, or refactored. The disruption fields are strictly new columns; the conditional logic lives in the serializer, not in the ORM.
- **One source of truth for enum values.** Backend `TextChoices` classes define the canonical string values; the frontend re-declares the same string literals in a single `disruption.ts` constants module and Zod uses `z.enum([...])` against them.
- **Enum enforcement, not motive judgement.** Server rejects values *not in the presented dropdowns* (400), but never rejects a case because a passenger's answer seems wrong. This preserves the AC's "no validation on motive answers" while still keeping DB values clean for future reporting.
- **Conditional-nullability in the serializer.** Database `CheckConstraint` only enforces that `disruption_type` is non-null. All finer-grained conditional-required rules live in `DisruptionSerializer.validate()` — same pattern CASE_02 used for its compensation-fields invariant.
- **No changes to compensation.** `cases/compensation/*` is untouched; the compensation-preview endpoint is untouched. Disruption values are stored but never read by any downstream code in this story.

### Repo layout changes

Only **additive** files; no CASE_01/CASE_02 file is renamed or split:

```
backend/cases/
    disruption/
        __init__.py                    # re-exports choices + DisruptionSerializer
        choices.py                     # TextChoices for all 7 enum-like fields
    serializers.py                     # extended: DisruptionSerializer + wired into CaseCreateSerializer
    models.py                          # extended: 8 new fields + CheckConstraint
    admin.py                           # extended: 8 fields shown read-only
    views.py                           # extended: 201 response includes "disruption": {...}
    migrations/
        0003_disruption_fields.py      # new
    tests/
        test_disruption_serializer.py  # new
        test_api.py                    # extended, not new

frontend/src/features/case-entry/
    disruption.ts                      # new: enum literals + label maps for dropdowns
    sections/
        DisruptionSection.tsx          # new
        DisruptionSection.module.css   # new (or reuse sections.module.css)
    schema.ts                          # extended: disruptionSchema + merged into caseFormSchema
    types.ts                           # extended: DisruptionInput + CasePayload gains `disruption`
    CaseEntryForm.tsx                  # extended: renders <DisruptionSection/> after ConnectingFlightsSection

frontend/tests/
    DisruptionSection.test.tsx         # new
    CaseEntryForm.test.tsx             # extended payload assertion
```

### Environment variables

None. This story adds no new settings and no new external dependencies.

---

## 3. Data Model Changes

Single Django migration: `cases/migrations/0003_disruption_fields.py`.

### `cases.Case` — 8 new fields

| field | type | notes |
|---|---|---|
| `disruption_type` | `CharField(max_length=20, choices=DisruptionType.choices)` | **NOT NULL.** One of `CANCELLATION`, `DELAY`, `DENIED_BOARDING`. |
| `cancellation_notice` | `CharField(max_length=20, choices=CancellationNotice.choices, null=True, blank=True)` | Required iff `disruption_type == CANCELLATION`. |
| `delay_duration` | `CharField(max_length=20, choices=DelayDuration.choices, null=True, blank=True)` | Required iff `disruption_type == DELAY`. |
| `denied_boarding_voluntary` | `BooleanField(null=True, blank=True)` | Required iff `disruption_type == DENIED_BOARDING`. API accepts `"YES"`/`"NO"` strings (see §4). |
| `denied_boarding_reason` | `CharField(max_length=30, choices=DeniedBoardingReason.choices, null=True, blank=True)` | Required iff `disruption_type == DENIED_BOARDING` **and** `denied_boarding_voluntary is False`. |
| `airline_motive_mentioned` | `CharField(max_length=10, choices=MotiveMentioned.choices, null=True, blank=True)` | Required iff `disruption_type` in `{CANCELLATION, DELAY}`. |
| `airline_motive` | `CharField(max_length=20, choices=AirlineMotive.choices, null=True, blank=True)` | Required iff `airline_motive_mentioned == "YES"`. |
| `incident_description` | `TextField(max_length=2000)` | **NOT NULL, non-empty.** 1–2000 characters. |

### Migration column defaults (backfill)

The migration adds `disruption_type` and `incident_description` as `NOT NULL` columns. Because CASE_01 / CASE_02 have already been merged, existing rows in the dev DB (if any) need a backfill value:

- `disruption_type` → sentinel value **`"UNSPECIFIED"`** added *only* to `DisruptionType.choices` for the purpose of the backfill. New API submissions never accept `UNSPECIFIED` (the serializer's `choices` list excludes it — see §4).
- `incident_description` → `"(migrated from CASE_01/CASE_02; no disruption info collected)"`.

The migration is written in three ops: `AddField(disruption_type, default="UNSPECIFIED")`, `AddField(incident_description, default="(migrated ...)")`, then `AlterField` to drop the defaults (columns stay `NOT NULL` at the DB level). All six optional fields are added `null=True`; no backfill needed.

### Constraint

```python
models.CheckConstraint(
    check=Q(disruption_type__in=[
        "CANCELLATION", "DELAY", "DENIED_BOARDING", "UNSPECIFIED",
    ]),
    name="disruption_type_valid",
)
```

`UNSPECIFIED` is accepted at the DB level only so pre-existing backfilled rows remain valid. The serializer's exposed choices (§4) exclude it, so new submissions can never write it.

### Invariants (enforced in the serializer, tested)

1. If `disruption_type == CANCELLATION`: `cancellation_notice` non-null; `delay_duration`, `denied_boarding_voluntary`, `denied_boarding_reason` all null.
2. If `disruption_type == DELAY`: `delay_duration` non-null; `cancellation_notice`, `denied_boarding_voluntary`, `denied_boarding_reason` all null.
3. If `disruption_type == DENIED_BOARDING`: `denied_boarding_voluntary` non-null; `cancellation_notice`, `delay_duration`, `airline_motive_mentioned`, `airline_motive` all null. If voluntary is `False`, `denied_boarding_reason` non-null; if `True`, `denied_boarding_reason` null.
4. If `airline_motive_mentioned == "YES"`: `airline_motive` non-null. Otherwise null.
5. `incident_description` is always non-empty after strip and ≤ 2000 chars.

### TextChoices (`cases/disruption/choices.py`)

```python
from django.db import models


class DisruptionType(models.TextChoices):
    CANCELLATION = "CANCELLATION", "Cancellation"
    DELAY = "DELAY", "Delay"
    DENIED_BOARDING = "DENIED_BOARDING", "Denied boarding"
    # DB-only sentinel for backfilled rows; excluded from serializer choices.
    UNSPECIFIED = "UNSPECIFIED", "Unspecified (legacy)"


class CancellationNotice(models.TextChoices):
    MORE_THAN_14_DAYS = "MORE_THAN_14_DAYS", "More than 14 days before"
    LESS_THAN_14_DAYS = "LESS_THAN_14_DAYS", "Less than 14 days before"
    ON_FLIGHT_DAY = "ON_FLIGHT_DAY", "On the flight day"


class DelayDuration(models.TextChoices):
    LESS_THAN_3H = "LESS_THAN_3H", "Less than 3 hours"
    MORE_THAN_3H = "MORE_THAN_3H", "More than 3 hours"
    CONNECTION_LOST = "CONNECTION_LOST", "Connection flight lost"


class DeniedBoardingReason(models.TextChoices):
    OVERBOOKED = "OVERBOOKED", "Flight overbooked"
    AGGRESSIVE_BEHAVIOR = "AGGRESSIVE_BEHAVIOR", "Aggressive behaviour with staff"
    INTOXICATION = "INTOXICATION", "Intoxication"
    UNSPECIFIED = "UNSPECIFIED", "Unspecified reason"


class MotiveMentioned(models.TextChoices):
    YES = "YES", "Yes"
    NO = "NO", "No"
    DONT_KNOW = "DONT_KNOW", "I don't know"


class AirlineMotive(models.TextChoices):
    TECHNICAL = "TECHNICAL", "Technical problem"
    WEATHER = "WEATHER", "Meteorological conditions"
    STRIKE = "STRIKE", "Strike"
    AIRPORT_ISSUE = "AIRPORT_ISSUE", "Problems with airport"
    CREW = "CREW", "Crew problems"
    OTHER = "OTHER", "Other motives"
```

`DeniedBoardingReason.UNSPECIFIED` and `DisruptionType.UNSPECIFIED` share the string literal `"UNSPECIFIED"` but live in different fields — no collision.

### Admin

`cases/admin.py` — add all 8 new fields to `readonly_fields` and to a dedicated **"Disruption"** fieldset. No list-filter changes.

No changes to `FlightSegment`, `CaseDocument`, `Airport`, or the compensation module.

---

## 4. API Contract

### `POST /api/cases/` — extended request (multipart `payload` field)

Only the `disruption` sub-object is new. Everything else is unchanged from CASE_02.

```json
{
  "passenger": { "...": "unchanged" },
  "reservation_number": "ABC123",
  "segments": [ { "...": "unchanged" } ],
  "disruption": {
    "disruption_type": "DELAY",
    "delay_duration": "MORE_THAN_3H",
    "airline_motive_mentioned": "YES",
    "airline_motive": "TECHNICAL",
    "incident_description": "Flight departed 5 hours late; missed onward connection."
  },
  "gdpr_consent": true
}
```

**Serializer choices** (what the API accepts):

| field | accepted values |
|---|---|
| `disruption_type` | `"CANCELLATION"`, `"DELAY"`, `"DENIED_BOARDING"` — **`"UNSPECIFIED"` is rejected.** |
| `cancellation_notice` | `"MORE_THAN_14_DAYS"`, `"LESS_THAN_14_DAYS"`, `"ON_FLIGHT_DAY"` |
| `delay_duration` | `"LESS_THAN_3H"`, `"MORE_THAN_3H"`, `"CONNECTION_LOST"` |
| `denied_boarding_voluntary` | `"YES"`, `"NO"` (string). Serializer converts to `bool` for the model. |
| `denied_boarding_reason` | `"OVERBOOKED"`, `"AGGRESSIVE_BEHAVIOR"`, `"INTOXICATION"`, `"UNSPECIFIED"` |
| `airline_motive_mentioned` | `"YES"`, `"NO"`, `"DONT_KNOW"` |
| `airline_motive` | `"TECHNICAL"`, `"WEATHER"`, `"STRIKE"`, `"AIRPORT_ISSUE"`, `"CREW"`, `"OTHER"` |
| `incident_description` | string, 1–2000 chars after strip |

**Cross-branch contamination** — fields not applicable to the chosen `disruption_type` must be absent or `null`. Sending an unrelated non-null value returns 400. Example: `{"disruption_type": "CANCELLATION", "delay_duration": "MORE_THAN_3H", ...}` → `{"disruption": {"delay_duration": ["Not applicable for disruption_type 'CANCELLATION'."]}}`.

### `POST /api/cases/` — extended 201 response

```json
{
  "id": "…",
  "status": "NEW",
  "created_at": "…",
  "distance_km": "…",
  "compensation_amount_eur": 400,
  "compensation_error": null,
  "disruption": {
    "disruption_type": "DELAY",
    "cancellation_notice": null,
    "delay_duration": "MORE_THAN_3H",
    "denied_boarding_voluntary": null,
    "denied_boarding_reason": null,
    "airline_motive_mentioned": "YES",
    "airline_motive": "TECHNICAL",
    "incident_description": "Flight departed 5 hours late; missed onward connection."
  }
}
```

`denied_boarding_voluntary` is serialised back as **`"YES"` / `"NO"` / `null`** — symmetric with the request shape.

### `POST /api/cases/` — 400 error shapes

- Missing block: `{"payload": {"disruption": ["This field is required."]}}`.
- Missing required sub-field: `{"payload": {"disruption": {"cancellation_notice": ["This field is required."]}}}`.
- Unknown enum value: `{"payload": {"disruption": {"disruption_type": ["\"FOO\" is not a valid choice."]}}}`.
- Cross-branch contamination: see example above.
- Description too long / empty: `{"payload": {"disruption": {"incident_description": ["Ensure this field has no more than 2000 characters."]}}}` or `["This field may not be blank."]`.

### No other endpoints

- `POST /api/compensation/preview/` — **unchanged**. Disruption is never sent to it.
- `GET /api/airports/` — unchanged.

---

## 5. Frontend

### New constants module — `frontend/src/features/case-entry/disruption.ts`

```typescript
export const DISRUPTION_TYPES = ["CANCELLATION", "DELAY", "DENIED_BOARDING"] as const;
export type DisruptionType = typeof DISRUPTION_TYPES[number];

export const CANCELLATION_NOTICES = [
  "MORE_THAN_14_DAYS", "LESS_THAN_14_DAYS", "ON_FLIGHT_DAY",
] as const;
export const DELAY_DURATIONS = [
  "LESS_THAN_3H", "MORE_THAN_3H", "CONNECTION_LOST",
] as const;
export const DENIED_BOARDING_REASONS = [
  "OVERBOOKED", "AGGRESSIVE_BEHAVIOR", "INTOXICATION", "UNSPECIFIED",
] as const;
export const MOTIVE_MENTIONED = ["YES", "NO", "DONT_KNOW"] as const;
export const AIRLINE_MOTIVES = [
  "TECHNICAL", "WEATHER", "STRIKE", "AIRPORT_ISSUE", "CREW", "OTHER",
] as const;

// Label maps (English) keyed by the enum literal — used only for rendering.
export const LABELS = {
  disruption_type: {
    CANCELLATION: "Cancellation",
    DELAY: "Delay",
    DENIED_BOARDING: "Denied boarding",
  },
  cancellation_notice: {
    MORE_THAN_14_DAYS: "More than 14 days before",
    LESS_THAN_14_DAYS: "Less than 14 days before",
    ON_FLIGHT_DAY: "On the flight day",
  },
  // ... one map per field
} as const;

export const DESCRIPTION_MAX_LENGTH = 2000;
```

### Zod schema addition — `frontend/src/features/case-entry/schema.ts`

Add a `z.discriminatedUnion` on `disruption_type`; then merge into `caseFormSchema`:

```typescript
const descField = z
  .string()
  .trim()
  .min(1, "Required.")
  .max(DESCRIPTION_MAX_LENGTH, `Description must be ${DESCRIPTION_MAX_LENGTH} characters or fewer.`);

const cancellationBranch = z.object({
  disruption_type: z.literal("CANCELLATION"),
  cancellation_notice: z.enum(CANCELLATION_NOTICES),
  airline_motive_mentioned: z.enum(MOTIVE_MENTIONED),
  airline_motive: z.enum(AIRLINE_MOTIVES).nullable(),
  incident_description: descField,
}).refine(
  (v) => v.airline_motive_mentioned !== "YES" || v.airline_motive !== null,
  { path: ["airline_motive"], message: "Required." },
);

const delayBranch = /* mirror of cancellationBranch with delay_duration */;

const deniedBoardingBranch = z.object({
  disruption_type: z.literal("DENIED_BOARDING"),
  denied_boarding_voluntary: z.enum(["YES", "NO"]),
  denied_boarding_reason: z.enum(DENIED_BOARDING_REASONS).nullable(),
  incident_description: descField,
}).refine(
  (v) => v.denied_boarding_voluntary !== "NO" || v.denied_boarding_reason !== null,
  { path: ["denied_boarding_reason"], message: "Required." },
);

export const disruptionSchema = z.discriminatedUnion("disruption_type", [
  cancellationBranch, delayBranch, deniedBoardingBranch,
]);
```

Merged into `caseFormSchema` as a required top-level `disruption` field.

**Initial form values** — RHF `defaultValues.disruption` = `{ disruption_type: "" as any, incident_description: "" }`. Zod fails validation on the empty discriminator until the user picks a type; the section shows only the type dropdown initially.

### New section — `sections/DisruptionSection.tsx`

- Header: "Disruption information".
- Always-rendered: `disruption_type` dropdown; disabled placeholder option `"Select a disruption type…"`.
- Uses `useWatch({ name: "disruption.disruption_type" })` to drive conditional field rendering:
  - `CANCELLATION` block → `cancellation_notice` dropdown + shared motive block.
  - `DELAY` block → `delay_duration` dropdown + shared motive block.
  - `DENIED_BOARDING` block → `denied_boarding_voluntary` radio group; when `"NO"`, `denied_boarding_reason` dropdown appears.
- Shared motive block (rendered inside `CANCELLATION` and `DELAY` branches): `airline_motive_mentioned` dropdown; when `"YES"`, `airline_motive` dropdown appears.
- Always-rendered when a `disruption_type` is picked: `incident_description` textarea with `n / 2000` live counter (uses `useWatch` on the same field).
- All labels come from `disruption.ts` `LABELS`. Error rendering follows the existing `sections.module.css` `.fieldError` pattern.

**Field-reset behaviour on `disruption_type` change** — the section uses a `useEffect` on the watched `disruption_type` that calls `resetField("disruption")` **preserving the newly-picked type** so that fields from a previously-selected branch don't leak (e.g. user picks DELAY, fills `delay_duration`, then switches to CANCELLATION → `delay_duration` is cleared before Zod re-runs). This keeps the submitted payload clean and avoids the cross-branch-contamination 400.

### Form wiring — `frontend/src/features/case-entry/CaseEntryForm.tsx`

Insert `<DisruptionSection />` **after** `<ConnectingFlightsSection />` and **before** `<PassengerDetailsSection />`. No other change to the file.

### API client — `frontend/src/api/cases.ts`

No signature change: the existing `createCase(payload, files)` already accepts any `CasePayload`. Extend the `CasePayload` type in `types.ts` to include the `disruption` object, and extend `CaseCreateResponse` to include the returned `disruption` block. That's the entire diff to the API client layer.

---

## 6. Error Handling

- **Serializer validation errors** — surfaced field-by-field via DRF's standard 400 shape. The frontend already handles `payload` nesting (see CASE_01 error mapping); disruption keys flow through unchanged.
- **Cross-branch contamination** — treated as a 400 (not silently stripped) so a mismatched client is caught early. The frontend's own `resetField` on `disruption_type` change prevents this from happening in practice for our UI.
- **Description over 2000 chars** — Zod blocks submit before the request goes out; the backend enforces the same cap as a defence-in-depth measure.
- **No new runtime failure modes.** Disruption fields never call out to external services (unlike CASE_02's Airport Gap). There is no fallback logic and no `disruption_error` field on the response.

---

## 7. Testing

### Backend (pytest)

- **`test_disruption_serializer.py` (new)** — table-driven cases covering every branch of the conditional-required matrix, including:
  - Valid `CANCELLATION` payload with `airline_motive_mentioned == "YES"` and with `"NO"` and with `"DONT_KNOW"`.
  - Valid `DELAY` payload — same three motive variants.
  - Valid `DENIED_BOARDING` payload with `voluntary == "YES"` (reason omitted) and with `"NO"` + each reason.
  - Missing required sub-field per type → 400.
  - Cross-branch contamination per type → 400.
  - `disruption_type == "UNSPECIFIED"` → 400 (not in serializer choices).
  - `incident_description` empty / whitespace-only / 2001 chars → 400.
  - `airline_motive_mentioned == "YES"` without `airline_motive` → 400.
  - `voluntary == "NO"` without `denied_boarding_reason` → 400.

- **`test_api.py` (extended)** — end-to-end multipart `POST /api/cases/`:
  - 201 for one payload per disruption type; response `disruption` block round-trips exactly.
  - 400 when `disruption` key is missing entirely.
  - Existing CASE_01/CASE_02 assertions unchanged.
  - Assert the persisted `Case` row has the correct 8 columns populated.

- **`factories.py` (extended)** — `CaseFactory` gains disruption defaults (`DELAY` + `MORE_THAN_3H` + `DONT_KNOW` + description). All existing CASE_01/CASE_02 test files keep passing without edits.

### Frontend (Vitest + RTL)

- **`DisruptionSection.test.tsx` (new)** —
  - Renders only the type dropdown initially.
  - Picking `CANCELLATION` reveals `cancellation_notice`, `airline_motive_mentioned`, description; **not** `delay_duration` or denied-boarding fields.
  - Picking `DELAY` reveals `delay_duration` and motive block.
  - Picking `DENIED_BOARDING` reveals voluntary radios; picking `"NO"` reveals reason dropdown.
  - Switching from `DELAY` to `CANCELLATION` clears `delay_duration`.
  - `airline_motive` field appears only when `airline_motive_mentioned == "YES"`.
  - Description counter renders `n / 2000` and updates on input.
  - Zod error appears when submitting with a picked type but missing sub-field.

- **`CaseEntryForm.test.tsx` (extended)** — the existing happy-path test now fills the disruption block; the submitted payload assertion is extended to include the nested `disruption` object.

### Coverage target

Every conditional-required rule from §3 invariants list must have at least one negative test (rule violated → 400) and one positive test (rule satisfied → 201) on the backend.

---

## 8. Migration & Rollout Notes

- Migration `0003_disruption_fields.py` is safely applied on the shared dev DB because `disruption_type` and `incident_description` come with backfill defaults, then the defaults are dropped.
- No data cleanup needed post-deploy.
- No feature flag: CASE_03 is either fully live or the migration hasn't run. There is no half-state where the API accepts a case without disruption.
- Rolling back: `python manage.py migrate cases 0002` drops the 8 columns and the check constraint. No CASE_01/CASE_02 data is affected.

---

## 9. Open Questions

None at spec-approval time. All conditional-required rules, enum value sets, storage decisions, and section placement were confirmed during brainstorming (see conversation record for 2026-07-24).
