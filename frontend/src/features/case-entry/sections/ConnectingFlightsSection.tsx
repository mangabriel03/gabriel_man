import { Controller, useFieldArray, useFormContext } from "react-hook-form";

import { AirportAutocomplete } from "../AirportAutocomplete";
import type { CaseFormValues } from "../schema";
import styles from "./sections.module.css";


export function ConnectingFlightsSection() {
  const { control, register, watch, setValue, formState: { errors } } =
    useFormContext<CaseFormValues>();
  const { fields, append, remove } = useFieldArray({ control, name: "segments" });
  const segments = watch("segments");

  const canAdd = fields.length < 5;

  const problemIndex = segments.findIndex((s) => s.is_problem_flight);

  const setProblem = (idx: number) => {
    segments.forEach((_, i) => {
      setValue(`segments.${i}.is_problem_flight`, i === idx, { shouldValidate: true });
    });
  };

  return (
    <section className={styles.section} aria-labelledby="connecting-heading">
      <h2 id="connecting-heading">Connecting flights &amp; problem-flight marker</h2>

      <fieldset>
        <legend>Which segment is the problem flight?</legend>
        {fields.map((f, i) => (
          <label key={f.id} style={{ display: "block" }}>
            <input
              type="radio"
              name="problem-flight"
              checked={problemIndex === i}
              onChange={() => setProblem(i)}
            />
            {i === 0 ? "Primary segment" : `Connecting ${i}`} — {segments[i]?.flight_number || "?"}
          </label>
        ))}
      </fieldset>
      {errors.segments && typeof errors.segments.message === "string" && (
        <p className={styles.error}>{errors.segments.message}</p>
      )}

      {fields.slice(1).map((f, offset) => {
        const idx = offset + 1;
        return (
          <div key={f.id} className={styles.section}>
            <h3>Connecting flight {idx}</h3>
            <div className={styles.grid}>
              <label className={styles.field}>
                Flight date
                <input type="date" {...register(`segments.${idx}.flight_date`)} />
              </label>
              <label className={styles.field}>
                Flight number
                <input {...register(`segments.${idx}.flight_number`)} />
              </label>
              <label className={styles.field}>
                Airline
                <input {...register(`segments.${idx}.airline`)} />
              </label>
              <Controller
                control={control}
                name={`segments.${idx}.departure_airport_iata`}
                render={({ field, fieldState }) => (
                  <AirportAutocomplete
                    id={`dep-${idx}`}
                    label="From"
                    value={field.value}
                    onChange={field.onChange}
                    error={fieldState.error?.message}
                  />
                )}
              />
              <Controller
                control={control}
                name={`segments.${idx}.arrival_airport_iata`}
                render={({ field, fieldState }) => (
                  <AirportAutocomplete
                    id={`arr-${idx}`}
                    label="To"
                    value={field.value}
                    onChange={field.onChange}
                    error={fieldState.error?.message}
                  />
                )}
              />
              <label className={styles.field}>
                Departure time
                <input type="datetime-local" {...register(`segments.${idx}.planned_departure_time`)} />
              </label>
              <label className={styles.field}>
                Arrival time
                <input type="datetime-local" {...register(`segments.${idx}.planned_arrival_time`)} />
              </label>
            </div>
            <div className={styles.actions}>
              <button type="button" onClick={() => remove(idx)}>Remove</button>
            </div>
          </div>
        );
      })}

      <div className={styles.actions}>
        <button
          type="button"
          disabled={!canAdd}
          onClick={() =>
            append({
              order: fields.length,
              flight_date: "",
              flight_number: "",
              airline: "",
              departure_airport_iata: "",
              arrival_airport_iata: "",
              planned_departure_time: "",
              planned_arrival_time: "",
              is_problem_flight: false,
            })
          }
        >
          Add connecting flight
        </button>
      </div>
    </section>
  );
}
