import { STATIC_BASE } from "./api";

/**
 * Vrátí absolutní URL obrázku.
 * - Pokud je to už URL → vrátí ji rovnou
 * - Pokud začíná / → přidá STATIC_BASE (pokud je definován)
 * - Pokud je to jen název souboru → přidá /static/uploads/
 */
export function resolveMediaUrl(url: string | null | undefined): string | null {
  if (!url) return null;
  if (/^https?:\/\//i.test(url)) return url;
  if (url.startsWith("/")) {
    return STATIC_BASE ? `${STATIC_BASE}${url}` : url;
  }
  const base = STATIC_BASE || "";
  return `${base}/static/uploads/${url}`;
}

/**
 * Alias pro absoluteUploadUrl (kompatibilita se starým projektem)
 */
export function absoluteUploadUrl(url: string | null | undefined): string | null {
  const resolved = resolveMediaUrl(url);
  if (!resolved) return null;
  if (/\.webp(\?|#|$)/i.test(resolved)) return resolved;
  if (/\.(png|jpe?g|gif|bmp|tiff|heic|heif)(\?|#|$)/i.test(resolved)) {
    return null;
  }
  return resolved;
}
