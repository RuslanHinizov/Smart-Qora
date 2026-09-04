const TOKEN_KEY = "smart-qora-token";

let onUnauthorized: (() => void) | null = null;

export function setUnauthorizedHandler(handler: () => void) {
  onUnauthorized = handler;
}

export function readToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function writeToken(token: string | null) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* storage disabled — token lives only in memory for this session */
  }
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string,
  ) {
    super(detail || `HTTP ${status}`);
    this.name = "ApiError";
  }
}

type Options = {
  method?: string;
  body?: unknown;
  form?: Record<string, string>;
  params?: Record<string, string | number | undefined>;
};

export async function apiFetch<T>(
  path: string,
  options: Options = {},
): Promise<{ data: T; response: Response }> {
  const url = new URL(`/api${path}`, window.location.origin);
  for (const [key, value] of Object.entries(options.params ?? {})) {
    if (value !== undefined && value !== "") url.searchParams.set(key, String(value));
  }

  const headers: Record<string, string> = {};
  const token = readToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  let body: BodyInit | undefined;
  if (options.form) {
    headers["Content-Type"] = "application/x-www-form-urlencoded";
    body = new URLSearchParams(options.form).toString();
  } else if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(options.body);
  }

  const method = options.method ?? (body !== undefined ? "POST" : "GET");
  const response = await fetch(url, { method, headers, body });

  if (response.status === 401) {
    writeToken(null);
    onUnauthorized?.();
    throw new ApiError(401, "Unauthorized");
  }

  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const payload = await response.json();
      if (typeof payload?.detail === "string") detail = payload.detail;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(response.status, detail);
  }

  const data = response.status === 204 ? (undefined as T) : ((await response.json()) as T);
  return { data, response };
}
