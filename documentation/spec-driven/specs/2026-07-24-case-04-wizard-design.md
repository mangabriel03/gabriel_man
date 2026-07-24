# CASE_04 — Multi-Step Wizard: Design Spec

**Project:** AirAssist (EU 261/2004 flight-compensation claim management)
**Story:** CASE_04 — Multi-Step Claim Wizard
**Date:** 2026-07-24
**Status:** Approved for planning

---

## 1. Purpose & Scope

Replace the current single-page `CaseEntryForm` with a **7-step wizard** where each step lives on its own URL, has its own validation gate, and hands control off to the next step only after the current step is valid. Modernise the visual style at the same time so the whole product looks like a real 2026 product (Linear/Stripe/Vercel-docs aesthetic) instead of a plain HTML form.

This is purely a **frontend + UX** story. The backend contract (`POST /api/cases/` multipart) is unchanged and stays exactly as CASE_01 + CASE_02 + CASE_03 left it. No backend files are touched by this story.

### In scope (CASE_04)

- Introduce `react-router-dom` and set up 8 routes: `/` (redirects to `/case/new/itinerary`), one route per step, and `/case/created/:id` for the success page.
- Split the current `CaseEntryForm` into 7 wizard steps (see §3). Existing section components (`FlightItinerarySection`, `ConnectingFlightsSection`, `PassengerDetailsSection`, `DocumentsSection`, `GdprSection`) are reused as-is where possible; new components are created only where necessary.
- Add a **Disruption Info** step (step 3) that collects the CASE_03 fields via a new `DisruptionInfoSection` component — this is the frontend deliverable that was deferred from CASE_03.
- A **progress bar** at the top of every step showing the 7 step names, with checkmarks on completed steps and the active step highlighted. Only completed steps and the current step are clickable.
- A **Review & Submit** step (step 7) that renders every collected value grouped by section with an "Edit" link that jumps to the corresponding step and returns to Review after Save.
- The final `POST /api/cases/` submission happens on the Review step. On success, navigate to `/case/created/:id` where the `CompensationSummary` renders (this is the only place the compensation preview logic is used — the intermediate steps do NOT show it).
- **Session persistence** of non-file form values under a single `sessionStorage` key (`airassist:case:draft`). Refresh restores state; file inputs (`boarding_pass`, `id_document`) are excluded and must be re-uploaded. A banner on the Documents step surfaces that constraint when the user arrives with hydrated non-file state but no files.
- A **design-token system** in `frontend/src/styles/tokens.css` (per `.github/instructions/frontend-style.instructions.md`) and updated CSS Modules for every component so the whole UI looks cohesive and modern.
- Vitest tests for: the wizard router setup, per-step navigation gating, sessionStorage hydration, Review-page edit-and-return flow, the new `DisruptionInfoSection`, and end-to-end multi-step submission.

### Explicitly out of scope

- Any change to backend endpoints, models, migrations, serializers, admin, or tests. (`backend/` remains untouched.)
- Payment collection, passenger accounts, login, or i18n.
- Server-side draft persistence — sessionStorage only, cleared on submit success or explicit "Start over".
- File upload chunking, retries, or upload-progress indicators beyond the browser's default.
- Autosave debouncing beyond `useEffect`-on-change writes to sessionStorage.
- A drag-and-drop reorderable segment list — keep the current "add/remove flight" UX from CASE_01 unchanged inside the Connecting Flights step.
- Analytics, feature flags, A/B testing.
- Any change to the Django admin's own visual style.

---

## 2. Architecture Overview

### Routing model

Single-page application with `react-router-dom` (`BrowserRouter`). Every wizard step is a real URL so browser Back/Forward, deep-linking, and reload work as expected.

```
/                                        → <Navigate to="/case/new/itinerary" replace />
/case/new/itinerary                      → step 1: FlightItinerarySection wrapped in <WizardStep>
/case/new/connecting-flights             → step 2: ConnectingFlightsSection wrapped in <WizardStep>
/case/new/disruption                     → step 3: DisruptionInfoSection wrapped in <WizardStep>
/case/new/passenger                      → step 4: PassengerDetailsSection wrapped in <WizardStep>
/case/new/documents                      → step 5: DocumentsSection wrapped in <WizardStep>
/case/new/consent                        → step 6: GdprSection wrapped in <WizardStep>
/case/new/review                         → step 7: <ReviewStep>
/case/created/:id                        → success page: <CaseCreatedPage> with <CompensationSummary>
*                                        → <Navigate to="/case/new/itinerary" replace />
```

