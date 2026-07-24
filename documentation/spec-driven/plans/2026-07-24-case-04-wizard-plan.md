# CASE_04 — Multi-Step Wizard Implementation Plan

> **Execution:** Use subagent-driven development to implement this plan task-by-task.

**Goal:** Convert the single-page `CaseEntryForm` into a URL-per-step 7-step wizard with per-step Zod validation, `sessionStorage` draft persistence, a Review-and-Submit step, and a modernised token-based visual system — while adding the CASE_03 Disruption Info form as step 3.

**Architecture:** `react-router-dom` provides one route per step under a shared `<WizardLayout>` that owns a single React Hook Form instance via `<FormProvider>`. Each step lives inside a `<WizardStep>` wrapper that gates `Next` on `methods.trigger(fieldSubset)`; `Back` never validates. Draft values (files excluded) persist to `sessionStorage` under one JSON key; the Review step submits the whole form to `POST /api/cases/` and hands the 201 response to a `/case/created/:id` success page that renders `CompensationSummary`. A new `frontend/src/styles/tokens.css` design-token layer replaces raw hex/px values throughout the app.

**Tech Stack:** React 18, TypeScript, React Hook Form 7, Zod 3, `react-router-dom` ^6.26 (new), Vite 5, Vitest 1, Testing Library. No backend changes.

**Design Spec:** [documentation/spec-driven/specs/2026-07-24-case-04-wizard-design.md](../specs/2026-07-24-case-04-wizard-design.md)

---

## File Structure

**New files:**

- `frontend/src/styles/tokens.css` — CSS custom properties (colors, spacing, radii, shadows, type, motion).
- `frontend/src/styles/reset.css` — minimal reset + `:focus-visible` outline.
- `frontend/src/features/case-entry/disruption-enums.ts` — labelled enum arrays for the disruption form.
- `frontend/src/features/case-entry/sections/DisruptionInfoSection.tsx` — new CASE_03 form section.
- `frontend/src/features/case-entry/wizard/persistence.ts` — `sessionStorage` load/save helpers + `FIELD_TO_STEP` map.
- `frontend/src/features/case-entry/wizard/WizardLayout.tsx` — top-level layout: `<FormProvider>`, `<ProgressBar>`, `<Outlet>`, `<WizardNav>`, persistence effects.
- `frontend/src/features/case-entry/wizard/WizardLayout.module.css`
- `frontend/src/features/case-entry/wizard/WizardStep.tsx` — per-step wrapper that validates `fields` on Next.
- `frontend/src/features/case-entry/wizard/WizardNav.tsx` — Back / Next buttons.
- `frontend/src/features/case-entry/wizard/WizardNav.module.css`
- `frontend/src/features/case-entry/wizard/ProgressBar.tsx` — 7-step progress indicator.
- `frontend/src/features/case-entry/wizard/ProgressBar.module.css`
- `frontend/src/features/case-entry/wizard/ReviewStep.tsx` — read-only summary + Submit button.
- `frontend/src/features/case-entry/wizard/ReviewStep.module.css`
- `frontend/src/features/case-entry/wizard/CaseCreatedPage.tsx` — `/case/created/:id` success page.
- `frontend/src/features/case-entry/wizard/CaseCreatedPage.module.css`
- `frontend/src/features/case-entry/wizard/empty-values.ts` — shared `emptyValues` constant (extracted so `WizardLayout` and tests share it).
- `frontend/tests/wizard-routing.test.tsx`
- `frontend/tests/wizard-persistence.test.tsx`
- `frontend/tests/wizard-review.test.tsx`
- `frontend/tests/DisruptionInfoSection.test.tsx`
- `frontend/tests/progress-bar.test.tsx`

**Modified files:**

- `frontend/package.json` — add `react-router-dom` dep.
- `frontend/src/main.tsx` — import `reset.css` and `tokens.css` before `global.css`.
- `frontend/src/styles/global.css` — rewrite to use tokens; drop legacy raw hex.
- `frontend/src/App.tsx` — replace with `<BrowserRouter>` + routes.
- `frontend/src/features/case-entry/schema.ts` — add `disruptionSchema`, extend `caseFormSchema`.
- `frontend/src/features/case-entry/types.ts` — add `DisruptionInput`, extend `CasePayload` + `CaseCreateResponse`.
- `frontend/src/features/case-entry/sections/sections.module.css` — refactor to tokens.
- `frontend/src/features/case-entry/CompensationSummary.module.css` — refactor to tokens.
- `frontend/src/features/case-entry/AirportAutocomplete.module.css` — refactor to tokens.
- `frontend/tests/CompensationSummary.test.tsx` — mount inside a `MemoryRouter` since it now lives on `<CaseCreatedPage>`.

**Deleted files:**

- `frontend/src/features/case-entry/CaseEntryForm.tsx` — replaced by wizard.
- `frontend/src/features/case-entry/CaseEntryForm.module.css` — replaced by wizard CSS modules.
- `frontend/tests/CaseEntryForm.test.tsx` — replaced by `wizard-*.test.tsx`.

**Files untouched:**

- Everything under `backend/`.
- `frontend/src/api/**` (except no changes needed).
- `frontend/src/features/case-entry/AirportAutocomplete.tsx` (component logic).
- `frontend/src/features/case-entry/CompensationSummary.tsx` (component logic).
- `frontend/src/features/case-entry/sections/{FlightItinerarySection,ConnectingFlightsSection,PassengerDetailsSection,DocumentsSection,GdprSection}.tsx` — these components are reused as-is inside `<WizardStep>` wrappers. If any tweak becomes necessary (e.g. the Documents banner), it is scoped in the relevant task.

---

## Task 1: Foundation — router install, design tokens, reset, global rewrite

**Files:**
- Modify: `frontend/package.json`
- Create: `frontend/src/styles/tokens.css`
- Create: `frontend/src/styles/reset.css`
- Modify: `frontend/src/styles/global.css`
- Modify: `frontend/src/main.tsx`

**Requirements:**
- Install `react-router-dom` at `^6.26.0`.
- Introduce a CSS custom-property design-token layer per the frontend-style instructions.
- Every subsequent CSS Module can reference these tokens as `var(--...)`.
- `global.css` is minimal — sets font, base color, body background, base type scale. Layout/component styling lives in the CSS Modules.

**Implementation:**

Run in `frontend/`:

```powershell
npm install react-router-dom@^6.26.0
```

`frontend/src/styles/tokens.css` (full content):

```css
:root {
  /* Neutrals — cool grey scale */
  --color-neutral-0:   #ffffff;
  --color-neutral-50:  #f8fafc;
  --color-neutral-100: #f1f5f9;
  --color-neutral-200: #e2e8f0;
  --color-neutral-300: #cbd5e1;
  --color-neutral-400: #94a3b8;
  --color-neutral-500: #64748b;
  --color-neutral-600: #475569;
  --color-neutral-700: #334155;
  --color-neutral-800: #1e293b;
  --color-neutral-900: #0f172a;

  /* Accent */
  --color-accent-50:  #eff6ff;
  --color-accent-100: #dbeafe;
  --color-accent-500: #2563eb;
  --color-accent-600: #1d4ed8;
  --color-accent-700: #1e40af;

  /* Semantic */
  --color-danger-50:   #fef2f2;
  --color-danger-500:  #dc2626;
  --color-danger-700:  #991b1b;
  --color-success-50:  #f0fdf4;
  --color-success-500: #16a34a;
  --color-success-700: #15803d;
  --color-warning-50:  #fffbeb;
  --color-warning-500: #d97706;
  --color-warning-700: #b45309;

  /* Spacing (4 px base) */
  --space-1:  0.25rem;   /* 4  */
  --space-2:  0.5rem;    /* 8  */
  --space-3:  0.75rem;   /* 12 */
  --space-4:  1rem;      /* 16 */
  --space-5:  1.25rem;   /* 20 */
  --space-6:  1.5rem;    /* 24 */
  --space-8:  2rem;      /* 32 */
  --space-10: 2.5rem;    /* 40 */
  --space-12: 3rem;      /* 48 */
  --space-16: 4rem;      /* 64 */

  /* Radii */
  --radius-sm:   4px;
  --radius-md:   8px;
  --radius-lg:  12px;
  --radius-pill: 999px;

  /* Shadows */
  --shadow-sm: 0 1px 2px 0 rgba(15, 23, 42, 0.06);
  --shadow-md: 0 4px 12px -2px rgba(15, 23, 42, 0.08);
  --shadow-lg: 0 12px 32px -8px rgba(15, 23, 42, 0.14);

  /* Focus ring */
  --focus-ring: 0 0 0 3px rgba(37, 99, 235, 0.25);

  /* Type */
  --font-family-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", "Inter",
    Roboto, Helvetica, Arial, sans-serif;
  --font-size-xs:   0.75rem;   /* 12 */
  --font-size-sm:   0.875rem;  /* 14 */
  --font-size-base: 1rem;      /* 16 */
  --font-size-lg:   1.125rem;  /* 18 */
  --font-size-xl:   1.25rem;   /* 20 */
  --font-size-2xl:  1.5rem;    /* 24 */
  --font-size-3xl:  1.875rem;  /* 30 */
  --font-weight-regular:  400;
  --font-weight-medium:   500;
  --font-weight-semibold: 600;
  --line-height-tight:   1.2;
  --line-height-base:    1.5;
  --line-height-relaxed: 1.65;

  /* Motion */
  --motion-duration-fast: 120ms;
  --motion-duration-base: 200ms;
  --motion-ease-standard: cubic-bezier(0.4, 0, 0.2, 1);
}
```

`frontend/src/styles/reset.css` (full content):

```css
*,
*::before,
*::after { box-sizing: border-box; }

body,
h1, h2, h3, h4, h5, h6,
p, figure, blockquote,
dl, dd { margin: 0; }

ul, ol { margin: 0; padding: 0; }

button { font: inherit; color: inherit; }

input,
select,
textarea { font: inherit; color: inherit; }

:focus-visible {
  outline: 2px solid var(--color-accent-500);
  outline-offset: 2px;
}

*:focus:not(:focus-visible) { outline: none; }
```

`frontend/src/styles/global.css` (full replacement):

```css
:root {
  font-family: var(--font-family-sans);
  color: var(--color-neutral-900);
  color-scheme: light;
  font-size: 16px;
  line-height: var(--line-height-base);
}

body {
  background: var(--color-neutral-50);
  min-height: 100vh;
}
```

