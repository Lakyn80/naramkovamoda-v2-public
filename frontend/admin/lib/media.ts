import { STATIC_BASE } from "./api";

export function resolveMediaUrl(path?: string | null): string | null {
  if (!path) return null;

  if (
    path.startsWith("http://") ||
    path.startsWith("https://") ||
    path.startsWith("/static/")
  ) {
    if (STATIC_BASE && path.startsWith("/static/")) {
      return `${STATIC_BASE}${path}`;
    }
    return path;
  }

  if (STATIC_BASE) {
    return `${STATIC_BASE}/static/uploads/${path}`;
  }
  return `/static/uploads/${path}`;
}