All wizard step routes are children of a `<WizardLayout>` route that provides:
- The `<FormProvider>` from React Hook Form so every step reads/writes the same form state.
- The `<ProgressBar>` at the top.
- The `<WizardNav>` (Back / Next buttons) at the bottom, whose behaviour is defined per-step by the wrapped step component.
- The hydration effect that reads `sessionStorage` on mount and the persistence effect that writes on every value change.

### State model

React Hook Form (`useForm<CaseFormValues>`) at the `<WizardLayout>` level is the single source of truth. It replaces the current per-form `useForm` call in `CaseEntryForm.tsx`. The `mode` stays `"onTouched"` (matches CASE_01).

The `caseFormSchema` grows one nested field — `disruption: disruptionSchema` — but is otherwise unchanged. Per-step validation runs on a **subset** of the full schema (see §5) so a step can gate `Next` without dragging in unrelated errors.

### Persistence model

- **Storage key:** `airassist:case:draft` (constant `SESSION_KEY` in `frontend/src/features/case-entry/wizard/persistence.ts`).
- **What is persisted:** the entire RHF `getValues()` output, minus `boarding_pass` and `id_document` (they are stripped before serialisation).
- **When we write:** in a `useEffect` that watches `methods.watch()` values, debounced 400 ms.
- **When we read:** once, on `<WizardLayout>` mount. If a stored draft exists, `methods.reset(hydrated)` is called before the first render commits. Files remain unset.
- **When we clear:** on successful `POST /api/cases/` (before `navigate("/case/created/:id")`), and when the user clicks a "Start over" link on the success page.
- **Refresh with missing files:** when the user lands on `/case/new/documents` and either file input is empty AND the rest of the form has non-default values, render a banner: *"Please re-upload your boarding pass and ID — files aren't kept when you refresh the page."*

### Component topology

```
<App>
  <BrowserRouter>
    <Routes>
      <Route path="/case/new" element={<WizardLayout />}>
        <Route path="itinerary"           element={<WizardStep index={0} nextPath="../connecting-flights" fields={['segments.0']}><FlightItinerarySection /></WizardStep>} />
        <Route path="connecting-flights"  element={<WizardStep index={1} nextPath="../disruption"         fields={['segments']}><ConnectingFlightsSection /></WizardStep>} />
        <Route path="disruption"          element={<WizardStep index={2} nextPath="../passenger"          fields={['disruption']}><DisruptionInfoSection /></WizardStep>} />
        <Route path="passenger"           element={<WizardStep index={3} nextPath="../documents"          fields={['passenger', 'reservation_number']}><PassengerDetailsSection /></WizardStep>} />
        <Route path="documents"           element={<WizardStep index={4} nextPath="../consent"            fields={['boarding_pass', 'id_document']}><DocumentsSection /></WizardStep>} />
        <Route path="consent"             element={<WizardStep index={5} nextPath="../review"             fields={['gdpr_consent']}><GdprSection /></WizardStep>} />
        <Route path="review"              element={<ReviewStep />} />
      </Route>
      <Route path="/case/created/:id"     element={<CaseCreatedPage />} />
      <Route path="/"                     element={<Navigate to="/case/new/itinerary" replace />} />
      <Route path="*"                     element={<Navigate to="/case/new/itinerary" replace />} />
    </Routes>
  </BrowserRouter>
</App>
```

`<WizardLayout>` renders `<ProgressBar />`, the child `<Outlet />`, and `<WizardNav />`. `<WizardStep>` is a thin wrapper that (a) validates the listed fields on click of Next using `methods.trigger(fields)`, (b) navigates via `nextPath` on success, and (c) exposes `stepIndex` to the layout so the progress bar knows the current position. Back always navigates without validation.

### Dependency additions

- `react-router-dom` ^6.26 — routing.
- No other new deps. React Hook Form, Zod, and the resolvers stay at their current versions.

---

## 3. Wizard Steps

Numbered 1–7. Each step has a **route slug**, a **required-field set** (used for `methods.trigger` on Next), and a **short description** of what the user sees.