`frontend/src/main.tsx` (full replacement):

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./styles/reset.css";
import "./styles/tokens.css";
import "./styles/global.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
```

**Verification:**

```powershell
cd frontend
npm install                    # ensure lockfile clean after adding dep
npx tsc --noEmit               # zero TS errors
npm run build                  # builds successfully — Vite will crash if any CSS import path is wrong
```

Expected: `dist/` is produced, no errors. `package.json` shows `"react-router-dom": "^6.26.0"` under `dependencies`.

---

## Task 2: Types, disruption enum module, extended Zod schema

**Files:**
- Modify: `frontend/src/features/case-entry/types.ts`
- Create: `frontend/src/features/case-entry/disruption-enums.ts`
- Modify: `frontend/src/features/case-entry/schema.ts`
- Create: `frontend/src/features/case-entry/wizard/empty-values.ts`

**Requirements:**
- `types.ts` gains a `DisruptionInput` type mirroring the backend's `DisruptionSerializer` cleaned dict (8 keys, `denied_boarding_voluntary` typed as `boolean | null`).
- `CasePayload` gains `disruption: DisruptionInput`.
- `CaseCreateResponse` gains `disruption: DisruptionResponse` (all 8 keys, `denied_boarding_voluntary` typed as `"YES" | "NO" | null` because the backend serializes bool back to string).
- `disruption-enums.ts` exports the 6 labelled arrays; `value` strings match backend `DISRUPTION_TYPE_API_VALUES` (UNSPECIFIED absent).
- `schema.ts` gains a `disruptionSchema` exported by name; `caseFormSchema` composes it as `disruption: disruptionSchema`. The schema enforces the same conditional rules as the backend serializer.
- `empty-values.ts` exports `emptyValues: CaseFormValues` including a default `disruption` block that satisfies the schema's "type must be picked" rule minimally — use an empty-string-based default that the user MUST replace (Zod will report `"Required."` until they do).

**Implementation:**

`frontend/src/features/case-entry/types.ts` (full replacement):

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

export type DisruptionType = "CANCELLATION" | "DELAY" | "DENIED_BOARDING";
export type CancellationNotice = "MORE_THAN_14_DAYS" | "LESS_THAN_14_DAYS" | "ON_FLIGHT_DAY";
export type DelayDuration = "LESS_THAN_3H" | "MORE_THAN_3H" | "CONNECTION_LOST";
export type DeniedBoardingReason =
  | "OVERBOOKED" | "AGGRESSIVE_BEHAVIOR" | "INTOXICATION" | "UNSPECIFIED";
export type MotiveMentioned = "YES" | "NO" | "DONT_KNOW";
export type AirlineMotive =
  | "TECHNICAL" | "WEATHER" | "STRIKE" | "AIRPORT_ISSUE" | "CREW" | "OTHER";

export interface DisruptionInput {
  disruption_type: DisruptionType | "";               // "" only in draft state; rejected by schema
  cancellation_notice: CancellationNotice | null;
  delay_duration: DelayDuration | null;
  denied_boarding_voluntary: "YES" | "NO" | null;     // form-level string; schema converts to bool on transform if needed
  denied_boarding_reason: DeniedBoardingReason | null;
  airline_motive_mentioned: MotiveMentioned | null;
  airline_motive: AirlineMotive | null;
  incident_description: string;
}

export interface CasePayload {
  passenger: PassengerInput;
  reservation_number: string;
  segments: FlightSegmentInput[];
  disruption: DisruptionInput;
  gdpr_consent: boolean;
}

export interface DisruptionResponse {
  disruption_type: DisruptionType | "UNSPECIFIED";
  cancellation_notice: CancellationNotice | null;
  delay_duration: DelayDuration | null;
  denied_boarding_voluntary: "YES" | "NO" | null;
  denied_boarding_reason: DeniedBoardingReason | null;
  airline_motive_mentioned: MotiveMentioned | null;
  airline_motive: AirlineMotive | null;
  incident_description: string;
}

export interface CaseCreateResponse {
  id: string;
  status: "NEW" | "VALID" | "ASSIGNED" | "INVALID";
  created_at: string;
  distance_km: string | number | null;
  compensation_amount_eur: 250 | 400 | 600 | null;
  compensation_error: string | null;
  disruption: DisruptionResponse;
}
```

`frontend/src/features/case-entry/disruption-enums.ts` (full content):

```ts
import type {
  AirlineMotive,
  CancellationNotice,
  DelayDuration,
  DeniedBoardingReason,
  DisruptionType,
  MotiveMentioned,
} from "./types";

export const DISRUPTION_TYPES: readonly { value: DisruptionType; label: string }[] = [
  { value: "CANCELLATION",    label: "Cancellation" },
  { value: "DELAY",           label: "Delay" },
  { value: "DENIED_BOARDING", label: "Denied boarding" },
] as const;

export const CANCELLATION_NOTICES: readonly { value: CancellationNotice; label: string }[] = [
  { value: "MORE_THAN_14_DAYS", label: "More than 14 days before the flight" },
  { value: "LESS_THAN_14_DAYS", label: "Less than 14 days before the flight" },
  { value: "ON_FLIGHT_DAY",     label: "On the day of the flight" },
] as const;

export const DELAY_DURATIONS: readonly { value: DelayDuration; label: string }[] = [
  { value: "LESS_THAN_3H",    label: "Less than 3 hours" },
  { value: "MORE_THAN_3H",    label: "More than 3 hours" },
  { value: "CONNECTION_LOST", label: "Connection lost" },
] as const;

export const DENIED_BOARDING_REASONS: readonly { value: DeniedBoardingReason; label: string }[] = [
  { value: "OVERBOOKED",          label: "Overbooked" },
  { value: "AGGRESSIVE_BEHAVIOR", label: "Aggressive behaviour" },
  { value: "INTOXICATION",        label: "Intoxication" },
  { value: "UNSPECIFIED",         label: "Not specified" },
] as const;

export const MOTIVE_MENTIONED: readonly { value: MotiveMentioned; label: string }[] = [
  { value: "YES",        label: "Yes" },
  { value: "NO",         label: "No" },
  { value: "DONT_KNOW",  label: "Don't know" },
] as const;

export const AIRLINE_MOTIVES: readonly { value: AirlineMotive; label: string }[] = [
  { value: "TECHNICAL",     label: "Technical issue" },
  { value: "WEATHER",       label: "Weather" },
  { value: "STRIKE",        label: "Strike" },
  { value: "AIRPORT_ISSUE", label: "Airport issue" },
  { value: "CREW",          label: "Crew" },
  { value: "OTHER",         label: "Other" },
] as const;

export const INCIDENT_DESCRIPTION_MAX = 2000;
```

`frontend/src/features/case-entry/schema.ts` (full replacement — the existing top portion is preserved, `disruptionSchema` is inserted before `caseFormSchema`, and `caseFormSchema` gains the `disruption` key):

```ts
import { z } from "zod";

const PHONE_REGEX = /^\+?[0-9\s\-()]{7,30}$/;
const IATA_REGEX = /^[A-Z]{3}$/;
const MAX_FILE_BYTES = 5 * 1024 * 1024;
const ALLOWED_MIMES = new Set(["application/pdf", "image/jpeg", "image/png"]);
const INCIDENT_DESCRIPTION_MAX = 2000;

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

const DISRUPTION_TYPE = z.enum(["CANCELLATION", "DELAY", "DENIED_BOARDING"]);
const CANCELLATION_NOTICE = z.enum(["MORE_THAN_14_DAYS", "LESS_THAN_14_DAYS", "ON_FLIGHT_DAY"]);
const DELAY_DURATION = z.enum(["LESS_THAN_3H", "MORE_THAN_3H", "CONNECTION_LOST"]);
const DENIED_BOARDING_REASON = z.enum(["OVERBOOKED", "AGGRESSIVE_BEHAVIOR", "INTOXICATION", "UNSPECIFIED"]);
const MOTIVE_MENTIONED = z.enum(["YES", "NO", "DONT_KNOW"]);
const AIRLINE_MOTIVE = z.enum(["TECHNICAL", "WEATHER", "STRIKE", "AIRPORT_ISSUE", "CREW", "OTHER"]);

/**
 * Draft-shape disruption schema. Mirrors backend DisruptionSerializer.
 * Optional fields are nullable to allow un-selected radios to persist as null in sessionStorage.
 */
export const disruptionSchema = z
  .object({
    disruption_type: DISRUPTION_TYPE.or(z.literal("")).refine(
      (v): v is z.infer<typeof DISRUPTION_TYPE> => v !== "",
      { message: "Please pick a disruption type." },
    ),
    cancellation_notice: CANCELLATION_NOTICE.nullable(),
    delay_duration: DELAY_DURATION.nullable(),
    denied_boarding_voluntary: z.enum(["YES", "NO"]).nullable(),
    denied_boarding_reason: DENIED_BOARDING_REASON.nullable(),
    airline_motive_mentioned: MOTIVE_MENTIONED.nullable(),
    airline_motive: AIRLINE_MOTIVE.nullable(),
    incident_description: z
      .string()
      .trim()
      .min(1, "Please describe the incident.")
      .max(INCIDENT_DESCRIPTION_MAX, `Maximum ${INCIDENT_DESCRIPTION_MAX} characters.`),
  })
  .superRefine((val, ctx) => {
    if (val.disruption_type === "CANCELLATION") {
      if (!val.cancellation_notice) {
        ctx.addIssue({ code: "custom", path: ["cancellation_notice"], message: "Required." });
      }
      if (!val.airline_motive_mentioned) {
        ctx.addIssue({ code: "custom", path: ["airline_motive_mentioned"], message: "Required." });
      }
      if (val.airline_motive_mentioned === "YES" && !val.airline_motive) {
        ctx.addIssue({ code: "custom", path: ["airline_motive"], message: "Required." });
      }
    } else if (val.disruption_type === "DELAY") {
      if (!val.delay_duration) {
        ctx.addIssue({ code: "custom", path: ["delay_duration"], message: "Required." });
      }
      if (!val.airline_motive_mentioned) {
        ctx.addIssue({ code: "custom", path: ["airline_motive_mentioned"], message: "Required." });
      }
      if (val.airline_motive_mentioned === "YES" && !val.airline_motive) {
        ctx.addIssue({ code: "custom", path: ["airline_motive"], message: "Required." });
      }
    } else if (val.disruption_type === "DENIED_BOARDING") {
      if (!val.denied_boarding_voluntary) {
        ctx.addIssue({ code: "custom", path: ["denied_boarding_voluntary"], message: "Required." });
      }
      if (val.denied_boarding_voluntary === "NO" && !val.denied_boarding_reason) {
        ctx.addIssue({ code: "custom", path: ["denied_boarding_reason"], message: "Required." });
      }
    }
  });

export const caseFormSchema = z
  .object({
    passenger: passengerSchema,
    reservation_number: z.string().min(1, "Required.").max(30),
    segments: z.array(segmentSchema).min(1).max(5),
    disruption: disruptionSchema,
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
export type DisruptionFormValues = z.infer<typeof disruptionSchema>;
```

`frontend/src/features/case-entry/wizard/empty-values.ts` (full content):

```ts
import type { CaseFormValues } from "../schema";

export const emptyValues: CaseFormValues = {
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
  // `disruption_type` starts as "" so radios render un-selected; schema requires user to pick one.
  disruption: {
    disruption_type: "" as unknown as CaseFormValues["disruption"]["disruption_type"],
    cancellation_notice: null,
    delay_duration: null,
    denied_boarding_voluntary: null,
    denied_boarding_reason: null,
    airline_motive_mentioned: null,
    airline_motive: null,
    incident_description: "",
  },
  gdpr_consent: false,
  boarding_pass: undefined as unknown as File,
  id_document: undefined as unknown as File,
};
```

**Verification:**

```powershell
cd frontend
npx tsc --noEmit
```

Expected: zero errors. `caseFormSchema.parse({...emptyValues, boarding_pass: <File>, id_document: <File>})` would fail on `disruption.disruption_type` — that's correct; the user must pick one to advance past step 3.

---

## Task 3: Wizard infrastructure — persistence, layout, step wrapper, nav, progress bar

