import { useFormContext, useWatch } from "react-hook-form";

import {
  AIRLINE_MOTIVES,
  CANCELLATION_NOTICES,
  DELAY_DURATIONS,
  DENIED_BOARDING_REASONS,
  DISRUPTION_TYPES,
  INCIDENT_DESCRIPTION_MAX,
  MOTIVE_MENTIONED,
} from "../disruption-enums";
import type { CaseFormValues } from "../schema";
import styles from "./sections.module.css";

function RadioGroup<T extends string>(props: {
  legend: string;
  name: string;
  options: readonly { value: T; label: string }[];
  error?: string;
}) {
  const { register } = useFormContext<CaseFormValues>();
  return (
    <fieldset className={styles.fieldset}>
      <legend>{props.legend}</legend>
      <div className={styles.radioGroup}>
        {props.options.map((opt) => (
          <label key={opt.value} className={styles.radio}>
            <input type="radio" value={opt.value} {...register(props.name as never)} />
            <span>{opt.label}</span>
          </label>
        ))}
      </div>
      {props.error && <p className={styles.error}>{props.error}</p>}
    </fieldset>
  );
}

export function DisruptionInfoSection() {
  const {
    register,
    control,
    formState: { errors },
  } = useFormContext<CaseFormValues>();

  const disruption = useWatch({ control, name: "disruption" });
  const disruptionType = disruption?.disruption_type;
  const mentioned = disruption?.airline_motive_mentioned;
  const voluntary = disruption?.denied_boarding_voluntary;
  const description = disruption?.incident_description ?? "";

  const dErrors = errors.disruption ?? {};

  return (
    <section className={styles.section} aria-labelledby="disruption-heading">
      <h2 id="disruption-heading">Disruption information</h2>

      <RadioGroup
        legend="What happened to your flight?"
        name="disruption.disruption_type"
        options={DISRUPTION_TYPES}
        error={
          typeof dErrors === "object" && "disruption_type" in dErrors
            ? (dErrors as { disruption_type?: { message?: string } }).disruption_type?.message
            : undefined
        }
      />

      {disruptionType === "CANCELLATION" && (
        <RadioGroup
          legend="When were you informed of the cancellation?"
          name="disruption.cancellation_notice"
          options={CANCELLATION_NOTICES}
          error={
            (dErrors as { cancellation_notice?: { message?: string } })
              .cancellation_notice?.message
          }
        />
      )}

      {disruptionType === "DELAY" && (
        <RadioGroup
          legend="How long was the delay?"
          name="disruption.delay_duration"
          options={DELAY_DURATIONS}
          error={
            (dErrors as { delay_duration?: { message?: string } })
              .delay_duration?.message
          }
        />
      )}

      {disruptionType === "DENIED_BOARDING" && (
        <>
          <RadioGroup
            legend="Was boarding denied voluntarily?"
            name="disruption.denied_boarding_voluntary"
            options={[
              { value: "YES", label: "Yes, I volunteered" },
              { value: "NO", label: "No, I was denied" },
            ]}
            error={
              (dErrors as { denied_boarding_voluntary?: { message?: string } })
                .denied_boarding_voluntary?.message
            }
          />
          {voluntary === "NO" && (
            <RadioGroup
              legend="Reason boarding was denied"
              name="disruption.denied_boarding_reason"
              options={DENIED_BOARDING_REASONS}
              error={
                (dErrors as { denied_boarding_reason?: { message?: string } })
                  .denied_boarding_reason?.message
              }
            />
          )}
        </>
      )}

      {(disruptionType === "CANCELLATION" || disruptionType === "DELAY") && (
        <>
          <RadioGroup
            legend="Did the airline mention a reason?"
            name="disruption.airline_motive_mentioned"
            options={MOTIVE_MENTIONED}
            error={
              (dErrors as { airline_motive_mentioned?: { message?: string } })
                .airline_motive_mentioned?.message
            }
          />
          {mentioned === "YES" && (
            <RadioGroup
              legend="Which reason did the airline give?"
              name="disruption.airline_motive"
              options={AIRLINE_MOTIVES}
              error={
                (dErrors as { airline_motive?: { message?: string } })
                  .airline_motive?.message
              }
            />
          )}
        </>
      )}

      <label className={styles.field}>
        <span>Describe what happened</span>
        <textarea
          rows={5}
          maxLength={INCIDENT_DESCRIPTION_MAX}
          placeholder="e.g. Flight was delayed 5 hours; we were told there was a technical fault."
          {...register("disruption.incident_description")}
        />
        <span className={styles.counter}>
          {description.length} / {INCIDENT_DESCRIPTION_MAX}
        </span>
        {(dErrors as { incident_description?: { message?: string } })
          .incident_description?.message && (
          <span className={styles.error}>
            {(dErrors as { incident_description?: { message?: string } })
              .incident_description!.message}
          </span>
        )}
      </label>
    </section>
  );
}
