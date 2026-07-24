import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { loginPassenger } from "../../api/auth";
import { ApiError, ApiValidationError } from "../../api/client";
import styles from "./AuthCard.module.css";


type LoginState = {
  email?: string;
  banner?: string;
};


export function LoginPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const state = (location.state as LoginState | null) ?? null;
  const [email, setEmail] = useState(state?.email ?? "");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(state?.banner ?? null);
  const [success, setSuccess] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    setInfo(null);
    setSuccess(null);
    try {
      const response = await loginPassenger(email, password);
      if (response.role === "SYSTEM_ADMIN") {
        navigate("/admin");
        return;
      }
      if (response.must_change_password) {
        navigate("/account/change-password", {
          state: {
            email: response.email,
            currentPassword: password,
          },
        });
        return;
      }
      setSuccess(`Signed in as ${response.email}. Your password is already up to date.`);
    } catch (err) {
      if (err instanceof ApiValidationError) {
        const detail = err.fieldErrors.detail;
        setError(typeof detail === "string" ? detail : "Could not sign in.");
      } else if (err instanceof ApiError) {
        setError("Could not sign in right now. Please try again.");
      } else {
        setError("Unexpected error. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className={styles.page}>
      <div className={styles.shell}>
        <section className={styles.card} aria-labelledby="login-title">
          <p className={styles.eyebrow}>Passenger access</p>
          <h1 id="login-title" className={styles.title}>Sign in to AirAssist</h1>
          <p className={styles.intro}>
            Use the email address from your passenger claim and the temporary password sent by email.
          </p>

          {info && <div className={`${styles.banner} ${styles.bannerInfo}`}>{info}</div>}
          {error && <div className={`${styles.banner} ${styles.bannerError}`}>{error}</div>}
          {success && <div className={`${styles.banner} ${styles.bannerSuccess}`}>{success}</div>}

          <form className={styles.form} onSubmit={onSubmit}>
            <div className={styles.field}>
              <label className={styles.label} htmlFor="email">Email address</label>
              <input
                id="email"
                className={styles.input}
                type="email"
                autoComplete="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
              />
            </div>
            <div className={styles.field}>
              <label className={styles.label} htmlFor="password">Password</label>
              <input
                id="password"
                className={styles.input}
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
            </div>
            <div className={styles.actions}>
              <button className={styles.primaryButton} type="submit" disabled={submitting}>
                {submitting ? "Signing in..." : "Sign in"}
              </button>
              <Link to="/case/new/itinerary">Back to claim form</Link>
            </div>
          </form>
        </section>
      </div>
    </main>
  );
}