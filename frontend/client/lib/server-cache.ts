import "server-only";

import { getRedisClient } from "./redis";

const CACHE_PREFIX = "client-cache:";

function safeParse<T>(value: string | null): T | null {
  if (!value) return null;
  try {
    return JSON.parse(value) as T;
  } catch {
    return null;
  }
}

export async function getCachedJson<T>(
  key: string,
  ttlSeconds: number,
  fetcher: () => Promise<T>
): Promise<T> {
  const client = await getRedisClient();
  const cacheKey = `${CACHE_PREFIX}${key}`;

  if (client) {
    try {
      const cached = await client.get(cacheKey);
      const parsed = safeParse<T>(cached);
      if (parsed !== null) {
        return parsed;
      }
    } catch {
      // ignore cache read errors
    }
  }

  const data = await fetcher();

  if (client) {
    try {
      await client.set(cacheKey, JSON.stringify(data), { EX: ttlSeconds });
    } catch {
      // ignore cache write errors
    }
  }

  return data;
}
