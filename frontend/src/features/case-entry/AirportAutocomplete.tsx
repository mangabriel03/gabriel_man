import { useEffect, useRef, useState } from "react";

import { searchAirports } from "../../api/airports";
import type { AirportOption } from "./types";
import styles from "./AirportAutocomplete.module.css";

interface Props {
  id: string;
  label: string;
  value: string;                    // IATA
  onChange: (iata: string) => void;
  error?: string;
}

export function AirportAutocomplete({ id, label, value, onChange, error }: Props) {
  const [query, setQuery] = useState(value);
  const [options, setOptions] = useState<AirportOption[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const debounceRef = useRef<number | null>(null);
  const blurTimeoutRef = useRef<number | null>(null);
  const controllerRef = useRef<AbortController | null>(null);

  useEffect(() => setQuery(value), [value]);

  useEffect(() => {
    return () => {
      if (debounceRef.current) window.clearTimeout(debounceRef.current);
      if (blurTimeoutRef.current) window.clearTimeout(blurTimeoutRef.current);
      controllerRef.current?.abort();
    };
  }, []);

  useEffect(() => {
    if (debounceRef.current) window.clearTimeout(debounceRef.current);
    if (!query || query.length < 2) {
      setOptions([]);
      return;
    }
    debounceRef.current = window.setTimeout(() => {
      controllerRef.current?.abort();
      const ctrl = new AbortController();
      controllerRef.current = ctrl;
      setLoading(true);
      setFetchError(null);
      searchAirports(query, ctrl.signal)
        .then((rows) => setOptions(rows))
        .catch((err) => {
          if ((err as { name?: string }).name !== "AbortError") {
            setFetchError("Could not load airports.");
          }
        })
        .finally(() => setLoading(false));
    }, 250);
    return () => {
      if (debounceRef.current) window.clearTimeout(debounceRef.current);
    };
  }, [query]);

  return (
    <div className={styles.wrapper}>
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        type="text"
        value={query}
        onChange={(e) => {
          setQuery(e.target.value.toUpperCase());
          setOpen(true);
        }}
        onBlur={() => {
          if (blurTimeoutRef.current) window.clearTimeout(blurTimeoutRef.current);
          blurTimeoutRef.current = window.setTimeout(() => setOpen(false), 100);
        }}
        onFocus={() => setOpen(true)}
        aria-invalid={!!error}
        aria-describedby={error ? `${id}-err` : undefined}
        autoComplete="off"
      />
      {open && query.length >= 2 && (
        <ul className={styles.dropdown} role="listbox">
          {loading && <li className={styles.hint}>Loading…</li>}
          {!loading && !fetchError && options.length === 0 && (
            <li className={styles.hint}>No matches</li>
          )}
          {fetchError && <li className={styles.hint}>{fetchError}</li>}
          {options.map((opt) => (
            <li
              key={opt.iata}
              role="option"
              aria-selected={value === opt.iata}
              className={styles.option}
              onMouseDown={(e) => {
                e.preventDefault();
                onChange(opt.iata);
                setQuery(opt.iata);
                setOpen(false);
              }}
            >
              <strong>{opt.iata}</strong> — {opt.name} ({opt.city}, {opt.country})
            </li>
          ))}
        </ul>
      )}
      {error && (
        <p id={`${id}-err`} className={styles.error}>
          {error}
        </p>
      )}
    </div>
  );
}
