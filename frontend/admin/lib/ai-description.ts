const EMOJI_RE =
  /(\p{Extended_Pictographic}(?:\uFE0F|\uFE0E)?(?:\u200D\p{Extended_Pictographic}(?:\uFE0F|\uFE0E)?)*)/gu;

const EMOJI_RULES: Array<{ emoji: string; keywords: string[] }> = [
  { emoji: "🦋", keywords: ["motýl", "motýli"] },
  { emoji: "🌸", keywords: ["květ", "květy", "květina", "květiny"] },
  { emoji: "💖", keywords: ["srdce", "láska"] },
  { emoji: "⭐", keywords: ["hvězda", "hvězdy"] },
  { emoji: "🌙", keywords: ["měsíc"] },
  { emoji: "☀️", keywords: ["slunce"] },
  { emoji: "💎", keywords: ["náramek", "náhrdelník", "šperk", "korálek", "korálky", "perla", "perly"] },
  { emoji: "🕯️", keywords: ["svíčka", "svíčky"] },
  { emoji: "🐾", keywords: ["tlapka", "tlapky", "pes", "kočka", "pejsek", "kočička"] },
  { emoji: "🌿", keywords: ["list", "listy", "příroda", "přírodní", "rostlina"] },
  { emoji: "🔗", keywords: ["přívěsek", "klíčenka"] },
  { emoji: "🌈", keywords: ["duha", "barevný", "barevná", "barevné"] },
];

export const STRUCTURED_DESCRIPTION_RULES = [
  "Return the full description in this exact format:",
  "✨ Popis produktu:",
  "- první odrážka",
  "- druhá odrážka",
  "",
  "💎 Styl: 2–3 přívlastky oddělené čárkami",
  "Add 1–2 relevant emojis only if they fit the content. If no suitable emoji fits, do not add any.",
];

export const STRUCTURED_DESCRIPTION_INSTRUCTIONS = [
  ...STRUCTURED_DESCRIPTION_RULES,
  "Return plain text only.",
];

const HAS_POPIS_RE = /popis produktu\s*:/i;
const HAS_STYL_RE = /styl\s*:/i;

export function ensureStructuredDescription(rawText: string): string {
  const text = String(rawText || "").trim();
  if (!text) return text;

  const lines = text.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  const hasPopis = HAS_POPIS_RE.test(text);
  const hasStyl = HAS_STYL_RE.test(text);
  if (hasPopis && hasStyl) {
    const normalized: string[] = [];
    for (const line of lines) {
      normalized.push(line);
    }
    return normalized.join("\n");
  }

  let styleLine = "";
  const bullets: string[] = [];

  for (const line of lines) {
    if (HAS_STYL_RE.test(line)) {
      styleLine = line;
      continue;
    }
    if (HAS_POPIS_RE.test(line)) {
      continue;
    }
    if (line.startsWith("-")) {
      const bullet = line.replace(/^\-\s*/, "").trim();
      if (bullet) bullets.push(bullet);
      continue;
    }
    bullets.push(line);
  }

  if (!bullets.length) {
    bullets.push(text);
  }

  const output: string[] = [];
  output.push("✨ Popis produktu:");
  bullets.forEach((bullet) => output.push(`- ${bullet}`));
  output.push("");
  if (styleLine) {
    if (!styleLine.startsWith("💎")) {
      if (styleLine.toLowerCase().startsWith("styl")) {
        styleLine = `💎 ${styleLine}`;
      } else {
        styleLine = `💎 Styl: ${styleLine}`;
      }
    }
    output.push(styleLine);
  } else {
    output.push("💎 Styl: jemný, elegantní");
  }

  return output.join("\n");
}

export function injectRelevantEmojis(rawText: string): string {
  const text = String(rawText || "");
  if (!text.trim()) return text;
  if (EMOJI_RE.test(text)) return text;

  const lower = text.toLowerCase();
  const matches: string[] = [];
  for (const rule of EMOJI_RULES) {
    if (rule.keywords.some((kw) => lower.includes(kw))) {
      if (!matches.includes(rule.emoji)) {
        matches.push(rule.emoji);
      }
      if (matches.length >= 2) break;
    }
  }

  if (!matches.length) return text;

  const lines = text.split(/\r?\n/);
  let added = 0;
  const updated = lines.map((line) => {
    if (added >= matches.length) return line;
    const trimmed = line.trim();
    if (trimmed.startsWith("-")) {
      const emoji = matches[added++];
      return line.replace(/^\-\s*/, `- ${emoji} `);
    }
    if (trimmed.toLowerCase().startsWith("💎 styl:") || trimmed.toLowerCase().startsWith("styl:")) {
      const emoji = matches[added++];
      return `${line} ${emoji}`;
    }
    return line;
  });

  return updated.join("\n");
}

export function normalizeAiDescription(rawText: string): string {
  const structured = ensureStructuredDescription(rawText);
  return injectRelevantEmojis(structured);
}
