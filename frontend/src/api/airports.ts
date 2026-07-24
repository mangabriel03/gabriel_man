import { getJson } from "./client";
import type { AirportOption } from "../features/case-entry/types";

export function searchAirports(q: string, signal?: AbortSignal): Promise<AirportOption[]> {
  const params = new URLSearchParams({ q });
  return getJson<AirportOption[]>(`/api/airports/?${params.toString()}`, { signal });
}
