import { useEffect, type ReactNode } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import type { FieldPath } from "react-hook-form";

import type { CaseFormValues } from "../schema";
import { useWizard } from "./WizardLayout";

interface Props {
  index: number;
  nextPath: string;
  fields: readonly string[];
  children: ReactNode;
}

export function WizardStep({ index, nextPath, fields, children }: Props) {
  const { methods, markCompleted, setNextHandler, setNextLabel, setBanner } = useWizard();
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    setNextLabel("Next");
    setBanner(null);
    const handler = async () => {
      const ok = await methods.trigger(fields as FieldPath<CaseFormValues>[]);
      if (!ok) return;
      markCompleted(index);
      const returnTo = (location.state as { returnTo?: string } | null)?.returnTo;
      if (returnTo === "review") {
        navigate("/case/new/review");
      } else {
        navigate(nextPath);
      }
    };
    setNextHandler(() => handler);
    return () => setNextHandler(null);
  }, [
    methods, fields, index, nextPath, navigate, location.state,
    markCompleted, setNextHandler, setNextLabel, setBanner,
  ]);

  return <>{children}</>;
}
