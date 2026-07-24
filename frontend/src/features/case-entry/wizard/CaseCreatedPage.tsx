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
  const accountEmail = state?.account_email;

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

        <div className={styles.onboarding}>
          <p className={styles.onboardingTitle}>Passenger account ready</p>
          <p className={styles.meta}>
            We emailed a temporary password to {accountEmail ?? "the passenger email on this claim"}.
            The first sign-in will require a password change.
          </p>
          <Link
            to="/login"
            className={styles.secondaryLink}
            state={accountEmail ? { email: accountEmail } : null}
          >
            Go to passenger login
          </Link>
        </div>

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
