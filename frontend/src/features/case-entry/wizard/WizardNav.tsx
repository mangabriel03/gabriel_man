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
