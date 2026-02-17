"use client";

import { useEffect } from "react";

export default function ServiceWorkerCleanup() {
  useEffect(() => {
    if (typeof window === "undefined") return;
    if (!("serviceWorker" in navigator)) return;
    navigator.serviceWorker
      .getRegistrations()
      .then((registrations) => Promise.all(registrations.map((registration) => registration.unregister())))
      .catch(() => {
        // ignore
      });
  }, []);

  return null;
}
