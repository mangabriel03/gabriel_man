import { getJson, postJson } from "./client";


export interface LoginResponse {
  email: string;
  first_name: string;
  last_name: string;
  role: string;
  must_change_password: boolean;
}

export interface ChangePasswordResponse {
  must_change_password: boolean;
}

export interface AdminNavigationAction {
  key: string;
  label: string;
  href: string;
  description: string;
}

export interface AdminNavigationResponse {
  actions: AdminNavigationAction[];
}

export function loginPassenger(email: string, password: string): Promise<LoginResponse> {
  return postJson<LoginResponse>("/api/auth/login/", { email, password });
}

export function changePassengerPassword(
  email: string,
  currentPassword: string,
  newPassword: string,
): Promise<ChangePasswordResponse> {
  return postJson<ChangePasswordResponse>("/api/auth/change-password/", {
    email,
    current_password: currentPassword,
    new_password: newPassword,
  });
}

export function fetchAdminNavigation(): Promise<AdminNavigationResponse> {
  return getJson<AdminNavigationResponse>("/api/admin/navigation/");
}