| # | Route slug             | Section component           | Required-field set for Next                                             | Notes |
|---|------------------------|-----------------------------|-------------------------------------------------------------------------|-------|
| 1 | `itinerary`            | `FlightItinerarySection`    | `segments.0` (first-segment fields)                                     | User enters the primary flight (origin, destination, date, times, airline, flight number). Marked as the problem flight by default. |
| 2 | `connecting-flights`   | `ConnectingFlightsSection`  | `segments` (whole array — cross-field "exactly one problem flight" rule) | User optionally adds up to 4 more segments (indices 1–4). "Problem flight" checkbox is a radio-group behaviour: selecting one clears the others. Also validates the array cross-field constraint. |
| 3 | `disruption`           | `DisruptionInfoSection` *(new)* | `disruption`                                                        | The CASE_03 form: disruption type radio → branch-specific sub-fields → optional airline motive → incident description textarea. Frontend enforces the same conditional rules as `DisruptionSerializer` so the user cannot submit an invalid combination. |
| 4 | `passenger`            | `PassengerDetailsSection`   | `passenger`, `reservation_number`                                       | Name, DOB, email, phone, address, postal code, reservation number. |
| 5 | `documents`            | `DocumentsSection`          | `boarding_pass`, `id_document`                                          | Two file inputs, PDF/JPG/PNG ≤ 5 MB each. Shows the re-upload banner if hydrated draft has no files. |
| 6 | `consent`              | `GdprSection`               | `gdpr_consent`                                                          | GDPR consent checkbox. Also a summary sentence about what will be shared. |
| 7 | `review`               | `ReviewStep` *(new)*        | (whole form) — submits on Next                                          | Read-only summary of all collected values grouped by section, each with an "Edit" link that navigates back to the corresponding step. Primary CTA is **"Submit claim"** which calls `createCase(...)`. |

Progress bar labels (short form for display): *Itinerary · Connecting flights · Disruption · Passenger · Documents · Consent · Review*.

### Navigation contract

