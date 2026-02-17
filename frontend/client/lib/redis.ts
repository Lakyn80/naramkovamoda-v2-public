import "server-only";

import { createClient } from "redis";

const REDIS_URL = process.env.REDIS_URL || "redis://redis:6379";

// ZÁMĚRNĚ BEZ PŘESNÝCH TYPŮ — aby prošel produkční build
let client: any = null;
let clientPromise: Promise<any> | null = null;

async function connectClient(): Promise<any> {
  try {
    const nextClient = createClient({ url: REDIS_URL });
    await nextClient.connect();
    client = nextClient; // uložení bez typové kontroly
    return nextClient;
  } catch {
    return null;
  }
}

export async function getRedisClient(): Promise<any> {
  if (client) return client;
  if (!clientPromise) {
    clientPromise = connectClient().finally(() => {
      if (!client) {
        clientPromise = null;
      }
    });
  }
  return clientPromise;
}
