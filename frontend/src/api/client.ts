export class ApiError extends Error {
  readonly status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export class ApiValidationError extends ApiError {
  readonly fieldErrors: Record<string, unknown>;
  constructor(fieldErrors: Record<string, unknown>) {
    super(400, "Validation failed");
    this.fieldErrors = fieldErrors;
  }
}

export class ApiThrottledError extends ApiError {
  constructor() {
    super(429, "Too many attempts. Please wait a moment and try again.");
  }
}

export async function getJson<T>(url: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(url, { ...init, headers: { Accept: "application/json", ...(init?.headers ?? {}) } });
  if (!resp.ok) throw new ApiError(resp.status, `GET ${url} failed with ${resp.status}`);
  return (await resp.json()) as T;
}

export async function postMultipart<T>(url: string, form: FormData): Promise<T> {
  const resp = await fetch(url, { method: "POST", body: form });
  if (resp.status === 429) throw new ApiThrottledError();
  if (resp.status === 400) {
    const errBody = await safeJson(resp);
    throw new ApiValidationError(errBody ?? {});
  }
  if (!resp.ok) throw new ApiError(resp.status, `POST ${url} failed with ${resp.status}`);
  return (await resp.json()) as T;
}

export async function postJson<T>(url: string, body: unknown): Promise<T> {
  const resp = await fetch(url, {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  if (resp.status === 429) throw new ApiThrottledError();
  if (resp.status === 400) {
    const errBody = await safeJson(resp);
    throw new ApiValidationError(errBody ?? {});
  }
  if (!resp.ok) throw new ApiError(resp.status, `POST ${url} failed with ${resp.status}`);
  return (await resp.json()) as T;
}

export async function deleteJson<T>(url: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(url, {
    method: "DELETE",
    headers: {
      Accept: "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });
  if (!resp.ok) throw new ApiError(resp.status, `DELETE ${url} failed with ${resp.status}`);
  return (await resp.json()) as T;
}

async function safeJson(resp: Response): Promise<Record<string, unknown> | null> {
  try { return (await resp.json()) as Record<string, unknown>; }
  catch { return null; }
}
