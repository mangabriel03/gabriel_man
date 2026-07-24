import { Controller, useFormContext } from "react-hook-form";

import type { CaseFormValues } from "../schema";
import styles from "./sections.module.css";


function FileField(props: {
  id: string;
  label: string;
  name: "boarding_pass" | "id_document";
}) {
  const { control, formState: { errors } } = useFormContext<CaseFormValues>();
  return (
    <Controller
      control={control}
      name={props.name}
      render={({ field }) => (
        <label className={styles.field} htmlFor={props.id}>
          {props.label}
          <input
            id={props.id}
            type="file"
            accept="application/pdf,image/jpeg,image/png"
            onChange={(e) => field.onChange(e.target.files?.[0] ?? undefined)}
          />
          {errors[props.name] && (
            <span className={styles.error}>{String(errors[props.name]?.message)}</span>
          )}
        </label>
      )}
    />
  );
}


export function DocumentsSection() {
  return (
    <section className={styles.section} aria-labelledby="docs-heading">
      <h2 id="docs-heading">Documents</h2>
      <div className={styles.grid}>
        <FileField id="bp" label="Boarding pass (PDF / JPG / PNG, ≤ 5 MB)" name="boarding_pass" />
        <FileField id="id" label="ID or passport (PDF / JPG / PNG, ≤ 5 MB)" name="id_document" />
      </div>
    </section>
  );
}
