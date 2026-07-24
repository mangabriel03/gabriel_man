import { useMemo, useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";

import { changePassengerPassword } from "../../api/auth";
import { ApiError, ApiValidationError } from "../../api/client";
import styles from "./AuthCard.module.css";


type ChangePasswordState = {
  email?: string;
  currentPassword?: string;
};


export function ChangePasswordPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const state = useMemo(() => (location.state as ChangePasswordState | null) ?? null, [location.state]);
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (!state?.email || !state.currentPassword) {
    return <Navigate to="/login" replace state={{ banner: "Sign in first to change your temporary password." }} />;
  }

  const email = state.email;
  const currentPassword = state.currentPassword;

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (newPassword !== confirmPassword) {
      setError("The new passwords do not match.");
      return;
    }

    setSubmitting(true);
    try {
      await changePassengerPassword(email, currentPassword, newPassword);
      navigate("/login", {
        replace: true,
        state: {
          email,
          banner: "Password changed. Sign in again with your new password.",
        },
      });
    } catch (err) {
      if (err instanceof ApiValidationError) {
        const detail = err.fieldErrors.detail;
        const fieldMessage = err.fieldErrors.new_password;
        if (typeof detail === "string") {
          setError(detail);
        } else if (Array.isArray(fieldMessage) && typeof fieldMessage[0] === "string") {
          setError(fieldMessage[0]);
        } else {
          setError("Could not change your password.");
        }
      } else if (err instanceof ApiError) {
        setError("Could not change your password right now. Please try again.");
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
        <section className={styles.card} aria-labelledby="change-password-title">
          <p className={styles.eyebrow}>First sign-in</p>
          <h1 id="change-password-title" className={styles.title}>Change your temporary password</h1>
          <p className={styles.intro}>
            For security, the first login requires a new password before you continue.
          </p>

          <div className={`${styles.banner} ${styles.bannerInfo}`}>
            Signed in as {email}. Choose a password with at least 12 characters.
          </div>
          {error && <div className={`${styles.banner} ${styles.bannerError}`}>{error}</div>}

          <form className={styles.form} onSubmit={onSubmit}>
            <div className={styles.field}>
              <label className={styles.label} htmlFor="new-password">New password</label>
              <input
                id="new-password"
                className={styles.input}
                type="password"
                autoComplete="new-password"
                value={newPassword}
                onChange={(event) => setNewPassword(event.target.value)}
                aria-invalid={Boolean(error) && newPassword.length > 0}
              />
            </div>
            <div className={styles.field}>
              <label className={styles.label} htmlFor="confirm-password">Confirm new password</label>
              <input
                id="confirm-password"
                className={styles.input}
                type="password"
                autoComplete="new-password"
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                aria-invalid={Boolean(error) && confirmPassword.length > 0}
              />
            </div>
            <p className={styles.finePrint}>
              You will use this new password together with your email address on future sign-ins.
            </p>
            <div className={styles.actions}>
              <button className={styles.primaryButton} type="submit" disabled={submitting}>
                {submitting ? "Updating..." : "Update password"}
              </button>
            </div>
          </form>
        </section>
      </div>
    </main>
  );
}