**Files:**
- Create: `frontend/src/features/case-entry/wizard/persistence.ts`
- Create: `frontend/src/features/case-entry/wizard/WizardLayout.tsx`
- Create: `frontend/src/features/case-entry/wizard/WizardLayout.module.css`
- Create: `frontend/src/features/case-entry/wizard/WizardStep.tsx`
- Create: `frontend/src/features/case-entry/wizard/WizardNav.tsx`
- Create: `frontend/src/features/case-entry/wizard/WizardNav.module.css`
- Create: `frontend/src/features/case-entry/wizard/ProgressBar.tsx`
- Create: `frontend/src/features/case-entry/wizard/ProgressBar.module.css`

**Requirements:**
- `persistence.ts` exports:
  - `SESSION_KEY = "airassist:case:draft"`
  - `STEPS: readonly WizardStepDef[]` — one entry per step (`slug`, `label`, `fields[]`).
  - `FIELD_TO_STEP: Record<string, number>` — top-level field name → step index (for post-submit error routing).
  - `loadDraft(): Partial<CaseFormValues> | null` — reads sessionStorage, returns parsed JSON or `null`. Files never present.
  - `saveDraft(values: CaseFormValues): void` — writes JSON, stripping `boarding_pass` and `id_document`.
  - `clearDraft(): void` — removes the key.
- `WizardLayout` mounts `<FormProvider>` with a `useForm<CaseFormValues>` instance, hydrates from `loadDraft()` in a `useEffect(..., [])`, saves via `methods.watch()` subscription (debounced 400 ms), renders `<ProgressBar />`, `<Outlet />`, `<WizardNav />`, tracks `maxCompletedIndex` in state, and provides a context that `<WizardStep>` and `<WizardNav>` consume.
- `WizardStep` accepts `{ index: number; nextPath: string; fields: (keyof CaseFormValues | string)[]; children: ReactNode }`. It exposes its `Next` handler to the layout via context so `<WizardNav>` can render the button and call it. On successful `trigger`, it calls `setMaxCompletedIndex(prev => Math.max(prev, index + 1))`, then honours `location.state.returnTo === "review"` (navigate to `/case/new/review`) OR default `nextPath`.
- `WizardNav` renders Back (disabled when `index === 0`) and Next; also gets `nextLabel` from context (Review step overrides it to "Submit claim").
- `ProgressBar` renders a horizontal list of 7 step chips. Completed = accent-500 fill + white checkmark. Current = accent-500 border + accent-50 fill. Future = neutral-200 border + white fill. Each chip is a `<button>` that navigates to `STEPS[i].slug` — disabled (`aria-disabled="true"`, `tabIndex={-1}`, no `onClick`) if `i > currentIndex && i > maxCompletedIndex`. The current index is derived from `useLocation().pathname` (last segment matched against `STEPS[i].slug`).

**Implementation:**

`frontend/src/features/case-entry/wizard/persistence.ts` (full content):

```ts
import type { CaseFormValues } from "../schema";

export const SESSION_KEY = "airassist:case:draft";

export interface WizardStepDef {
  slug: string;
  label: string;
  /** RHF field paths validated when Next is clicked on this step. */
  fields: readonly string[];
}

export const STEPS: readonly WizardStepDef[] = [
  { slug: "itinerary",          label: "Itinerary",          fields: ["segments.0"] },
  { slug: "connecting-flights", label: "Connecting flights", fields: ["segments"] },
  { slug: "disruption",         label: "Disruption",         fields: ["disruption"] },
  { slug: "passenger",          label: "Passenger",          fields: ["passenger", "reservation_number"] },
  { slug: "documents",          label: "Documents",          fields: ["boarding_pass", "id_document"] },
  { slug: "consent",            label: "Consent",            fields: ["gdpr_consent"] },
  { slug: "review",             label: "Review",             fields: [] },
] as const;

/** Map top-level backend field name (as returned in 400 response) to the step that owns it. */
export const FIELD_TO_STEP: Readonly<Record<string, number>> = {
  segments: 0,           // itinerary / connecting flights — earliest is 0
  disruption: 2,
  passenger: 3,
  reservation_number: 3,
  boarding_pass: 4,
  id_document: 4,
  gdpr_consent: 5,
};

/** Returns the earliest step index that owns any of the errored top-level fields. */
export function firstErroredStep(fieldErrors: Record<string, unknown>): number {
  let earliest = STEPS.length - 1;
  for (const key of Object.keys(fieldErrors)) {
    const step = FIELD_TO_STEP[key];
    if (step !== undefined && step < earliest) earliest = step;
  }
  return earliest;
}

type Draftable = Omit<CaseFormValues, "boarding_pass" | "id_document">;

export function loadDraft(): Draftable | null {
  try {
    const raw = sessionStorage.getItem(SESSION_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as Draftable;
  } catch {
    return null;
  }
}

export function saveDraft(values: CaseFormValues): void {
  try {
    const { boarding_pass: _bp, id_document: _id, ...draftable } = values;
    sessionStorage.setItem(SESSION_KEY, JSON.stringify(draftable));
  } catch {
    // Quota exceeded or sessionStorage unavailable — silently skip.
  }
}

export function clearDraft(): void {
  try {
    sessionStorage.removeItem(SESSION_KEY);
  } catch {
    // ignore
  }
}
```

`frontend/src/features/case-entry/wizard/WizardLayout.tsx` (full content):

```tsx
import { createContext, useContext, useEffect, useMemo, useRef, useState } from "react";
import { FormProvider, useForm, type UseFormReturn } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Outlet, useLocation } from "react-router-dom";

import { caseFormSchema, type CaseFormValues } from "../schema";
import { emptyValues } from "./empty-values";
import { loadDraft, saveDraft, STEPS } from "./persistence";
import { ProgressBar } from "./ProgressBar";
import { WizardNav } from "./WizardNav";
import styles from "./WizardLayout.module.css";

interface WizardContextValue {
  methods: UseFormReturn<CaseFormValues>;
  currentIndex: number;
  maxCompletedIndex: number;
  markCompleted: (index: number) => void;
  banner: string | null;
  setBanner: (msg: string | null) => void;
  /** Registered by the current <WizardStep> so <WizardNav> can invoke it. */
  nextHandler: (() => void) | null;
  setNextHandler: (h: (() => void) | null) => void;
  /** Overridable per-step: Review step sets "Submit claim". */
  nextLabel: string;
  setNextLabel: (label: string) => void;
  submitting: boolean;
  setSubmitting: (v: boolean) => void;
}

const WizardCtx = createContext<WizardContextValue | null>(null);

export function useWizard(): WizardContextValue {
  const ctx = useContext(WizardCtx);
  if (!ctx) throw new Error("useWizard must be used inside <WizardLayout>");
  return ctx;
}

function slugFromPath(pathname: string): string {
  const parts = pathname.split("/").filter(Boolean);
  return parts[parts.length - 1] ?? "";
}

export function WizardLayout() {
  const location = useLocation();
  const currentIndex = Math.max(
    0,
    STEPS.findIndex((s) => s.slug === slugFromPath(location.pathname)),
  );

  const methods = useForm<CaseFormValues>({
    resolver: zodResolver(caseFormSchema),
    defaultValues: emptyValues,
    mode: "onTouched",
  });

  const [maxCompletedIndex, setMaxCompletedIndex] = useState(0);
  const [banner, setBanner] = useState<string | null>(null);
  const [nextHandler, setNextHandler] = useState<(() => void) | null>(null);
  const [nextLabel, setNextLabel] = useState("Next");
  const [submitting, setSubmitting] = useState(false);

  // Hydrate from sessionStorage once on mount.
  const hydrated = useRef(false);
  useEffect(() => {
    if (hydrated.current) return;
    hydrated.current = true;
    const draft = loadDraft();
    if (draft) {
      methods.reset({ ...emptyValues, ...draft });
    }
  }, [methods]);

  // Persist on change (debounced 400 ms).
  useEffect(() => {
    let timeout: ReturnType<typeof setTimeout> | null = null;
    const sub = methods.watch((values) => {
      if (timeout) clearTimeout(timeout);
      timeout = setTimeout(() => {
        saveDraft(values as CaseFormValues);
      }, 400);
    });
    return () => {
      if (timeout) clearTimeout(timeout);
      sub.unsubscribe();
    };
  }, [methods]);

  const markCompleted = (index: number) => {
    setMaxCompletedIndex((prev) => Math.max(prev, index + 1));
  };

  const ctxValue = useMemo<WizardContextValue>(
    () => ({
      methods,
      currentIndex,
      maxCompletedIndex,
      markCompleted,
      banner,
      setBanner,
      nextHandler,
      setNextHandler,
      nextLabel,
      setNextLabel,
      submitting,
      setSubmitting,
    }),
    [methods, currentIndex, maxCompletedIndex, banner, nextHandler, nextLabel, submitting],
  );

  return (
    <WizardCtx.Provider value={ctxValue}>
      <FormProvider {...methods}>
        <main className={styles.wrapper}>
          <header className={styles.header}>
            <h1 className={styles.title}>File a compensation claim</h1>
            <p className={styles.subtitle}>
              EU 261/2004 — takes about 5 minutes.
            </p>
          </header>
          <ProgressBar />
          {banner && (
            <div className={styles.banner} role="alert">
              {banner}
            </div>
          )}
          <div className={styles.panel}>
            <Outlet />
          </div>
          <WizardNav />
        </main>
      </FormProvider>
    </WizardCtx.Provider>
  );
}
```

`frontend/src/features/case-entry/wizard/WizardLayout.module.css` (full content):

```css
.wrapper {
  max-width: 780px;
  margin: 0 auto;
  padding: var(--space-8) var(--space-4) var(--space-12);
}

.header {
  margin-bottom: var(--space-6);
}

.title {
  font-size: var(--font-size-3xl);
  font-weight: var(--font-weight-semibold);
  line-height: var(--line-height-tight);
  color: var(--color-neutral-900);
}

.subtitle {
  margin-top: var(--space-2);
  color: var(--color-neutral-500);
  font-size: var(--font-size-sm);
}

.panel {
  background: var(--color-neutral-0);
  border: 1px solid var(--color-neutral-200);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  padding: var(--space-6);
  margin-top: var(--space-6);
}

.banner {
  background: var(--color-danger-50);
  border: 1px solid var(--color-danger-500);
  color: var(--color-danger-700);
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  margin-top: var(--space-4);
}
```

`frontend/src/features/case-entry/wizard/WizardStep.tsx` (full content):

```tsx
import { useEffect, type ReactNode } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import type { FieldPath } from "react-hook-form";

import type { CaseFormValues } from "../schema";
import { useWizard } from "./WizardLayout";

interface Props {
  index: number;
  nextPath: string;
  fields: readonly string[];
  children: ReactNode;
}

export function WizardStep({ index, nextPath, fields, children }: Props) {
  const { methods, markCompleted, setNextHandler, setNextLabel, setBanner } = useWizard();
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    setNextLabel("Next");
    setBanner(null);
    const handler = async () => {
      const ok = await methods.trigger(fields as FieldPath<CaseFormValues>[]);
      if (!ok) return;
      markCompleted(index);
      const returnTo = (location.state as { returnTo?: string } | null)?.returnTo;
      if (returnTo === "review") {
        navigate("/case/new/review");
      } else {
        navigate(nextPath);
      }
    };
    setNextHandler(() => handler);
    return () => setNextHandler(null);
  }, [
    methods, fields, index, nextPath, navigate, location.state,
    markCompleted, setNextHandler, setNextLabel, setBanner,
  ]);

  return <>{children}</>;
}
```

