"use client";

const DEFAULT_API_BASE = "http://127.0.0.1:8000";

export function apiBases() {
  const bases = [process.env.NEXT_PUBLIC_INSIGHTSYNC_API_BASE, DEFAULT_API_BASE];

  if (typeof window !== "undefined") {
    const localOverride = window.localStorage.getItem("INSIGHTSYNC_API_BASE");
    if (localOverride) bases.unshift(localOverride);
  }

  return Array.from(
    new Set(
      bases
        .filter((base): base is string => Boolean(base))
        .map((base) => base.replace(/\/$/, ""))
    )
  );
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const errors: string[] = [];

  for (const base of apiBases()) {
    try {
      const response = await fetch(`${base}${path}`, {
        cache: "no-store",
        ...init,
        headers: {
          "Content-Type": "application/json",
          ...init?.headers,
        },
      });

      if (!response.ok) {
        throw new Error(`${path} returned ${response.status}`);
      }

      return response.json() as Promise<T>;
    } catch (error) {
      errors.push(
        `${base}${path}: ${error instanceof Error ? error.message : "failed"}`
      );
    }
  }

  throw new Error(errors.join("; "));
}

export function getJson<T>(path: string) {
  return requestJson<T>(path);
}

export function postJson<TResponse, TBody>(path: string, body: TBody) {
  return requestJson<TResponse>(path, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function putJson<TResponse, TBody>(path: string, body: TBody) {
  return requestJson<TResponse>(path, {
    method: "PUT",
    body: JSON.stringify(body),
  });
}
