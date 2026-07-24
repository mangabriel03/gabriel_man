import { useEffect, useMemo, useRef, useState } from "react";
import { useFormContext, useWatch } from "react-hook-form";

import { ApiError, ApiThrottledError } from "../../api/client";
import {
  CompensationUnavailable,
  previewCompensation,
  type CompensationLeg,
  type CompensationPreview,
} from "../../api/compensation";
import type { CaseFormValues } from "./schema";
import styles from "./CompensationSummary.module.css";

type ViewState =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "success"; data: CompensationPreview }
  | { kind: "soft-error"; message: string }
  | { kind: "throttled" };

function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(t);
  }, [value, delayMs]);
  return debounced;
}

const IATA_RX = /^[A-Za-z]{3}$/;
const NUMBER_FMT = new Intl.NumberFormat("en", { useGrouping: true });

export function CompensationSummary() {
  const { control } = useFormContext<CaseFormValues>();
  const segments = useWatch({ control, name: "segments" });

  const legs: CompensationLeg[] = useMemo(() => {
    if (!Array.isArray(segments)) return [];
    return [...segments]
      .sort((a, b) => (a?.order ?? 0) - (b?.order ?? 0))
      .map((s) => ({
        from: (s?.departure_airport_iata ?? "").toUpperCase(),
        to: (s?.arrival_airport_iata ?? "").toUpperCase(),
      }))
      .filter(
        (l) => IATA_RX.test(l.from) && IATA_RX.test(l.to) && l.from !== l.to,
      );
  }, [segments]);

  // Debounce the serialised leg list so rapid typing collapses into one call.
  const legsKey = JSON.stringify(legs);
  const debouncedKey = useDebouncedValue(legsKey, 400);

  const [state, setState] = useState<ViewState>({ kind: "idle" });
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    // Cancel any in-flight request from a previous key.
    abortRef.current?.abort();

    const currentLegs: CompensationLeg[] = JSON.parse(debouncedKey);
    if (currentLegs.length === 0) {
      setState({ kind: "idle" });
      return;
    }

    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setState({ kind: "loading" });

    previewCompensation(currentLegs, ctrl.signal)
      .then((data) => {
        if (ctrl.signal.aborted) return;
        setState({ kind: "success", data });
      })
      .catch((err) => {
        if (ctrl.signal.aborted || err?.name === "AbortError") return;
        if (err instanceof ApiThrottledError) {
          setState({ kind: "throttled" });
          return;
        }
        if (err instanceof CompensationUnavailable || err instanceof ApiError) {
          setState({
            kind: "soft-error",
            message:
              "We couldn't calculate compensation yet — check that all airport codes are valid.",
          });
          return;
        }
        setState({
          kind: "soft-error",
          message:
            "We couldn't calculate compensation yet — check that all airport codes are valid.",
        });
      });

    return () => ctrl.abort();
  }, [debouncedKey]);

  if (state.kind === "idle") return null;

  return (
    <section
      className={styles.summary}
      aria-live="polite"
      data-testid="compensation-summary"
    >
      <h2>Estimated compensation</h2>
      {state.kind === "loading" && (
        <p className={styles.pending}>Calculating compensation…</p>
      )}
      {state.kind === "success" && (
        <>
          <p className={styles.amount}>
            <strong>{state.data.compensation_amount_eur} €</strong>
          </p>
          <p className={styles.detail}>
            Total flight distance:{" "}
            {NUMBER_FMT.format(Math.round(state.data.distance_km))} km across{" "}
            {state.data.legs.length} leg(s).
          </p>
        </>
      )}
      {state.kind === "soft-error" && (
        <p className={styles.warning} role="status">
          {state.message}
        </p>
      )}
      {state.kind === "throttled" && (
        <p className={styles.warning} role="status">
          Too many attempts; retrying shortly.
        </p>
      )}
    </section>
  );
}
