const STORAGE_KEY = "vibe_trading_api_auth_key";
const ADMIN_TOKEN_KEY = "vibe_trading_admin_token";

export function getApiAuthKey(): string {
  return window.localStorage.getItem(STORAGE_KEY) || "";
}

export function setApiAuthKey(value: string): void {
  const trimmed = value.trim();
  if (trimmed) {
    window.localStorage.setItem(STORAGE_KEY, trimmed);
  } else {
    window.localStorage.removeItem(STORAGE_KEY);
  }
}

export function getAdminToken(): string {
  return window.localStorage.getItem(ADMIN_TOKEN_KEY) || "";
}

export function setAdminToken(value: string): void {
  const trimmed = value.trim();
  if (trimmed) {
    window.localStorage.setItem(ADMIN_TOKEN_KEY, trimmed);
  } else {
    window.localStorage.removeItem(ADMIN_TOKEN_KEY);
  }
}

export function authHeaders(): Record<string, string> {
  const key = getApiAuthKey();
  const token = getAdminToken();
  const headers: Record<string, string> = {};
  if (key) {
    headers["Authorization"] = `Bearer ${key}`;
  }
  if (token) {
    headers["X-Admin-Token"] = token;
  }
  return headers;
}

export function authQuerySuffix(): string {
  const key = getApiAuthKey();
  return key ? `api_key=${encodeURIComponent(key)}` : "";
}

export function withAuthQuery(url: string): string {
  const suffix = authQuerySuffix();
  if (!suffix) return url;
  return `${url}${url.includes("?") ? "&" : "?"}${suffix}`;
}

/** Returns true when the user has successfully elevated to admin in this session. */
export function isAdminElevated(): boolean {
  return Boolean(window.localStorage.getItem(ADMIN_TOKEN_KEY));
}
