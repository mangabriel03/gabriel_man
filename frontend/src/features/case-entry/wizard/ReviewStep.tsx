import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

import { createCase } from "../../../api/cases";
import { ApiError, ApiThrottledError, ApiValidationError } from "../../../api/client";
import type { CaseCreateResponse, CasePayload } from "../types";
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