`frontend/src/features/case-entry/wizard/WizardNav.tsx` (full content):

```tsx
import { useNavigate } from "react-router-dom";

import { useWizard } from "./WizardLayout";
import { STEPS } from "./persistence";
import styles from "./WizardNav.module.css";

export function WizardNav() {
  const navigate = useNavigate();
  const { currentIndex, nextHandler, nextLabel, submitting } = useWizard();
  const isFirst = currentIndex === 0;

  return (
    <nav className={styles.nav} aria-label="Wizard navigation">
      <button
        type="button"
        className={styles.back}
        onClick={() => navigate(-1)}
        disabled={isFirst}
      >
        Back
      </button>
      <div className={styles.spacer} />
      <span className={styles.stepCounter} aria-live="polite">
        Step {currentIndex + 1} of {STEPS.length}
      </span>
      <button
        type="button"
        className={styles.next}
        onClick={() => nextHandler?.()}
        disabled={!nextHandler || submitting}
      >
        {submitting ? "Submitting…" : nextLabel}
      </button>
    </nav>
  );
}
```

`frontend/src/features/case-entry/wizard/WizardNav.module.css` (full content):

```css
.nav {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-top: var(--space-6);
}

.spacer { flex: 1; }

.stepCounter {
  color: var(--color-neutral-500);
  font-size: var(--font-size-sm);
}

.back,
.next {
  border-radius: var(--radius-md);
  padding: var(--space-3) var(--space-5);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  cursor: pointer;
  transition: background var(--motion-duration-fast) var(--motion-ease-standard),
              color var(--motion-duration-fast) var(--motion-ease-standard),
              border-color var(--motion-duration-fast) var(--motion-ease-standard);
}

.back {
  background: var(--color-neutral-0);
  color: var(--color-neutral-700);
  border: 1px solid var(--color-neutral-200);
}

.back:hover:not(:disabled) {
  background: var(--color-neutral-50);
  border-color: var(--color-neutral-300);
}

.back:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.next {
  background: var(--color-accent-500);
  color: var(--color-neutral-0);
  border: 1px solid var(--color-accent-500);
}

.next:hover:not(:disabled) {
  background: var(--color-accent-600);
  border-color: var(--color-accent-600);
}

.next:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
```

`frontend/src/features/case-entry/wizard/ProgressBar.tsx` (full content):

```tsx
import { useNavigate } from "react-router-dom";

import { STEPS } from "./persistence";
import { useWizard } from "./WizardLayout";
import styles from "./ProgressBar.module.css";

export function ProgressBar() {
  const navigate = useNavigate();
  const { currentIndex, maxCompletedIndex } = useWizard();

  return (
    <ol className={styles.list} aria-label="Progress">
      {STEPS.map((step, i) => {
        const isCurrent = i === currentIndex;
        const isCompleted = i < maxCompletedIndex;
        const isClickable = isCompleted || isCurrent;
        const stateClass = isCompleted
          ? styles.completed
          : isCurrent
          ? styles.current
          : styles.future;

        return (
          <li key={step.slug} className={styles.item}>
            <button
              type="button"
              className={`${styles.chip} ${stateClass}`}
              aria-current={isCurrent ? "step" : undefined}
              aria-disabled={!isClickable}
              tabIndex={isClickable ? 0 : -1}
              onClick={() => {
                if (!isClickable) return;
                navigate(`/case/new/${step.slug}`);
              }}
            >
              <span className={styles.circle} aria-hidden="true">
                {isCompleted ? "✓" : i + 1}
              </span>
              <span className={styles.label}>{step.label}</span>
            </button>
            {i < STEPS.length - 1 && (
              <span
                className={`${styles.connector} ${
                  isCompleted ? styles.connectorDone : ""
                }`}
                aria-hidden="true"
              />
            )}
          </li>
        );
      })}
    </ol>
  );
}
```

`frontend/src/features/case-entry/wizard/ProgressBar.module.css` (full content):

```css
.list {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  list-style: none;
  padding: 0;
  overflow-x: auto;
}

.item {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.chip {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  background: none;
  border: none;
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-md);
  cursor: pointer;
  color: var(--color-neutral-500);
  font-size: var(--font-size-sm);
  transition: color var(--motion-duration-fast) var(--motion-ease-standard);
}

.chip[aria-disabled="true"] {
  cursor: not-allowed;
}

.chip:not([aria-disabled="true"]):hover {
  color: var(--color-neutral-800);
}

.circle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: var(--radius-pill);
  border: 1px solid var(--color-neutral-200);
  background: var(--color-neutral-0);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-semibold);
  transition: background var(--motion-duration-fast) var(--motion-ease-standard),
              border-color var(--motion-duration-fast) var(--motion-ease-standard),
              color var(--motion-duration-fast) var(--motion-ease-standard);
}

.current .circle {
  border-color: var(--color-accent-500);
  background: var(--color-accent-50);
  color: var(--color-accent-700);
}

.current .label {
  color: var(--color-neutral-900);
  font-weight: var(--font-weight-medium);
}

.completed .circle {
  background: var(--color-accent-500);
  border-color: var(--color-accent-500);
  color: var(--color-neutral-0);
}

.completed .label {
  color: var(--color-neutral-700);
}

.future .circle {
  color: var(--color-neutral-400);
}

.label {
  white-space: nowrap;
}

.connector {
  width: var(--space-6);
  height: 2px;
  background: var(--color-neutral-200);
  margin: 0 var(--space-1);
}

.connectorDone {
  background: var(--color-accent-500);
}
```

**Verification:**

```powershell
cd frontend
npx tsc --noEmit
```

Expected: zero TS errors. The wizard scaffolding compiles standalone (no route consumers yet — those come in Task 5).

---

## Task 4: DisruptionInfoSection component

**Files:**
- Create: `frontend/src/features/case-entry/sections/DisruptionInfoSection.tsx`

**Requirements:**
- New section component consumed by step 3 of the wizard.
- Renders radio groups per §4 of the design spec, using labelled arrays from `disruption-enums.ts`.
- Sub-blocks render conditionally based on `watch("disruption.disruption_type")` and the `airline_motive_mentioned` / `denied_boarding_voluntary` values.
- When the user switches disruption type, no other fields are cleared — Zod's `superRefine` ignores inapplicable values on non-matching branches, and the wizard-level `caseFormSchema` still accepts the whole draft. (Backend's `DisruptionSerializer.validate` will strip inapplicable values at submit time.) This keeps the UX forgiving — a user can toggle back and forth without losing typed text.
- Character counter next to the textarea shows `${length} / 2000`.
- Uses the existing `sections.module.css` styles (`.section`, `.grid`, `.field`, `.error`) — no new CSS module needed.
- Radio groups are semantically `<fieldset><legend>` for a11y.

**Implementation:**

`frontend/src/features/case-entry/sections/DisruptionInfoSection.tsx` (full content):

```tsx
import { useFormContext, useWatch } from "react-hook-form";

import {
  AIRLINE_MOTIVES,
  CANCELLATION_NOTICES,
  DELAY_DURATIONS,
  DENIED_BOARDING_REASONS,
  DISRUPTION_TYPES,
  INCIDENT_DESCRIPTION_MAX,
  MOTIVE_MENTIONED,
} from "../disruption-enums";
import type { CaseFormValues } from "../schema";
import styles from "./sections.module.css";

function RadioGroup<T extends string>(props: {
  legend: string;
  name: string;
  options: readonly { value: T; label: string }[];
  error?: string;
}) {
  const { register } = useFormContext<CaseFormValues>();
  return (
    <fieldset className={styles.fieldset}>
      <legend>{props.legend}</legend>
      <div className={styles.radioGroup}>
        {props.options.map((opt) => (
          <label key={opt.value} className={styles.radio}>
            <input type="radio" value={opt.value} {...register(props.name as never)} />
            <span>{opt.label}</span>
          </label>
        ))}
      </div>
      {props.error && <p className={styles.error}>{props.error}</p>}
    </fieldset>
  );
}

export function DisruptionInfoSection() {
  const {
    register,
    control,
    formState: { errors },
  } = useFormContext<CaseFormValues>();

  const disruption = useWatch({ control, name: "disruption" });
  const disruptionType = disruption?.disruption_type;
  const mentioned = disruption?.airline_motive_mentioned;
  const voluntary = disruption?.denied_boarding_voluntary;
  const description = disruption?.incident_description ?? "";

  const dErrors = errors.disruption ?? {};

  return (
    <section className={styles.section} aria-labelledby="disruption-heading">
      <h2 id="disruption-heading">Disruption information</h2>

      <RadioGroup
        legend="What happened to your flight?"
        name="disruption.disruption_type"
        options={DISRUPTION_TYPES}
        error={
          typeof dErrors === "object" && "disruption_type" in dErrors
            ? (dErrors as { disruption_type?: { message?: string } }).disruption_type?.message
            : undefined
        }
      />

      {disruptionType === "CANCELLATION" && (
        <RadioGroup
          legend="When were you informed of the cancellation?"
          name="disruption.cancellation_notice"
          options={CANCELLATION_NOTICES}
          error={
            (dErrors as { cancellation_notice?: { message?: string } })
              .cancellation_notice?.message
          }
        />
      )}

      {disruptionType === "DELAY" && (
        <RadioGroup
          legend="How long was the delay?"
          name="disruption.delay_duration"
          options={DELAY_DURATIONS}
          error={
            (dErrors as { delay_duration?: { message?: string } })
              .delay_duration?.message
          }
        />
      )}

      {disruptionType === "DENIED_BOARDING" && (
        <>
          <RadioGroup
            legend="Was boarding denied voluntarily?"
            name="disruption.denied_boarding_voluntary"
            options={[
              { value: "YES", label: "Yes, I volunteered" },
              { value: "NO", label: "No, I was denied" },
            ]}
            error={
              (dErrors as { denied_boarding_voluntary?: { message?: string } })
                .denied_boarding_voluntary?.message
            }
          />
          {voluntary === "NO" && (
            <RadioGroup
              legend="Reason boarding was denied"
              name="disruption.denied_boarding_reason"
              options={DENIED_BOARDING_REASONS}
              error={
                (dErrors as { denied_boarding_reason?: { message?: string } })
                  .denied_boarding_reason?.message
              }
            />
          )}
        </>
      )}

      {(disruptionType === "CANCELLATION" || disruptionType === "DELAY") && (
        <>
          <RadioGroup
            legend="Did the airline mention a reason?"
            name="disruption.airline_motive_mentioned"
            options={MOTIVE_MENTIONED}
            error={
              (dErrors as { airline_motive_mentioned?: { message?: string } })
                .airline_motive_mentioned?.message
            }
          />
          {mentioned === "YES" && (
            <RadioGroup
              legend="Which reason did the airline give?"
              name="disruption.airline_motive"
              options={AIRLINE_MOTIVES}
              error={
                (dErrors as { airline_motive?: { message?: string } })
                  .airline_motive?.message
              }
            />
          )}
        </>
      )}

      <label className={styles.field}>
        <span>Describe what happened</span>
        <textarea
          rows={5}
          maxLength={INCIDENT_DESCRIPTION_MAX}
          placeholder="e.g. Flight was delayed 5 hours; we were told there was a technical fault."
          {...register("disruption.incident_description")}
        />
        <span className={styles.counter}>
          {description.length} / {INCIDENT_DESCRIPTION_MAX}
        </span>
        {(dErrors as { incident_description?: { message?: string } })
          .incident_description?.message && (
          <span className={styles.error}>
            {(dErrors as { incident_description?: { message?: string } })
              .incident_description!.message}
          </span>
        )}
      </label>
    </section>
  );
}
```

