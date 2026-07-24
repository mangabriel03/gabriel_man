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
