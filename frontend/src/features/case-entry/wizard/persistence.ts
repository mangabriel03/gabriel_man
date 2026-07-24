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
