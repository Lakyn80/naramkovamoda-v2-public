export function slugify(input: string | null | undefined): string {
  let s = String(input ?? "").toLowerCase().trim();

  try {
    s = s.normalize("NFD").replace(/[\u0300-\u036f]/g, "");
  } catch {
    // ignore normalization errors
  }

  // odstranění všech typů uvozovek
  s = s.replace(/["'`""„]+/g, " ");

  s = s.replace(/[:;)(]+/g, " "); // smajlíky z interpunkce
  s = s.replace(/[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}]/gu, ""); // emoji pryč

  s = s
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "");

  return s || "produkt";
}
