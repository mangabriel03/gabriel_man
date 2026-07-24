import { Controller, useFormContext } from "react-hook-form";

import { AirportAutocomplete } from "../AirportAutocomplete";
import type { CaseFormValues } from "../schema";
import styles from "./sections.module.css";


export function FlightItinerarySection() {
  const { register, control, formState: { errors } } = useFormContext<CaseFormValues>();
  const segErr = errors.segments?.[0];
  return (
    <section className={styles.section} aria-labelledby="itinerary-heading">
      <h2 id="itinerary-heading">Primary flight itinerary</h2>
      <div className={styles.grid}>
        <label className={styles.field}>
          Flight date
          <input type="date" {...register("segments.0.flight_date")} />
          {segErr?.flight_date && <span className={styles.error}>{segErr.flight_date.message}</span>}
        </label>
        <label className={styles.field}>
          Flight number
          <input {...register("segments.0.flight_number")} />
          {segErr?.flight_number && <span className={styles.error}>{segErr.flight_number.message}</span>}
        </label>
        <label className={styles.field}>
          Airline
          <input {...register("segments.0.airline")} />
          {segErr?.airline && <span className={styles.error}>{segErr.airline.message}</span>}
        </label>
        <Controller
          control={control}
          name="segments.0.departure_airport_iata"
          render={({ field, fieldState }) => (
            <AirportAutocomplete
              id="dep-0"
              label="Departing airport"
              value={field.value}
              onChange={field.onChange}
              error={fieldState.error?.message}
            />
          )}
        />
        <Controller
          control={control}
          name="segments.0.arrival_airport_iata"
          render={({ field, fieldState }) => (
            <AirportAutocomplete
              id="arr-0"
              label="Destination airport"
              value={field.value}
              onChange={field.onChange}
              error={fieldState.error?.message}
            />
          )}
        />
        <label className={styles.field}>
          Planned departure time
          <input type="datetime-local" {...register("segments.0.planned_departure_time")} />
          {segErr?.planned_departure_time && (
            <span className={styles.error}>{segErr.planned_departure_time.message}</span>
          )}
        </label>
        <label className={styles.field}>
          Planned arrival time
          <input type="datetime-local" {...register("segments.0.planned_arrival_time")} />
          {segErr?.planned_arrival_time && (
            <span className={styles.error}>{segErr.planned_arrival_time.message}</span>
          )}
        </label>
      </div>
    </section>
  );
}
