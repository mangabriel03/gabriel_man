import { postMultipart } from "./client";
import type { CasePayload, CaseCreateResponse } from "../features/case-entry/types";

export function createCase(
  payload: CasePayload,
  files: { boarding_pass: File; id_document: File },
): Promise<CaseCreateResponse> {
  const form = new FormData();
  form.append("payload", JSON.stringify(payload));
  form.append("boarding_pass", files.boarding_pass);
  form.append("id_document", files.id_document);
  return postMultipart<CaseCreateResponse>("/api/cases/", form);
}
