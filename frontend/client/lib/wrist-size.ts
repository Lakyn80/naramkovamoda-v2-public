export function normalizeWristSize(value?: string | number | null): string {
  if (value === null || value === undefined) return "";
  const raw = String(value).trim();
  if (!raw) return "";
  return raw.replace(/\s*cm$/i, "");
}

export function formatWristSize(value?: string | number | null): string {
  const normalized = normalizeWristSize(value);
  if (!normalized) return "";
  return `${normalized} cm`;
}

export function wristSizeToNumber(value?: string | number | null): number | null {
  const normalized = normalizeWristSize(value);
  if (!normalized) return null;
  const numeric = Number(normalized.replace(",", "."));
  return Number.isFinite(numeric) ? numeric : null;
}
