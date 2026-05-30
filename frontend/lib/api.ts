"use client";

import type { TokenPair } from "./types";

const ACCESS_KEY = "vr_access";
const REFRESH_KEY = "vr_refresh";

export const tokenStore = {
  get access() {
    return typeof window !== "undefined" ? localStorage.getItem(ACCESS_KEY) : null;
  },
  get refresh() {
    return typeof window !== "undefined" ? localStorage.getItem(REFRESH_KEY) : null;
  },
  set(pair: TokenPair) {
    localStorage.setItem(ACCESS_KEY, pair.accessToken);
    localStorage.setItem(REFRESH_KEY, pair.refreshToken);
  },
  clear() {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
};

export class ApiError extends Error {
  status: number;
  code?: string;
  constructor(status: number, message: string, code?: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

const BASE = "/api/v1";

async function refreshAccessToken(): Promise<boolean> {
  const refresh = tokenStore.refresh;
  if (!refresh) return false;
  const res = await fetch(`${BASE}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refreshToken: refresh }),
  });
  if (!res.ok) return false;
  tokenStore.set(await res.json());
  return true;
}

async function request<T>(path: string, init: RequestInit = {}, retry = true): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  const access = tokenStore.access;
  if (access) headers.set("Authorization", `Bearer ${access}`);

  const res = await fetch(`${BASE}${path}`, { ...init, headers });

  if (res.status === 401 && retry && (await refreshAccessToken())) {
    return request<T>(path, init, false);
  }
  if (res.status === 401) {
    tokenStore.clear();
    if (typeof window !== "undefined") window.location.href = "/login";
    throw new ApiError(401, "نشست منقضی شده است.");
  }
  if (!res.ok) {
    let message = "خطایی رخ داد.";
    let code: string | undefined;
    try {
      const body = await res.json();
      message = body?.error?.message ?? body?.detail ?? message;
      code = body?.error?.code;
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, message, code);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
  patch: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "PATCH", body: body ? JSON.stringify(body) : undefined }),
  put: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "PUT", body: body ? JSON.stringify(body) : undefined }),
};

export async function login(email: string, password: string): Promise<TokenPair> {
  const res = await fetch(`${BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    let message = "ایمیل یا رمز عبور نادرست است.";
    try {
      const body = await res.json();
      message = body?.error?.message ?? message;
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, message);
  }
  const pair: TokenPair = await res.json();
  tokenStore.set(pair);
  return pair;
}