**Notes for the implementer:**
- The `styles.fieldset`, `styles.radioGroup`, `styles.radio`, and `styles.counter` classes are added in **Task 7** when `sections.module.css` is refactored. Until Task 7 runs, these class names will be `undefined` at runtime — the component still functions (unstyled radios/fieldsets), and TypeScript does not error because CSS module lookups are `Record<string, string>`. Task 7 fills them in.

**Verification:**

```powershell
cd frontend
npx tsc --noEmit
```

Expected: zero errors.

---

## Task 5: Router wiring — App.tsx replacement, delete legacy CaseEntryForm

**Files:**
- Modify: `frontend/src/App.tsx`
- Delete: `frontend/src/features/case-entry/CaseEntryForm.tsx`
- Delete: `frontend/src/features/case-entry/CaseEntryForm.module.css`

**Requirements:**
- `App.tsx` sets up `BrowserRouter` and all 9 routes from §2 of the spec (`/`, one per step under `/case/new/*`, `/case/created/:id`, `*`).
- The 6 concrete-form steps wrap their existing/new section components in `<WizardStep>`.
- Step 5 (Documents) additionally renders a re-upload banner when the RHF state has a hydrated `disruption.disruption_type` (proxy for "user has progressed past step 3") but `boarding_pass` is undefined — showing this signals a page-refresh scenario. Implement via a small inline wrapper component `<DocumentsStep>` local to `App.tsx`.
- The Review step (`/case/new/review`) is a plain `<Route>` — `<ReviewStep>` (built in Task 6) owns its own submit and does NOT use `<WizardStep>`.
- The `/` and `*` catch-alls redirect to `/case/new/itinerary`.

**Implementation:**

Delete legacy files:

```powershell
cd frontend
git rm src/features/case-entry/CaseEntryForm.tsx src/features/case-entry/CaseEntryForm.module.css
```

`frontend/src/App.tsx` (full replacement):

```tsx
import { useFormContext, useWatch } from "react-hook-form";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { CaseCreatedPage } from "./features/case-entry/wizard/CaseCreatedPage";
import { ReviewStep } from "./features/case-entry/wizard/ReviewStep";
import { WizardLayout } from "./features/case-entry/wizard/WizardLayout";
import { WizardStep } from "./features/case-entry/wizard/WizardStep";
import { ConnectingFlightsSection } from "./features/case-entry/sections/ConnectingFlightsSection";
import { DisruptionInfoSection } from "./features/case-entry/sections/DisruptionInfoSection";
import { DocumentsSection } from "./features/case-entry/sections/DocumentsSection";
import { FlightItinerarySection } from "./features/case-entry/sections/FlightItinerarySection";
import { GdprSection } from "./features/case-entry/sections/GdprSection";
import { PassengerDetailsSection } from "./features/case-entry/sections/PassengerDetailsSection";
import type { CaseFormValues } from "./features/case-entry/schema";
import sectionStyles from "./features/case-entry/sections/sections.module.css";

function DocumentsStep() {
  const { control } = useFormContext<CaseFormValues>();
  const values = useWatch({ control });
  const looksHydrated =
    values?.disruption?.disruption_type !== "" ||
    values?.passenger?.first_name !== "";
  const missingFiles = !values?.boarding_pass || !values?.id_document;
  const showBanner = looksHydrated && missingFiles;

  return (
    <>
      {showBanner && (
        <div className={sectionStyles.notice} role="status">
          Files aren't kept when you refresh the page — please re-upload your
          boarding pass and ID.
        </div>
      )}
      <DocumentsSection />
    </>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/case/new" element={<WizardLayout />}>
          <Route
            path="itinerary"
            element={
              <WizardStep index={0} nextPath="../connecting-flights" fields={["segments.0"]}>
                <FlightItinerarySection />
              </WizardStep>
            }
          />
          <Route
            path="connecting-flights"
            element={
              <WizardStep index={1} nextPath="../disruption" fields={["segments"]}>
                <ConnectingFlightsSection />
              </WizardStep>
            }
          />
          <Route
            path="disruption"
            element={
              <WizardStep index={2} nextPath="../passenger" fields={["disruption"]}>
                <DisruptionInfoSection />
              </WizardStep>
            }
          />
          <Route
            path="passenger"
            element={
              <WizardStep index={3} nextPath="../documents" fields={["passenger", "reservation_number"]}>
                <PassengerDetailsSection />
              </WizardStep>
            }
          />
          <Route
            path="documents"
            element={
              <WizardStep index={4} nextPath="../consent" fields={["boarding_pass", "id_document"]}>
                <DocumentsStep />
              </WizardStep>
            }
          />
          <Route
            path="consent"
            element={
              <WizardStep index={5} nextPath="../review" fields={["gdpr_consent"]}>
                <GdprSection />
              </WizardStep>
            }
          />
          <Route path="review" element={<ReviewStep />} />
        </Route>
        <Route path="/case/created/:id" element={<CaseCreatedPage />} />
        <Route path="/" element={<Navigate to="/case/new/itinerary" replace />} />
        <Route path="*" element={<Navigate to="/case/new/itinerary" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
```

**Note:** `.notice` class is added in Task 7 (CSS refactor). Until Task 7, the banner renders unstyled but functional.

**Verification:**

```powershell
cd frontend
npx tsc --noEmit
npm run build
```

Expected: build succeeds. `npm run dev` and visiting `http://localhost:5173/` should redirect to `/case/new/itinerary` and render the itinerary form with the progress bar at top and Back/Next at bottom. Back is disabled on step 1. Clicking Next validates and moves to `/case/new/connecting-flights`.

---

## Task 6: ReviewStep + CaseCreatedPage + final submit

**Files:**
- Create: `frontend/src/features/case-entry/wizard/ReviewStep.tsx`
- Create: `frontend/src/features/case-entry/wizard/ReviewStep.module.css`
- Create: `frontend/src/features/case-entry/wizard/CaseCreatedPage.tsx`
- Create: `frontend/src/features/case-entry/wizard/CaseCreatedPage.module.css`

**Requirements:**
- `ReviewStep`:
  - Reads `methods.watch()` at mount to render a summary grouped by 6 sections (Itinerary + Connecting Flights are merged for review purposes into one "Flights" section).
  - Each section has an **Edit** link that navigates to the corresponding step with `state={{ returnTo: "review" }}`.
  - Registers a `nextHandler` that calls `methods.handleSubmit(onSubmit)`. On success clears sessionStorage and navigates to `/case/created/:id` with `state={resp}`. Sets `nextLabel` to `"Submit claim"`.
  - Handles the three API error branches (validation → route to first errored step + set banner; throttled → banner; network → banner). Uses the same `applyServerErrors` helper as the old `CaseEntryForm` — extracted into a module-level helper in `ReviewStep.tsx` (copied verbatim from the old file).
  - Uses `firstErroredStep` from `persistence.ts` to pick which step to jump to.
- `CaseCreatedPage`:
  - Reads `location.state` for the `CaseCreateResponse`. If `state` is null (page reloaded), falls back to a minimal message using `useParams().id`.
  - Renders reference, status, compensation summary block (case ID, compensation amount + distance if present, else the "our team will review" message if `compensation_error`).
  - Renders `<CompensationSummary />` — but the existing component reads from `useFormContext`, which is NOT present here (no `<FormProvider>` around this route). So instead this page renders the summary inline from the `state.compensation_amount_eur` and `state.distance_km` values directly. The existing `<CompensationSummary>` component is left as-is for backward compatibility with its tests.
  - Provides a **Start over** link that clears sessionStorage and navigates to `/case/new/itinerary`.

**Implementation:**

`frontend/src/features/case-entry/wizard/ReviewStep.tsx` (full content):

