import { useFormContext } from "react-hook-form";

import type { CaseFormValues } from "../schema";
import styles from "./sections.module.css";


export function GdprSection() {
  const { register, formState: { errors } } = useFormContext<CaseFormValues>();
  return (
    <section className={styles.section} aria-labelledby="gdpr-heading">
      <h2 id="gdpr-heading">E-mail &amp; GDPR compliance</h2>
      <label>
        <input type="checkbox" {...register("gdpr_consent")} />
        I agree to the GDPR policy and consent to processing of my personal data
        for the purpose of this compensation claim.
      </label>
      {errors.gdpr_consent && (
        <p className={styles.error}>{errors.gdpr_consent.message}</p>
      )}
    </section>
  );
}