- **Next button:** on click, calls `methods.trigger(fieldsForThisStep)`. If it resolves `true`, mark the step index as "completed" in local state and `navigate(nextPath)`. If it resolves `false`, do nothing (RHF's own error messages already render inline).
- **Back button:** always calls `navigate(-1)` — no validation, no error clearing. Values entered in the current step are preserved in RHF state (and persisted to sessionStorage) regardless of validity.
- **Progress-bar step click:** enabled only for `stepIndex ≤ maxCompletedIndex` and for the current step. Clicks call `navigate(stepPath)` without validation. Disabled steps have `aria-disabled="true"` and are not focusable.
- **Review page Edit link:** `navigate(stepPath, { state: { returnTo: "review" } })`. When the target step's Next button fires, if `location.state?.returnTo === "review"` navigate to `/case/new/review` instead of the step's default `nextPath`.
- **Final submit (Review Next):** validates the entire schema with `handleSubmit(onSubmit)`. `onSubmit` calls `createCase(payload, files)` exactly as CASE_01 does today. On 201, clear sessionStorage and `navigate(`/case/created/${resp.id}`, { state: resp })`. Errors are mapped to the correct step via `applyServerErrors` (existing helper), then the wizard navigates to the first step that has an error and surfaces a banner: *"Please fix the highlighted fields."*

---

## 4. New Component: `DisruptionInfoSection`

This is the only genuinely new section (the other four were built in CASE_01). It lives at `frontend/src/features/case-entry/sections/DisruptionInfoSection.tsx` next to its peers.

### Fields rendered

1. **Disruption type** (radio group, required): *Cancellation · Delay · Denied boarding*. Maps to `disruption.disruption_type` ∈ `{"CANCELLATION", "DELAY", "DENIED_BOARDING"}`.
2. **Conditional block for CANCELLATION:**
   - Cancellation notice (radio, required): *More than 14 days · Less than 14 days · On the day of the flight* → `disruption.cancellation_notice`.
3. **Conditional block for DELAY:**
   - Delay duration (radio, required): *Less than 3 hours · More than 3 hours · Connection lost* → `disruption.delay_duration`.
4. **Conditional block for DENIED_BOARDING:**
   - Voluntary (radio, required): *Yes, I volunteered · No, I was denied* → `disruption.denied_boarding_voluntary` (`"YES"` or `"NO"`).
   - If **No** selected, reason (radio, required): *Overbooked · Aggressive behaviour · Intoxication · Not specified* → `disruption.denied_boarding_reason`.
5. **Airline motive mentioned** (radio, required — only for CANCELLATION and DELAY): *Yes · No · Don't know* → `disruption.airline_motive_mentioned`.
6. **Airline motive** (radio, required — only when mentioned == "YES"): *Technical · Weather · Strike · Airport issue · Crew · Other* → `disruption.airline_motive`.
7. **Incident description** (textarea, required, 1–2000 chars): free-text field with a character counter. Placeholder mirrors the backend example.

### Frontend enum source of truth

A new module `frontend/src/features/case-entry/disruption-enums.ts` exports labelled arrays for each enum, e.g.:

```ts
export const DISRUPTION_TYPES = [
  { value: "CANCELLATION",     label: "Cancellation" },
  { value: "DELAY",            label: "Delay" },
  { value: "DENIED_BOARDING",  label: "Denied boarding" },
] as const;
```

The `value` strings match the backend's `DISRUPTION_TYPE_API_VALUES` (i.e. UNSPECIFIED is deliberately absent).

### Zod schema

Extends `caseFormSchema` with a new `disruptionSchema` (in `schema.ts`) that mirrors the backend's `DisruptionSerializer.validate` gating: unions on `disruption_type`, `superRefine` for the motive/reason conditional rules, and stripping of inapplicable keys via `.transform`. The schema is exported as a standalone name so `<WizardStep>` can pass `fields={['disruption']}` and get a clean per-step validation pass.

---

## 5. Modernised Visual System

Auto-applied by `.github/instructions/frontend-style.instructions.md` whenever any file under `frontend/` is edited. CASE_04 is the first story that actually **creates** the token file and rewrites the CSS Modules.

### Files created

- `frontend/src/styles/tokens.css` — CSS custom properties for the design system.
- `frontend/src/styles/reset.css` — a small reset (`box-sizing: border-box`, margin/padding reset on `body h1 h2 …`, `:focus-visible` outline).

Both imported once from `frontend/src/main.tsx` before `global.css`.

### Token catalogue (summary; full values in the plan)

- **Neutrals:** cool grey scale `--color-neutral-0 (white)` through `--color-neutral-900` at 50/100/200/…/900 steps.
- **Accent:** single blue `--color-accent-500` (`#2563eb`) plus `--color-accent-600`/`700` for hover/active and `--color-accent-50` for tinted backgrounds.
- **Semantic:** `--color-danger-500`, `--color-success-500`, `--color-warning-500`, each with a `-50` tinted-background variant.
- **Spacing:** 4 px base — `--space-1` (4) through `--space-10` (40) plus `--space-12` (48) and `--space-16` (64).
- **Radii:** `--radius-sm` (4), `--radius-md` (8), `--radius-lg` (12), `--radius-pill` (999).
- **Shadows:** `--shadow-sm` (subtle 1-px), `--shadow-md` (card hover), `--shadow-lg` (modals — not used yet).
- **Type:** system font stack, `--font-size-{xs,sm,base,lg,xl,2xl,3xl}`, `--font-weight-{regular,medium,semibold}`, `--line-height-{tight,base,relaxed}`.
- **Motion:** `--motion-duration-fast` (120 ms), `--motion-duration-base` (200 ms), `--motion-ease-standard` (`cubic-bezier(0.4, 0, 0.2, 1)`).

### Component styling rules (enforced by the frontend-style instructions)

- All CSS Modules must reference tokens; no raw hex, no raw `px` for spacing (except 1–2 px for hairlines).
- Buttons: primary (accent 500 background, white text), secondary (transparent, neutral border), destructive (danger 500). All get a 2 px accent-500 focus-visible ring and a 120 ms hover transition.
- Form controls: 1 px neutral-200 border, 8 px radius, 40 px min height, focus-visible ring uses `--color-accent-500` at `box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.25)`.
- Cards / step panels: white background, `--shadow-sm`, 12 px radius, 24 px padding.
- Banners: `bg=<color>-50`, `border=<color>-500`, `text=<color>-700`. Use `role="alert"` for errors, `role="status"` for info.
- Progress bar: pill-shaped step numbers (28 px circle) connected by 2-px `--color-neutral-200` lines. Completed = accent-500 fill with white checkmark. Active = accent-500 border + accent-50 fill. Future = neutral-200 border + white fill.

### Deliverable checklist for the visual pass

- `frontend/src/styles/tokens.css` ✅ new
- `frontend/src/styles/reset.css` ✅ new
- `frontend/src/styles/global.css` — rewrite to use tokens, drop legacy rules.
- `frontend/src/features/case-entry/CaseEntryForm.module.css` — repurposed into `WizardLayout.module.css` (or replaced).
- `frontend/src/features/case-entry/wizard/WizardLayout.module.css` ✅ new
- `frontend/src/features/case-entry/wizard/ProgressBar.module.css` ✅ new
- `frontend/src/features/case-entry/wizard/ReviewStep.module.css` ✅ new
- `frontend/src/features/case-entry/sections/sections.module.css` — refactor to use tokens.
- `frontend/src/features/case-entry/CompensationSummary.module.css` — refactor to use tokens.
- `frontend/src/features/case-entry/AirportAutocomplete.module.css` — refactor to use tokens.

---

## 6. Error Handling & Edge Cases

- **API validation errors on submit** (400 with `payload.<field>: [...]`): the existing `applyServerErrors` helper is reused unchanged. After it runs, look up which step each errored field belongs to (using a static `FIELD_TO_STEP: Record<string, string>` map), pick the earliest one, and `navigate(stepPath)`. Banner *"Please fix the highlighted fields."* rendered above the step content.
- **API throttled (429):** banner *"Too many attempts. Please wait a minute and try again."* on the Review page; stay on Review; do not clear sessionStorage.
- **API network error:** banner *"Could not submit. Please try again."*; stay on Review; do not clear sessionStorage.
- **Compensation preview** (`CompensationSummary`): only mounted on the `/case/created/:id` success page, so preview 5xx-during-typing failures no longer distract the user. Existing throttled/soft-error rendering stays intact.
- **Deep link to a later step with insufficient state:** e.g. user visits `/case/new/review` directly with an empty draft. `<ReviewStep>` runs the whole `caseFormSchema` validation on mount; if invalid, redirect to the first errored step. Same behaviour for `<WizardStep>` when clicked directly (validation-on-mount is NOT done — steps are self-contained editors — but the Next button will always block progression).
- **Refresh mid-file-upload:** files are lost. Documents step banner explains this. All other form state is preserved.
- **Browser Back from step 1:** goes to the previous page in browser history (usually a blank / external site). No custom guard.
- **Success page reload:** `/case/created/:id` reads the created case from `location.state`. If `state` is `null` (e.g. user reloaded), fall back to a minimal message: *"Your claim was submitted. Reference: {id}."* No re-fetch (there is no `GET /api/cases/:id` endpoint in this story).

---

## 7. Testing

New Vitest test files under `frontend/tests/`:

- `wizard-routing.test.tsx` — mounts `<App>` at `/`, asserts redirect to `/case/new/itinerary`; asserts Next button on itinerary step is disabled/blocked until fields valid; asserts clicking Next navigates to `/case/new/connecting-flights`; asserts Back navigates to itinerary.
- `wizard-persistence.test.tsx` — fills step 1, unmounts and remounts the app, asserts values are restored from sessionStorage; asserts files are NOT restored; asserts sessionStorage is cleared after successful submit.
- `wizard-review.test.tsx` — walks the full 7-step happy path, lands on Review, asserts every field is rendered read-only; clicks "Edit passenger", asserts navigation to `/case/new/passenger`; edits a field, clicks Next, asserts return to `/case/new/review`; clicks Submit, mocks the API, asserts navigation to `/case/created/:id`.
- `DisruptionInfoSection.test.tsx` — for each disruption type, asserts the correct conditional fields render; asserts motive is required only when mentioned == YES; asserts reason is required only when voluntary == NO; asserts UNSPECIFIED is not a selectable option.
- `progress-bar.test.tsx` — asserts only completed + current steps are clickable; asserts navigating via a click works; asserts future steps have `aria-disabled="true"`.

Updated tests:

- `CaseEntryForm.test.tsx` — deleted (the component no longer exists as a single form). Content salvageable for `wizard-review.test.tsx`.
- `AirportAutocomplete.test.tsx` — unchanged (the component itself is unchanged).
- `CompensationSummary.test.tsx` — updated to mount inside `<CaseCreatedPage>` with a mocked success state, since the component is no longer rendered inline in the form.

All backend tests remain unchanged. `pytest -q` from `backend/` must still be 109/109.

---

## 8. Migration & Data Compatibility

None. This is a UI-only refactor. Every `Case` row created after this story ships is byte-identical (backend-wise) to a case created before this story — the wizard writes exactly the same multipart POST as the current single-page form. No database migration, no serializer change, no API version bump.

Session drafts stored under previous keys (there are none — this is the first version) require no migration.

---

## 9. Open Questions

None at spec-approval time. All 8 clarifying questions were resolved in the pre-spec brainstorming pass:

1. Back button: always allowed, no validation.
2. Progress-bar clicks: completed steps + current step only.
3. Review "Edit": navigates to the step, returns to Review after Save.
4. Final submit: on Review; success page hosts `CompensationSummary`.
5. File persistence on refresh: banner tells user to re-upload; other fields hydrated from sessionStorage.
6. Connecting Flights: always its own step, even for single-flight itineraries.
7. Step count: 7 (as listed in §3).
8. sessionStorage: one key holding the whole draft as JSON.