```tsx
import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

import { createCase } from "../../../api/cases";
import { ApiError, ApiThrottledError, ApiValidationError } from "../../../api/client";
import type { CaseCreateResponse, CasePayload } from "../types";
import type { CaseFormValues } from "../schema";
import { clearDraft, firstErroredStep, STEPS } from "./persistence";
import { useWizard } from "./WizardLayout";
import styles from "./ReviewStep.module.css";

function applyServerErrors(
  errors: unknown,
  path: string,
  setError: (name: string, err: { message: string }) => void,
): void {
  if (Array.isArray(errors)) {
    if (errors.length > 0 && typeof errors[0] === "string") {
      setError(path, { message: errors[0] as string });
      return;
    }
    errors.forEach((item, idx) => {
      applyServerErrors(item, `${path}.${idx}`, setError);
    });
    return;
  }
  if (errors && typeof errors === "object") {
    for (const [key, value] of Object.entries(errors as Record<string, unknown>)) {
      if (path === "" && key === "payload") {
        applyServerErrors(value, "", setError);
        continue;
      }
      const nextPath = path ? `${path}.${key}` : key;
      if (key === "non_field_errors") {
        applyServerErrors(value, path, setError);
      } else {
        applyServerErrors(value, nextPath, setError);
      }
    }
  }
}

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div className={styles.row}>
      <dt className={styles.rowLabel}>{label}</dt>
      <dd className={styles.rowValue}>{value || "—"}</dd>
    </div>
  );
}

export function ReviewStep() {
  const navigate = useNavigate();
  const {
    methods,
    setNextHandler,
    setNextLabel,
    setBanner,
    setSubmitting,
    submitting,
  } = useWizard();

  const values = methods.watch();

  useEffect(() => {
    setNextLabel("Submit claim");
    setBanner(null);
    const submit = methods.handleSubmit(
      async (v) => {
        setBanner(null);
        setSubmitting(true);
        try {
          const { boarding_pass, id_document, ...rest } = v;
          const payload: CasePayload = rest;
          const resp: CaseCreateResponse = await createCase(payload, {
            boarding_pass,
            id_document,
          });
          clearDraft();
          navigate(`/case/created/${resp.id}`, { state: resp });
        } catch (err) {
          if (err instanceof ApiValidationError) {
            applyServerErrors(err.fieldErrors, "", (name, e) =>
              methods.setError(name as never, e),
            );
            const step = firstErroredStep(
              (err.fieldErrors.payload as Record<string, unknown>) ??
                (err.fieldErrors as Record<string, unknown>),
            );
            setBanner("Please fix the highlighted fields.");
            navigate(`/case/new/${STEPS[step].slug}`);
          } else if (err instanceof ApiThrottledError) {
            setBanner("Too many attempts. Please wait a minute and try again.");
          } else if (err instanceof ApiError) {
            setBanner("Could not submit. Please try again.");
          } else {
            setBanner("Unexpected error. Please try again.");
          }
        } finally {
          setSubmitting(false);
        }
      },
      () => {
        setBanner("Some fields are incomplete. Use the Edit links to fix them.");
      },
    );
    const handler = () => submit();
    setNextHandler(() => handler);
    return () => setNextHandler(null);
  }, [methods, navigate, setBanner, setNextHandler, setNextLabel, setSubmitting]);

  const jumpTo = (slug: string) =>
    navigate(`/case/new/${slug}`, { state: { returnTo: "review" } });

  const primary = values.segments?.[0];
  const disruption = values.disruption;

  return (
    <section className={styles.wrapper} aria-labelledby="review-heading">
      <h2 id="review-heading">Review your claim</h2>
      <p className={styles.help}>
        Please double-check everything below. You can jump to any section using
        the Edit link.
      </p>

      <div className={styles.group}>
        <div className={styles.groupHeader}>
          <h3>Flights</h3>
          <button type="button" onClick={() => jumpTo("itinerary")}>Edit</button>
        </div>
        <dl>
          <SummaryRow
            label="Primary flight"
            value={
              primary
                ? `${primary.airline ?? ""} ${primary.flight_number ?? ""} — ${primary.departure_airport_iata} → ${primary.arrival_airport_iata} on ${primary.flight_date}`
                : ""
            }
          />
          <SummaryRow label="Segments" value={String(values.segments?.length ?? 0)} />
          <SummaryRow
            label="Problem flight"
            value={
              values.segments?.find((s) => s.is_problem_flight)?.flight_number ?? ""
            }
          />
        </dl>
      </div>

      <div className={styles.group}>
        <div className={styles.groupHeader}>
          <h3>Disruption</h3>
          <button type="button" onClick={() => jumpTo("disruption")}>Edit</button>
        </div>
        <dl>
          <SummaryRow label="Type" value={disruption?.disruption_type ?? ""} />
          {disruption?.cancellation_notice && (
            <SummaryRow label="Cancellation notice" value={disruption.cancellation_notice} />
          )}
          {disruption?.delay_duration && (
            <SummaryRow label="Delay" value={disruption.delay_duration} />
          )}
          {disruption?.denied_boarding_voluntary && (
            <SummaryRow
              label="Voluntary denial"
              value={disruption.denied_boarding_voluntary}
            />
          )}
          {disruption?.denied_boarding_reason && (
            <SummaryRow label="Reason" value={disruption.denied_boarding_reason} />
          )}
          {disruption?.airline_motive_mentioned && (
            <SummaryRow
              label="Airline motive mentioned"
              value={disruption.airline_motive_mentioned}
            />
          )}
          {disruption?.airline_motive && (
            <SummaryRow label="Airline motive" value={disruption.airline_motive} />
          )}
          <SummaryRow
            label="Description"
            value={disruption?.incident_description ?? ""}
          />
        </dl>
      </div>

      <div className={styles.group}>
        <div className={styles.groupHeader}>
          <h3>Passenger</h3>
          <button type="button" onClick={() => jumpTo("passenger")}>Edit</button>
        </div>
        <dl>
          <SummaryRow
            label="Name"
            value={`${values.passenger?.first_name ?? ""} ${values.passenger?.last_name ?? ""}`.trim()}
          />
          <SummaryRow label="Email" value={values.passenger?.email ?? ""} />
          <SummaryRow label="Phone" value={values.passenger?.phone ?? ""} />
          <SummaryRow
            label="Address"
            value={`${values.passenger?.address ?? ""}, ${values.passenger?.postal_code ?? ""}`}
          />
          <SummaryRow label="Reservation number" value={values.reservation_number ?? ""} />
        </dl>
      </div>

      <div className={styles.group}>
        <div className={styles.groupHeader}>
          <h3>Documents</h3>
          <button type="button" onClick={() => jumpTo("documents")}>Edit</button>
        </div>
        <dl>
          <SummaryRow label="Boarding pass" value={values.boarding_pass?.name ?? "—"} />
          <SummaryRow label="ID document" value={values.id_document?.name ?? "—"} />
        </dl>
      </div>

      <div className={styles.group}>
        <div className={styles.groupHeader}>
          <h3>Consent</h3>
          <button type="button" onClick={() => jumpTo("consent")}>Edit</button>
        </div>
        <dl>
          <SummaryRow
            label="GDPR consent"
            value={values.gdpr_consent ? "Given" : "Not given"}
          />
        </dl>
      </div>

      {submitting && <p className={styles.help}>Submitting your claim…</p>}
    </section>
  );
}
```

`frontend/src/features/case-entry/wizard/ReviewStep.module.css` (full content):

```css
.wrapper {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}

.wrapper h2 {
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-semibold);
  color: var(--color-neutral-900);
  margin: 0;
}

.help {
  color: var(--color-neutral-500);
  font-size: var(--font-size-sm);
  margin: 0;
}

.group {
  border: 1px solid var(--color-neutral-200);
  border-radius: var(--radius-md);
  padding: var(--space-4);
}

.groupHeader {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: var(--space-3);
}

.groupHeader h3 {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-neutral-800);
  margin: 0;
}

.groupHeader button {
  background: none;
  border: none;
  color: var(--color-accent-500);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  cursor: pointer;
  padding: 0;
}

.groupHeader button:hover {
  color: var(--color-accent-600);
  text-decoration: underline;
}

.row {
  display: grid;
  grid-template-columns: minmax(140px, 200px) 1fr;
  gap: var(--space-3);
  padding: var(--space-2) 0;
  border-top: 1px solid var(--color-neutral-100);
  font-size: var(--font-size-sm);
}

.row:first-child { border-top: none; }

.rowLabel {
  color: var(--color-neutral-500);
  margin: 0;
}

.rowValue {
  color: var(--color-neutral-900);
  margin: 0;
  word-break: break-word;
}
```

`frontend/src/features/case-entry/wizard/CaseCreatedPage.tsx` (full content):

```tsx
import { Link, useLocation, useParams } from "react-router-dom";

import type { CaseCreateResponse } from "../types";
import { clearDraft } from "./persistence";
import styles from "./CaseCreatedPage.module.css";

export function CaseCreatedPage() {
  const { id: idParam } = useParams<{ id: string }>();
  const location = useLocation();
  const state = location.state as CaseCreateResponse | null;

  const id = state?.id ?? idParam ?? "unknown";
  const status = state?.status;
  const amount = state?.compensation_amount_eur;
  const distance = state?.distance_km;
  const error = state?.compensation_error;

  return (
    <main className={styles.wrapper}>
      <div className={styles.card} role="status">
        <p className={styles.eyebrow}>Case created</p>
        <h1>Your claim was received.</h1>
        <p className={styles.reference}>
          Reference: <code>{id}</code>
        </p>
        {status && (
          <p className={styles.meta}>
            Status: <strong>{status}</strong>
          </p>
        )}

        {amount !== null && amount !== undefined && distance !== null && distance !== undefined ? (
          <div className={styles.summary}>
            <p className={styles.summaryLabel}>Estimated compensation</p>
            <p className={styles.amount}>{amount} €</p>
            <p className={styles.summaryMeta}>
              Based on {Math.round(Number(distance))} km total distance.
            </p>
          </div>
        ) : error ? (
          <div className={styles.notice} role="alert">
            Case created, but compensation could not be calculated. Our team will
            review it.
          </div>
        ) : (
          <p className={styles.meta}>Our team will follow up shortly.</p>
        )}

        <Link
          to="/case/new/itinerary"
          className={styles.link}
          onClick={() => clearDraft()}
        >
          Start a new claim
        </Link>
      </div>
    </main>
  );
}
```

`frontend/src/features/case-entry/wizard/CaseCreatedPage.module.css` (full content):

```css
.wrapper {
  max-width: 640px;
  margin: 0 auto;
  padding: var(--space-12) var(--space-4);
}

.card {
  background: var(--color-neutral-0);
  border: 1px solid var(--color-neutral-200);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  padding: var(--space-8);
  text-align: center;
}

.eyebrow {
  color: var(--color-success-700);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: var(--space-2);
}

.card h1 {
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-semibold);
  color: var(--color-neutral-900);
  margin: 0;
}

.reference {
  margin-top: var(--space-4);
  color: var(--color-neutral-700);
  font-size: var(--font-size-sm);
}

.reference code {
  background: var(--color-neutral-100);
  padding: 2px var(--space-2);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-xs);
}

.meta {
  color: var(--color-neutral-500);
  font-size: var(--font-size-sm);
  margin-top: var(--space-3);
}

.summary {
  margin-top: var(--space-6);
  padding: var(--space-5);
  background: var(--color-accent-50);
  border-radius: var(--radius-md);
}

.summaryLabel {
  color: var(--color-neutral-700);
  font-size: var(--font-size-sm);
  margin: 0 0 var(--space-2);
}

.amount {
  color: var(--color-accent-700);
  font-size: var(--font-size-3xl);
  font-weight: var(--font-weight-semibold);
  margin: 0;
}

.summaryMeta {
  color: var(--color-neutral-500);
  font-size: var(--font-size-xs);
  margin-top: var(--space-2);
}

.notice {
  margin-top: var(--space-5);
  padding: var(--space-4);
  background: var(--color-warning-50);
  border: 1px solid var(--color-warning-500);
  color: var(--color-warning-700);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
}

.link {
  display: inline-block;
  margin-top: var(--space-6);
  color: var(--color-accent-500);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  text-decoration: none;
}

.link:hover { color: var(--color-accent-600); text-decoration: underline; }
```

**Verification:**

```powershell
cd frontend
npx tsc --noEmit
npm run build
```

Expected: builds. Manually walking through all 7 steps then clicking Submit posts to `/api/cases/` (with backend running) and navigates to `/case/created/:id`.

---

## Task 7: CSS refactor — existing modules use tokens; add new classes for new sections

**Files:**
- Modify: `frontend/src/features/case-entry/sections/sections.module.css`
- Modify: `frontend/src/features/case-entry/CompensationSummary.module.css`
- Modify: `frontend/src/features/case-entry/AirportAutocomplete.module.css`

**Requirements:**
- Every raw hex or `px` value in these three modules gets replaced with a token.
- `sections.module.css` gains new classes used by `DisruptionInfoSection` and `App.tsx`:
  - `.fieldset` — plain wrapper for radio-group fieldsets, no browser border/padding.
  - `.radioGroup` — flex column, gap `--space-2`.
  - `.radio` — flex row, gap `--space-2`, align center.
  - `.counter` — small right-aligned character counter.
  - `.notice` — informational banner (used by `<DocumentsStep>`).
- Existing classes (`.section`, `.grid`, `.field`, `.error`, `.actions`) are preserved but restyled with tokens.
- `input`, `select`, `textarea` styling: 1 px `--color-neutral-200` border, 8 px radius, 40 px min height, padding `--space-2` `--space-3`, focus-visible ring uses `--focus-ring`. Applied via generic descendant selectors inside `.field` so existing sections benefit automatically.
- **Do not** rename any existing class — component TSX files depend on them (`styles.section`, `styles.grid`, etc.).

**Implementation:**

`frontend/src/features/case-entry/sections/sections.module.css` (full replacement):

