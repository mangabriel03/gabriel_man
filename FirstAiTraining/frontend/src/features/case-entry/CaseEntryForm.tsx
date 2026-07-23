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
      // The backend nests serializer errors under a top-level "payload" key
      // (multipart request field). Unwrap it so its children map directly to
      // RHF field paths like `passenger.email`.
      if (path === "" && key === "payload") {
        applyServerErrors(value, "", setError);
        continue;
      }
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
