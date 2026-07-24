import { getJson, postJson } from "./client";


export interface AdminUserListItem {
  id: number;
  name: string;
  email: string;
  role: string;
  assigned_case_count: number;
}


export interface AdminUserCreateRequest {
  first_name: string;
  last_name: string;
  email: string;
  password: string;
}


export interface AdminUserCreateResponse extends AdminUserListItem {
  detail: string;
}


export function fetchAdminUsers(): Promise<AdminUserListItem[]> {
  return getJson<AdminUserListItem[]>("/api/admin/users/");
}


export function createAdminUser(payload: AdminUserCreateRequest): Promise<AdminUserCreateResponse> {
  return postJson<AdminUserCreateResponse>("/api/admin/users/", payload);
}