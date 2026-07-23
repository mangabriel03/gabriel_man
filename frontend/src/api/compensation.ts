import { ApiError, ApiThrottledError } from "./client";

export interface CompensationLeg {
  from: string;
  to: string;
}

export interface CompensationBreakdownLeg {
  from: string;
  to: string;
  distance_km: number | null;
  source: "airportgap" | "haversine" | null;
  error?: string | null;
}

export interface CompensationPreview {
  distance_km: number;
  compensation_amount_eur: 250 | 400 | 600;
  legs: CompensationBreakdownLeg[];
}

export interface CompensationUnavailableBody {
  detail: string;
  legs: CompensationBreakdownLeg[];
}

export class CompensationUnavailable extends ApiError {
  readonly body: CompensationUnavailableBody;
  constructor(body: CompensationUnavailableBody) {
    super(422, body.detail || "Compensation could not be calculated.");
    this.body = body;
  }
}

export async function previewCompensation(
  legs: CompensationLeg[],
  signal?: AbortSignal,
): Promise<CompensationPreview> {
  const resp = await fetch("/api/compensation/preview/", {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ legs }),
    signal,
  });

  if (resp.status === 429) throw new ApiThrottledError();
  if (resp.status === 422) {
    const body = (await safeJson(resp)) as CompensationUnavailableBody | null;
    throw new CompensationUnavailable(
      body ?? { detail: "Compensation could not be calculated.", legs: [] },
    );
  }
  if (!resp.ok) {
    throw new ApiError(
      resp.status,
      `POST /api/compensation/preview/ failed with ${resp.status}`,
    );
  }

  const raw = (await resp.json()) as {
    distance_km: number | string;
    compensation_amount_eur: 250 | 400 | 600;
    legs: Array<{
      from: string;
      to: string;
      distance_km: number | string | null;
      source: "airportgap" | "haversine" | null;
      error?: string | null;
    }>;
  };
  return {
    distance_km: Number(raw.distance_km),
    compensation_amount_eur: raw.compensation_amount_eur,
    legs: raw.legs.map((l) => ({
      ...l,
      distance_km: l.distance_km === null ? null : Number(l.distance_km),
      error: l.error ?? null,
    })),
  };
}

async function safeJson(resp: Response): Promise<unknown> {
  try {
    return await resp.json();
  } catch {
    return null;
  }
}
