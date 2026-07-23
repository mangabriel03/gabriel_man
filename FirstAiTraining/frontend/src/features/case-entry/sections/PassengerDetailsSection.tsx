import { useFormContext } from "react-hook-form";

import type { CaseFormValues } from "../schema";
import styles from "./sections.module.css";


export function PassengerDetailsSection() {
  const { register, formState: { errors } } = useFormContext<CaseFormValues>();
  const perr = errors.passenger;
  return (
    <section className={styles.section} aria-labelledby="passenger-heading">
      <h2 id="passenger-heading">Passenger details</h2>
      <div className={styles.grid}>
        <label className={styles.field}>
          First name
          <input {...register("passenger.first_name")} />
          {perr?.first_name && <span className={styles.error}>{perr.first_name.message}</span>}
        </label>
        <label className={styles.field}>
          Last name
          <input {...register("passenger.last_name")} />
          {perr?.last_name && <span className={styles.error}>{perr.last_name.message}</span>}
        </label>
        <label className={styles.field}>
          Date of birth
          <input type="date" {...register("passenger.date_of_birth")} />
          {perr?.date_of_birth && <span className={styles.error}>{perr.date_of_birth.message}</span>}
        </label>
        <label className={styles.field}>
          Email
          <input type="email" {...register("passenger.email")} />
          {perr?.email && <span className={styles.error}>{perr.email.message}</span>}
        </label>
        <label className={styles.field}>
          Phone
          <input type="tel" {...register("passenger.phone")} />
          {perr?.phone && <span className={styles.error}>{perr.phone.message}</span>}
        </label>
        <label className={styles.field}>
          Address
          <input {...register("passenger.address")} />
          {perr?.address && <span className={styles.error}>{perr.address.message}</span>}
        </label>
        <label className={styles.field}>
          Postal code
          <input {...register("passenger.postal_code")} />
          {perr?.postal_code && <span className={styles.error}>{perr.postal_code.message}</span>}
        </label>
        <label className={styles.field}>
          Reservation number
          <input {...register("reservation_number")} />
          {errors.reservation_number && (
            <span className={styles.error}>{errors.reservation_number.message}</span>
          )}
        </label>
      </div>
    </section>
  );
}
