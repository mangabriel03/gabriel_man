import { deleteJson, getJson } from "./client";


export interface AdminCaseListItem {
  id: string;
  case_date: string;
  flight_number: string | null;
  flight_date: string | null;
  status: string;
}


export interface AdminCaseDeleteResponse {
  detail: string;
}


export function fetchAdminCases(): Promise<AdminCaseListItem[]> {
  return getJson<AdminCaseListItem[]>("/api/admin/cases/");
}


export function deleteAdminCase(caseId: string): Promise<AdminCaseDeleteResponse> {
  return deleteJson<AdminCaseDeleteResponse>(`/api/admin/cases/${caseId}/`);
}