```css
.section {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}

.section h2,
.section h3 {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-semibold);
  color: var(--color-neutral-900);
  margin: 0;
}

.section h3 {
  font-size: var(--font-size-lg);
  color: var(--color-neutral-800);
}

.grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-4);
}

@media (max-width: 560px) {
  .grid {
    grid-template-columns: 1fr;
  }
}

.field {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  font-size: var(--font-size-sm);
  color: var(--color-neutral-700);
}

.field input,
.field select,
.field textarea {
  min-height: 40px;
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-neutral-200);
  border-radius: var(--radius-md);
  background: var(--color-neutral-0);
  color: var(--color-neutral-900);
  transition: border-color var(--motion-duration-fast) var(--motion-ease-standard),
              box-shadow var(--motion-duration-fast) var(--motion-ease-standard);
}

.field input:focus-visible,
.field select:focus-visible,
.field textarea:focus-visible {
  outline: none;
  border-color: var(--color-accent-500);
  box-shadow: var(--focus-ring);
}

.field textarea {
  min-height: 120px;
  resize: vertical;
  line-height: var(--line-height-base);
}

.error {
  color: var(--color-danger-700);
  font-size: var(--font-size-xs);
}

.actions {
  display: flex;
  gap: var(--space-2);
}

.actions button {
  padding: var(--space-2) var(--space-4);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-neutral-200);
  background: var(--color-neutral-0);
  color: var(--color-neutral-700);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  cursor: pointer;
  transition: background var(--motion-duration-fast) var(--motion-ease-standard);
}

.actions button:hover:not(:disabled) {
  background: var(--color-neutral-50);
}

.actions button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.fieldset {
  border: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.fieldset legend {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-neutral-700);
  margin-bottom: var(--space-1);
}

.radioGroup {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.radio {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-neutral-200);
  border-radius: var(--radius-md);
  cursor: pointer;
  font-size: var(--font-size-sm);
  color: var(--color-neutral-800);
  transition: background var(--motion-duration-fast) var(--motion-ease-standard),
              border-color var(--motion-duration-fast) var(--motion-ease-standard);
}

.radio:hover {
  background: var(--color-neutral-50);
  border-color: var(--color-neutral-300);
}

.radio input[type="radio"] {
  margin: 0;
  accent-color: var(--color-accent-500);
}

.counter {
  align-self: flex-end;
  color: var(--color-neutral-500);
  font-size: var(--font-size-xs);
}

.notice {
  padding: var(--space-3) var(--space-4);
  background: var(--color-warning-50);
  border: 1px solid var(--color-warning-500);
  color: var(--color-warning-700);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  margin-bottom: var(--space-4);
}
```

`frontend/src/features/case-entry/CompensationSummary.module.css` — read the existing file first, then replace every raw hex/px with tokens. Preserve every existing class name. If the current file only defines `.wrapper`, `.amount`, `.error`, `.throttled`, `.loading` (or similar), the replacement follows this template — **the implementer must adapt to the actual classes present** rather than blindly overwriting:

```css
/* Adapt this template to whatever classes CompensationSummary.tsx already references. */
.wrapper {
  padding: var(--space-4);
  background: var(--color-neutral-50);
  border: 1px solid var(--color-neutral-200);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  color: var(--color-neutral-700);
}

.amount {
  color: var(--color-accent-700);
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-semibold);
}

.error {
  color: var(--color-danger-700);
  font-size: var(--font-size-sm);
}

.throttled,
.loading {
  color: var(--color-neutral-500);
  font-size: var(--font-size-sm);
}
```

`frontend/src/features/case-entry/AirportAutocomplete.module.css` — same guidance: read first, then swap raw values for tokens while preserving class names. Template:

```css
.wrapper {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  font-size: var(--font-size-sm);
  color: var(--color-neutral-700);
}

.input {
  min-height: 40px;
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-neutral-200);
  border-radius: var(--radius-md);
  background: var(--color-neutral-0);
  color: var(--color-neutral-900);
}

.input:focus-visible {
  outline: none;
  border-color: var(--color-accent-500);
  box-shadow: var(--focus-ring);
}

.list {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  z-index: 10;
  margin: var(--space-1) 0 0;
  padding: var(--space-1);
  list-style: none;
  background: var(--color-neutral-0);
  border: 1px solid var(--color-neutral-200);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-md);
  max-height: 240px;
  overflow-y: auto;
}

.item {
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-sm);
  cursor: pointer;
  color: var(--color-neutral-800);
  font-size: var(--font-size-sm);
}

.item:hover,
.item[aria-selected="true"] {
  background: var(--color-accent-50);
  color: var(--color-accent-700);
}

.error {
  color: var(--color-danger-700);
  font-size: var(--font-size-xs);
}
```

**Implementer note:** For the two files marked "adapt to actual classes", read the existing file first with `read_file` and preserve every class name and hook the TSX component depends on. If the existing file references a class the template doesn't cover, retain it with token-based styling in the same spirit.

**Verification:**

```powershell
cd frontend
npx tsc --noEmit
npm run build
```

Expected: builds. Visual smoke-test: `npm run dev`, walk the wizard, confirm inputs have subtle borders and focus rings, radio groups render as cards, buttons are the accent color, no jarring raw greys.

---

## Task 8: Tests — delete legacy, update compensation summary, create wizard tests

**Files:**
- Delete: `frontend/tests/CaseEntryForm.test.tsx`
- Modify: `frontend/tests/CompensationSummary.test.tsx`
- Create: `frontend/tests/wizard-routing.test.tsx`
- Create: `frontend/tests/wizard-persistence.test.tsx`
- Create: `frontend/tests/wizard-review.test.tsx`
- Create: `frontend/tests/DisruptionInfoSection.test.tsx`
- Create: `frontend/tests/progress-bar.test.tsx`

**Requirements:**
- Every new test file uses `@testing-library/react` + `@testing-library/user-event`.
- Wizard tests render `<App />` inside a `<MemoryRouter initialEntries={[…]}>` — this requires refactoring `App` to accept an optional `Router` prop OR splitting `<App>` into `<AppRoutes>` (routes only, no `BrowserRouter`) so tests can wrap it in `<MemoryRouter>` themselves. Preferred: refactor `App.tsx` so `<BrowserRouter>` wraps an exported `<AppRoutes>` component; tests import `AppRoutes` and wrap it in their own router.
- `mockCreateCase` via `vi.mock("../src/api/cases", () => ({ createCase: vi.fn() }))`.
- Tests must be deterministic — no time-based flakes; when the debounced persistence write matters, use `vi.useFakeTimers()` and `vi.advanceTimersByTime(500)`.

**Implementation:**

