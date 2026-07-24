import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { FormProvider, useForm, type UseFormReturn } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Outlet, useLocation } from "react-router-dom";

import { caseFormSchema, type CaseFormValues } from "../schema";
import { emptyValues } from "./empty-values";
import { loadDraft, saveDraft, STEPS } from "./persistence";
import { ProgressBar } from "./ProgressBar";
import { WizardNav } from "./WizardNav";
import styles from "./WizardLayout.module.css";

interface WizardContextValue {
  methods: UseFormReturn<CaseFormValues>;
  currentIndex: number;
  maxCompletedIndex: number;
  markCompleted: (index: number) => void;
  banner: string | null;
  setBanner: (msg: string | null) => void;
  /** Registered by the current <WizardStep> so <WizardNav> can invoke it. */
  nextHandler: (() => void) | null;
  setNextHandler: (h: (() => void) | null) => void;
  /** Overridable per-step: Review step sets "Submit claim". */
  nextLabel: string;
  setNextLabel: (label: string) => void;
  submitting: boolean;
  setSubmitting: (v: boolean) => void;
}

const WizardCtx = createContext<WizardContextValue | null>(null);

export function useWizard(): WizardContextValue {
  const ctx = useContext(WizardCtx);
  if (!ctx) throw new Error("useWizard must be used inside <WizardLayout>");
  return ctx;
}

function slugFromPath(pathname: string): string {
  const parts = pathname.split("/").filter(Boolean);
  return parts[parts.length - 1] ?? "";
}

export function WizardLayout() {
  const location = useLocation();
  const currentIndex = Math.max(
    0,
    STEPS.findIndex((s) => s.slug === slugFromPath(location.pathname)),
  );

  const methods = useForm<CaseFormValues>({
    resolver: zodResolver(caseFormSchema),
    defaultValues: emptyValues,
    mode: "onTouched",
  });

  const [maxCompletedIndex, setMaxCompletedIndex] = useState(0);
  const [banner, setBanner] = useState<string | null>(null);
  const [nextHandler, setNextHandler] = useState<(() => void) | null>(null);
  const [nextLabel, setNextLabel] = useState("Next");
  const [submitting, setSubmitting] = useState(false);

  // Hydrate from sessionStorage once on mount.
  const hydrated = useRef(false);
  useEffect(() => {
    if (hydrated.current) return;
    hydrated.current = true;
    const draft = loadDraft();
    if (draft) {
      methods.reset({ ...emptyValues, ...draft });
    }
  }, [methods]);

  // Persist on change (debounced 400 ms).
  useEffect(() => {
    let timeout: ReturnType<typeof setTimeout> | null = null;
    const sub = methods.watch((values) => {
      if (timeout) clearTimeout(timeout);
      timeout = setTimeout(() => {
        saveDraft(values as CaseFormValues);
      }, 400);
    });
    return () => {
      if (timeout) clearTimeout(timeout);
      sub.unsubscribe();
    };
  }, [methods]);

  const markCompleted = useCallback((index: number) => {
    setMaxCompletedIndex((prev) => Math.max(prev, index + 1));
  }, []);

  const ctxValue = useMemo<WizardContextValue>(
    () => ({
      methods,
      currentIndex,
      maxCompletedIndex,
      markCompleted,
      banner,
      setBanner,
      nextHandler,
      setNextHandler,
      nextLabel,
      setNextLabel,
      submitting,
      setSubmitting,
    }),
    [methods, currentIndex, maxCompletedIndex, banner, nextHandler, nextLabel, submitting],
  );

  return (
    <WizardCtx.Provider value={ctxValue}>
      <FormProvider {...methods}>
        <main className={styles.wrapper}>
          <header className={styles.header}>
            <h1 className={styles.title}>File a compensation claim</h1>
            <p className={styles.subtitle}>
              EU 261/2004 — takes about 5 minutes.
            </p>
          </header>
          <ProgressBar />
          {banner && (
            <div className={styles.banner} role="alert">
              {banner}
            </div>
          )}
          <div className={styles.panel}>
            <Outlet />
          </div>
          <WizardNav />
        </main>
      </FormProvider>
    </WizardCtx.Provider>
  );
}