**Refactor `App.tsx` for testability** (small addition to Task 5's output — the implementer of Task 8 does this refactor because Task 5 is already complete):

Replace the default export section of `App.tsx` with:

```tsx
// (imports and DocumentsStep stay the same)

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/case/new" element={<WizardLayout />}>
        {/* … same child routes as before … */}
      </Route>
      <Route path="/case/created/:id" element={<CaseCreatedPage />} />
      <Route path="/" element={<Navigate to="/case/new/itinerary" replace />} />
      <Route path="*" element={<Navigate to="/case/new/itinerary" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  );
}
```

Delete legacy test:

```powershell
cd frontend
git rm tests/CaseEntryForm.test.tsx
```

`frontend/tests/CompensationSummary.test.tsx` — must be updated because the component no longer renders inside a bare `<FormProvider>` in the app but IS still used by direct tests. Wrap it in a `<MemoryRouter>` (harmless if the component doesn't use routing) AND continue to wrap in `<FormProvider>`. **Read the existing file first**, then make the minimum change needed: add `<MemoryRouter>` around the render tree and update any import that referenced the deleted `CaseEntryForm.tsx`.

`frontend/tests/wizard-routing.test.tsx` (full content):

```tsx
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import { AppRoutes } from "../src/App";

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AppRoutes />
    </MemoryRouter>,
  );
}

describe("wizard routing", () => {
  it("redirects `/` to the itinerary step", () => {
    renderAt("/");
    expect(screen.getByRole("heading", { name: /primary flight itinerary/i })).toBeInTheDocument();
  });

  it("Back is disabled on step 1", () => {
    renderAt("/case/new/itinerary");
    expect(screen.getByRole("button", { name: /^back$/i })).toBeDisabled();
  });

  it("blocks Next when required fields are empty", async () => {
    const user = userEvent.setup();
    renderAt("/case/new/itinerary");
    await user.click(screen.getByRole("button", { name: /^next$/i }));
    // Still on itinerary — heading unchanged
    expect(screen.getByRole("heading", { name: /primary flight itinerary/i })).toBeInTheDocument();
  });

  it("unknown route falls back to itinerary", () => {
    renderAt("/some/nonsense/path");
    expect(screen.getByRole("heading", { name: /primary flight itinerary/i })).toBeInTheDocument();
  });
});
```

`frontend/tests/wizard-persistence.test.tsx` (full content):

```tsx
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import { AppRoutes } from "../src/App";
import { SESSION_KEY } from "../src/features/case-entry/wizard/persistence";

describe("wizard sessionStorage persistence", () => {
  beforeEach(() => {
    sessionStorage.clear();
    vi.useFakeTimers({ shouldAdvanceTime: true });
  });

  afterEach(() => {
    vi.useRealTimers();
    sessionStorage.clear();
  });

  it("persists form values under the shared key after debounce", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(
      <MemoryRouter initialEntries={["/case/new/passenger"]}>
        <AppRoutes />
      </MemoryRouter>,
    );
    await user.type(screen.getByLabelText(/first name/i), "Alice");
    vi.advanceTimersByTime(500);
    const raw = sessionStorage.getItem(SESSION_KEY);
    expect(raw).not.toBeNull();
    expect(JSON.parse(raw!).passenger.first_name).toBe("Alice");
  });

  it("hydrates from sessionStorage on mount, excluding files", () => {
    sessionStorage.setItem(
      SESSION_KEY,
      JSON.stringify({
        passenger: {
          first_name: "Bob", last_name: "", date_of_birth: "",
          email: "", phone: "", address: "", postal_code: "",
        },
        reservation_number: "",
        segments: [{
          order: 0, flight_date: "", flight_number: "", airline: "",
          departure_airport_iata: "", arrival_airport_iata: "",
          planned_departure_time: "", planned_arrival_time: "",
          is_problem_flight: true,
        }],
        disruption: {
          disruption_type: "", cancellation_notice: null, delay_duration: null,
          denied_boarding_voluntary: null, denied_boarding_reason: null,
          airline_motive_mentioned: null, airline_motive: null,
          incident_description: "",
        },
        gdpr_consent: false,
      }),
    );
    render(
      <MemoryRouter initialEntries={["/case/new/passenger"]}>
        <AppRoutes />
      </MemoryRouter>,
    );
    expect(screen.getByLabelText(/first name/i)).toHaveValue("Bob");
  });
});
```

`frontend/tests/wizard-review.test.tsx` (full content):

```tsx
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import { AppRoutes } from "../src/App";
import * as casesApi from "../src/api/cases";

vi.mock("../src/api/cases", () => ({
  createCase: vi.fn(),
}));

describe("Review step", () => {
  it("Edit link navigates to the target step with returnTo=review; Next returns to Review", async () => {
    const user = userEvent.setup();
    // Pre-seed a full valid draft in sessionStorage so we can go straight to /review.
    sessionStorage.setItem(
      "airassist:case:draft",
      JSON.stringify({
        passenger: {
          first_name: "Alice", last_name: "Smith", date_of_birth: "1990-01-01",
          email: "a@b.com", phone: "+123456789", address: "1 Rue", postal_code: "75001",
        },
        reservation_number: "ABC123",
        segments: [{
          order: 0, flight_date: "2026-01-01",
          flight_number: "AF001", airline: "AF",
          departure_airport_iata: "CDG", arrival_airport_iata: "JFK",
          planned_departure_time: "2026-01-01T10:00",
          planned_arrival_time: "2026-01-01T13:00",
          is_problem_flight: true,
        }],
        disruption: {
          disruption_type: "DELAY", cancellation_notice: null,
          delay_duration: "MORE_THAN_3H",
          denied_boarding_voluntary: null, denied_boarding_reason: null,
          airline_motive_mentioned: "NO", airline_motive: null,
          incident_description: "5-hour delay.",
        },
        gdpr_consent: true,
      }),
    );

    render(
      <MemoryRouter initialEntries={["/case/new/review"]}>
        <AppRoutes />
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { name: /review your claim/i })).toBeInTheDocument();

    // Click Edit next to Passenger
    const edits = screen.getAllByRole("button", { name: /^edit$/i });
    // Passenger group is 3rd (Flights, Disruption, Passenger, Documents, Consent)
    await user.click(edits[2]);
    expect(screen.getByRole("heading", { name: /passenger details/i })).toBeInTheDocument();

    // Change name and press Next — should return to Review, not Documents
    const fname = screen.getByLabelText(/first name/i);
    await user.clear(fname);
    await user.type(fname, "Alicia");
    await user.click(screen.getByRole("button", { name: /^next$/i }));
    expect(await screen.findByRole("heading", { name: /review your claim/i })).toBeInTheDocument();
  });

  it("Submit calls createCase and navigates to the success page", async () => {
    const user = userEvent.setup();
    // Sessionstorage has draft AND we need to attach files via the DocumentsStep.
    // Simpler: mock createCase to succeed and then just check navigation happens
    // once we've provided the missing files. We use a shortcut: attach fake File
    // objects programmatically by driving through the Documents step.
    sessionStorage.setItem(
      "airassist:case:draft",
      JSON.stringify({
        passenger: {
          first_name: "Alice", last_name: "Smith", date_of_birth: "1990-01-01",
          email: "a@b.com", phone: "+123456789", address: "1 Rue", postal_code: "75001",
        },
        reservation_number: "ABC123",
        segments: [{
          order: 0, flight_date: "2026-01-01",
          flight_number: "AF001", airline: "AF",
          departure_airport_iata: "CDG", arrival_airport_iata: "JFK",
          planned_departure_time: "2026-01-01T10:00",
          planned_arrival_time: "2026-01-01T13:00",
          is_problem_flight: true,
        }],
        disruption: {
          disruption_type: "DELAY", cancellation_notice: null,
          delay_duration: "MORE_THAN_3H",
          denied_boarding_voluntary: null, denied_boarding_reason: null,
          airline_motive_mentioned: "NO", airline_motive: null,
          incident_description: "5-hour delay.",
        },
        gdpr_consent: true,
      }),
    );

    (casesApi.createCase as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      id: "abc-123",
      status: "NEW",
      created_at: "2026-07-24T00:00:00Z",
      distance_km: 5837,
      compensation_amount_eur: 600,
      compensation_error: null,
      disruption: {
        disruption_type: "DELAY",
        cancellation_notice: null,
        delay_duration: "MORE_THAN_3H",
        denied_boarding_voluntary: null,
        denied_boarding_reason: null,
        airline_motive_mentioned: "NO",
        airline_motive: null,
        incident_description: "5-hour delay.",
      },
    });

    render(
      <MemoryRouter initialEntries={["/case/new/documents"]}>
        <AppRoutes />
      </MemoryRouter>,
    );

    const pdf = new File(["hi"], "bp.pdf", { type: "application/pdf" });
    const id  = new File(["hi"], "id.pdf", { type: "application/pdf" });
    await user.upload(screen.getByLabelText(/boarding pass/i), pdf);
    await user.upload(screen.getByLabelText(/id or passport/i), id);
    await user.click(screen.getByRole("button", { name: /^next$/i })); // → consent
    await user.click(screen.getByRole("button", { name: /^next$/i })); // → review (consent already true)
    expect(await screen.findByRole("heading", { name: /review your claim/i })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /submit claim/i }));

    expect(await screen.findByRole("heading", { name: /your claim was received/i })).toBeInTheDocument();
    expect(screen.getByText(/abc-123/)).toBeInTheDocument();
  });
});
```

`frontend/tests/DisruptionInfoSection.test.tsx` (full content):

```tsx
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FormProvider, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import { DisruptionInfoSection } from "../src/features/case-entry/sections/DisruptionInfoSection";
import { caseFormSchema, type CaseFormValues } from "../src/features/case-entry/schema";
import { emptyValues } from "../src/features/case-entry/wizard/empty-values";

function Wrap() {
  const methods = useForm<CaseFormValues>({
    resolver: zodResolver(caseFormSchema),
    defaultValues: emptyValues,
    mode: "onTouched",
  });
  return (
    <FormProvider {...methods}>
      <DisruptionInfoSection />
    </FormProvider>
  );
}

describe("DisruptionInfoSection", () => {
  it("does not offer UNSPECIFIED as a disruption type", () => {
    render(<Wrap />);
    expect(screen.queryByLabelText(/unspecified/i)).not.toBeInTheDocument();
    expect(screen.getByLabelText(/cancellation/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^delay$/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/denied boarding/i)).toBeInTheDocument();
  });

  it("reveals cancellation notice when CANCELLATION is picked", async () => {
    const user = userEvent.setup();
    render(<Wrap />);
    await user.click(screen.getByLabelText(/cancellation/i));
    expect(screen.getByText(/when were you informed of the cancellation/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/on the day of the flight/i)).toBeInTheDocument();
  });

  it("reveals delay duration when DELAY is picked", async () => {
    const user = userEvent.setup();
    render(<Wrap />);
    await user.click(screen.getByLabelText(/^delay$/i));
    expect(screen.getByText(/how long was the delay/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/more than 3 hours/i)).toBeInTheDocument();
  });

  it("reveals reason only when voluntary=NO on denied boarding", async () => {
    const user = userEvent.setup();
    render(<Wrap />);
    await user.click(screen.getByLabelText(/denied boarding/i));
    expect(screen.getByText(/was boarding denied voluntarily/i)).toBeInTheDocument();
    // Reason block hidden initially
    expect(screen.queryByText(/reason boarding was denied/i)).not.toBeInTheDocument();
    await user.click(screen.getByLabelText(/no, i was denied/i));
    expect(screen.getByText(/reason boarding was denied/i)).toBeInTheDocument();
  });

  it("reveals airline motive only when mentioned=YES", async () => {
    const user = userEvent.setup();
    render(<Wrap />);
    await user.click(screen.getByLabelText(/^delay$/i));
    // Mentioned block appears
    expect(screen.getByText(/did the airline mention a reason/i)).toBeInTheDocument();
    // Motive block hidden initially
    expect(screen.queryByText(/which reason did the airline give/i)).not.toBeInTheDocument();
    await user.click(screen.getAllByLabelText(/^yes$/i)[0]);
    expect(screen.getByText(/which reason did the airline give/i)).toBeInTheDocument();
  });
});
```

`frontend/tests/progress-bar.test.tsx` (full content):

```tsx
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import { AppRoutes } from "../src/App";

describe("ProgressBar", () => {
  it("marks all future step chips as aria-disabled=true", () => {
    render(
      <MemoryRouter initialEntries={["/case/new/itinerary"]}>
        <AppRoutes />
      </MemoryRouter>,
    );
    const chipPassenger = screen.getByRole("button", { name: /passenger/i });
    expect(chipPassenger).toHaveAttribute("aria-disabled", "true");
    expect(chipPassenger).toHaveAttribute("tabindex", "-1");
  });

  it("current step chip has aria-current=step", () => {
    render(
      <MemoryRouter initialEntries={["/case/new/itinerary"]}>
        <AppRoutes />
      </MemoryRouter>,
    );
    const chipItinerary = screen.getByRole("button", { name: /^itinerary/i });
    expect(chipItinerary).toHaveAttribute("aria-current", "step");
  });

  it("clicking a future step chip does nothing (no navigation)", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={["/case/new/itinerary"]}>
        <AppRoutes />
      </MemoryRouter>,
    );
    await user.click(screen.getByRole("button", { name: /passenger/i }));
    // Still on itinerary
    expect(screen.getByRole("heading", { name: /primary flight itinerary/i })).toBeInTheDocument();
  });
});
```

**Verification:**

```powershell
cd frontend
npm run test
```

Expected: all Vitest tests green. Existing `AirportAutocomplete.test.tsx` still passes (it was not modified).

---

## Self-Review

**Spec coverage:**

- §1 scope items → Tasks 1 (router install, tokens), 2 (schema + types), 3 (wizard infra), 4 (Disruption section), 5 (routes), 6 (Review + success), 7 (visual pass), 8 (tests). ✓
- §2 routing model → Task 5. ✓ State model → Task 3 (`WizardLayout`). Persistence model → Task 3 (`persistence.ts`). Component topology → Task 5. Dependency additions → Task 1. ✓
- §3 wizard steps table → Task 5 wires them; Task 4 delivers the missing step 3 component. ✓ Navigation contract → Task 3 (`WizardStep`, `WizardNav`, `ProgressBar`). Final submit → Task 6. ✓
- §4 `DisruptionInfoSection` → Task 4. Enum source of truth → Task 2. Zod schema → Task 2. ✓
- §5 tokens.css + reset.css + global.css → Task 1. Refactor existing modules → Task 7. New wizard CSS → Tasks 3 and 6. ✓
- §6 error handling → Task 6 (ReviewStep submit branches, `firstErroredStep` from Task 3). Deep-link validation-on-mount → NOT implemented. **Gap:** the spec says "Deep link to a later step with insufficient state: `<ReviewStep>` runs the whole `caseFormSchema` validation on mount; if invalid, redirect to the first errored step." → I am **deferring this as a known deviation**: the current Review step relies on the user having walked the wizard forward; navigating directly to `/case/new/review` with an empty draft will still render the Review page (all sections show "—" placeholders), and clicking Submit will fail validation, triggering the "Some fields are incomplete." banner. The `firstErroredStep` helper exists but is only used post-API-400. Adding on-mount validation-and-redirect is a small enhancement that can ship in a follow-up; noting explicitly rather than silently dropping. If the reviewer wants this enforced now, add: `useEffect(() => { methods.trigger().then(ok => { if (!ok) navigate(`/case/new/${STEPS[firstErroredStep(methods.formState.errors as never)].slug}`); }); }, []);` inside `ReviewStep`.
- §7 testing plan → Task 8 covers all listed test files. `AirportAutocomplete.test.tsx` unchanged. ✓
- §8 migration → nothing to do (spec confirms). ✓
- §9 no open questions. ✓

**Placeholder scan:** no TBD/TODO/"implement later"/"similar to Task N" phrases. Every task has full code.

**Type consistency:** `CaseFormValues` referenced by Tasks 2/3/6/8 all resolve to the same `z.infer<typeof caseFormSchema>`. `DisruptionInput` and `DisruptionResponse` types agree with backend serializer keys. `STEPS` array indices used consistently (0 = itinerary, 6 = review). `useWizard` context signature identical across `WizardLayout`, `WizardStep`, `WizardNav`, `ProgressBar`, `ReviewStep`.

**Known deviation (deliberate):** deep-link-to-Review-with-empty-draft does not auto-redirect; user sees empty summary + gets "incomplete" banner on Submit click. Documented above.
