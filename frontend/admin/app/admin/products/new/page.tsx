
"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import type { Category, ProductVariant } from "../../../../lib/types";
import {
  normalizeAiDescription,
  STRUCTURED_DESCRIPTION_INSTRUCTIONS,
  STRUCTURED_DESCRIPTION_RULES,
} from "../../../../lib/ai-description";
import {
  createProduct,
  fetchAiDraftFromUpload,
  fetchCategories,
  generateDescription,
  searchRag,
} from "../../../../lib/api";

type VariantForm = ProductVariant & {
  imageFile?: File | null;
  imagePreview?: string | null;
  extraPreviews?: string[];
  extraFiles?: File[];
};

function fileFromNothing() {
  return new Blob([]);
}

export default function AdminProductNewPage() {
  const router = useRouter();
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiError, setAiError] = useState<string | null>(null);
  const [aiFullLoading, setAiFullLoading] = useState(false);
  const [aiRewriteLoading, setAiRewriteLoading] = useState(false);
  const [aiShortenLoading, setAiShortenLoading] = useState(false);
  const [aiToneLoading, setAiToneLoading] = useState(false);
  const [aiBulletsLoading, setAiBulletsLoading] = useState(false);
  const [aiPriceLoading, setAiPriceLoading] = useState(false);
  const [variantAiAction, setVariantAiAction] = useState<{ index: number; action: string } | null>(null);

  const isAnyAiBusy =
    aiLoading ||
    aiFullLoading ||
    aiRewriteLoading ||
    aiShortenLoading ||
    aiToneLoading ||
    aiBulletsLoading ||
    aiPriceLoading ||
    variantAiAction !== null;

  const [form, setForm] = useState({
    name: "",
    description: "",
    price_czk: "",
    stock: "1",
    category_id: "",
    wrist_size: "",
    image: null as File | null,
  });

  const [mediaFiles, setMediaFiles] = useState<File[]>([]);
  const [variants, setVariants] = useState<VariantForm[]>([]);

  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [mediaPreviews, setMediaPreviews] = useState<Array<{ url: string; type: string }>>([]);

  useEffect(() => {
    let active = true;
    setLoading(true);
    fetchCategories()
      .then((data) => {
        if (!active) return;
        setCategories(data);
      })
      .catch((err: Error) => {
        if (!active) return;
        setError(err.message || "Nepodařilo se načíst kategorie");
      })
      .finally(() => {
        if (!active) return;
        setLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!form.image) {
      setImagePreview(null);
      return;
    }
    const url = URL.createObjectURL(form.image);
    setImagePreview(url);
    return () => URL.revokeObjectURL(url);
  }, [form.image]);

  useEffect(() => {
    if (!mediaFiles.length) {
      setMediaPreviews([]);
      return;
    }
    const next = mediaFiles.map((file) => ({
      url: URL.createObjectURL(file),
      type: file.type,
    }));
    setMediaPreviews(next);
    return () => {
      next.forEach((item) => URL.revokeObjectURL(item.url));
    };
  }, [mediaFiles]);

  const categoryOptions = useMemo(
    () =>
      categories.map((cat) => ({
        id: cat.id,
        label: `${cat.group || "—"} — ${cat.name}`,
      })),
    [categories]
  );

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] || null;
    setForm((prev) => ({ ...prev, image: file }));
  };

  const handleMediaChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setMediaFiles(Array.from(e.target.files || []));
  };

  const handleAddVariant = () => {
    setVariants((prev) => [
      ...prev,
      {
        variant_name: "",
        wrist_size: "",
        description: "",
        price_czk: null,
        stock: 1,
        image: null,
        image_url: null,
        media: [],
        imageFile: null,
        imagePreview: null,
        extraPreviews: [],
        extraFiles: [],
      },
    ]);
  };

  const handleRemoveVariant = (index: number) => {
    setVariants((prev) => {
      const target = prev[index];
      if (target?.imagePreview) {
        URL.revokeObjectURL(target.imagePreview);
      }
      (target?.extraPreviews || []).forEach((url) => URL.revokeObjectURL(url));
      return prev.filter((_, idx) => idx !== index);
    });
  };

  const updateVariant = (index: number, patch: Partial<VariantForm>) => {
    setVariants((prev) => prev.map((variant, idx) => (idx === index ? { ...variant, ...patch } : variant)));
  };

  const updateVariantImageFile = (index: number, file: File | null) => {
    setVariants((prev) =>
      prev.map((variant, idx) => {
        if (idx !== index) return variant;
        if (variant.imagePreview) {
          URL.revokeObjectURL(variant.imagePreview);
        }
        const imagePreview = file ? URL.createObjectURL(file) : null;
        return { ...variant, imageFile: file, imagePreview };
      })
    );
  };

  const updateVariantExtraFiles = (index: number, files: File[]) => {
    setVariants((prev) =>
      prev.map((variant, idx) => {
        if (idx !== index) return variant;
        (variant.extraPreviews || []).forEach((url) => URL.revokeObjectURL(url));
        const extraPreviews = files.map((file) => URL.createObjectURL(file));
        return { ...variant, extraFiles: files, extraPreviews };
      })
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    setSuccess(null);

    try {
      const data = new FormData();
      data.append("name", form.name);
      data.append("description", form.description);
      data.append("price_czk", form.price_czk);
      data.append("stock", form.stock ? form.stock : "1");
      data.append("category_id", form.category_id);
      data.append("wrist_size", form.wrist_size);

      if (form.image) {
        data.append("image", form.image);
      }

      mediaFiles.forEach((file) => data.append("media", file));

      variants.forEach((variant, index) => {
        data.append("variant_name[]", variant.variant_name || "");
        data.append("variant_wrist_size[]", variant.wrist_size || "");
        data.append("variant_stock[]", String(variant.stock ?? 0));
        data.append(
          "variant_price[]",
          variant.price_czk !== undefined && variant.price_czk !== null ? String(variant.price_czk) : ""
        );
        data.append("variant_description[]", variant.description || "");

        if (variant.imageFile) {
          data.append("variant_image[]", variant.imageFile);
        } else {
          data.append("variant_image[]", fileFromNothing(), "");
        }

        (variant.extraFiles || []).forEach((file) => {
          data.append(`variant_image_multi_${index}[]`, file);
        });
      });

      await createProduct(data);
      setSuccess("Produkt byl vytvořen.");
      router.push("/admin/products?created=1");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Nepodařilo se vytvořit produkt";
      setError(message);
    } finally {
      setSubmitting(false);
    }
  };

  const buildContext = (vision: Record<string, unknown>): string => {
    const labels = (vision.labels as string[]) || [];
    const objects = (vision.objects as string[]) || [];
    const colors =
      (vision.dominant_colors as string[]) ||
      (vision.dominantColors as string[]) ||
      (vision.colors as string[]) ||
      [];

    const lines = [
      labels.length ? `labels: ${labels.join(", ")}` : "",
      colors.length ? `dominant colors: ${colors.join(", ")}` : "",
      objects.length ? `objects: ${objects.join(", ")}` : "",
    ].filter(Boolean);

    return lines.join("\n");
  };

  const guessCategory = (labels: string[]): string => {
    if (!labels.length) return "";
    const lowered = labels.map((l) => l.toLowerCase());
    const match = categories.find((cat) => {
      const name = (cat.name || "").toLowerCase();
      const slug = (cat.slug || "").toLowerCase();
      return lowered.some((l) => name.includes(l) || slug.includes(l));
    });
    return match?.name || "";
  };

  const buildAiPrompt = (args: {
    visionText: string;
    productName?: string;
    ragExamples?: unknown;
  }): string => {
    const lines: string[] = [];
    lines.push("You are generating product data for a handmade shop.");
    lines.push("Return JSON only with keys: name, description, category_slug, price_czk, stock.");
    lines.push("Do not include extra keys or any commentary.");
    if (args.productName) {
      lines.push(`Product name hint: ${args.productName}`);
    }
    lines.push("Image attributes:");
    lines.push(args.visionText || "No attributes provided.");
    if (args.ragExamples) {
      lines.push("Similar examples (if any):");
      lines.push(JSON.stringify(args.ragExamples));
    }
    lines.push("Formatting rules:");
    lines.push("- description: MUST use the exact structured format below (with headings and bullets)");
    lines.push(...STRUCTURED_DESCRIPTION_RULES);
    lines.push("- category_slug: lowercase slug");
    lines.push("- price_czk: number");
    lines.push("- stock: integer");
    return lines.join("\n");
  };

  const buildVariantAiPrompt = (args: {
    visionText: string;
    variantName?: string;
    ragExamples?: unknown;
  }): string => {
    const lines: string[] = [];
    lines.push("You are generating product variant data for a handmade shop.");
    lines.push("Return JSON only with keys: variant_name, description, price_czk, stock.");
    lines.push("Do not include extra keys or any commentary.");
    if (args.variantName) {
      lines.push(`Variant name hint: ${args.variantName}`);
    }
    lines.push("Image attributes:");
    lines.push(args.visionText || "No attributes provided.");
    if (args.ragExamples) {
      lines.push("Similar examples (if any):");
      lines.push(JSON.stringify(args.ragExamples));
    }
    lines.push("Formatting rules:");
    lines.push("- description: MUST use the exact structured format below (with headings and bullets)");
    lines.push(...STRUCTURED_DESCRIPTION_RULES);
    lines.push("- price_czk: number");
    lines.push("- stock: integer");
    return lines.join("\n");
  };

  const extractJson = (value: string): Record<string, unknown> | null => {
    try {
      return JSON.parse(value);
    } catch {
      const start = value.indexOf("{");
      const end = value.lastIndexOf("}");
      if (start >= 0 && end > start) {
        try {
          return JSON.parse(value.slice(start, end + 1));
        } catch {
          return null;
        }
      }
      return null;
    }
  };

  const handleGenerateDescription = async () => {
    if (!form.image) {
      setAiError("Vyberte obrázek produktu.");
      return;
    }

    setAiError(null);
    setAiLoading(true);

    try {
      const formData = new FormData();
      formData.append("image", form.image);
      const draft = await fetchAiDraftFromUpload(formData);
      const description = normalizeAiDescription(draft.description || "");

      if (!description) {
        throw new Error("AI nevygenerovala popis.");
      }

      setForm((prev) => ({ ...prev, description }));
    } catch (err) {
      const message = err instanceof Error ? err.message : "AI generování selhalo.";
      setAiError(message);
    } finally {
      setAiLoading(false);
    }
  };

  const handleCreateWithAi = async () => {
    if (!form.image) {
      setAiError("Vyberte obrázek produktu.");
      return;
    }

    setAiError(null);
    setAiFullLoading(true);

    try {
      const formData = new FormData();
      formData.append("image", form.image);
      const draft = await fetchAiDraftFromUpload(formData);

      const nextName = draft.title || form.name || "";
      const nextDescription = normalizeAiDescription(draft.description || form.description || "");

      if (!nextName && !nextDescription) {
        throw new Error("AI nevrátila text.");
      }

      setForm((prev) => ({
        ...prev,
        name: nextName || prev.name,
        description: nextDescription || prev.description,
      }));
    } catch (err) {
      const message = err instanceof Error ? err.message : "AI generování selhalo.";
      setAiError(message);
    } finally {
      setAiFullLoading(false);
    }
  };

  const buildRagPayload = (labels: string[], colors: string[], objects: string[], category: string) => ({
    category,
    attributes: { labels, colors, objects },
  });

  const callRag = async () => {
    const labels = [] as string[];
    const colors = [] as string[];
    const objects = [] as string[];
    const categoryName =
      categories.find((cat) => String(cat.id) === String(form.category_id))?.name || "";
    if (!categoryName) return null;
    try {
      return await searchRag(buildRagPayload(labels, colors, objects, categoryName));
    } catch (err) {
      console.error("RAG search failed:", err);
      return null;
    }
  };

  const extractText = (value: string) => {
    const parsed = extractJson(value);
    if (parsed && typeof parsed.description === "string") {
      return parsed.description;
    }
    return value;
  };

  const extractBullets = (value: string): string[] => {
    const parsed = extractJson(value);
    if (parsed && Array.isArray(parsed.bullets)) {
      return parsed.bullets.map((b) => String(b));
    }
    return value
      .split("\n")
      .map((line) => line.replace(/^[-•*\s]+/, "").trim())
      .filter(Boolean);
  };

  const extractPrice = (value: string): string => {
    const parsed = extractJson(value);
    if (parsed && parsed.price_czk !== undefined) {
      return String(parsed.price_czk);
    }
    const match = value.match(/([0-9]+(?:[.,][0-9]+)?)/);
    return match ? match[1].replace(",", ".") : "";
  };

  const handleRewriteDescription = async () => {
    if (!form.description.trim()) {
      setAiError("Nejprve vyplňte popis.");
      return;
    }
    setAiError(null);
    setAiRewriteLoading(true);
    try {
      const categoryName =
        categories.find((cat) => String(cat.id) === String(form.category_id))?.name || "";
      const ragExamples = await callRag();
      const prompt = [
        "Rewrite the product description in Czech.",
        "Keep the same meaning but follow the required structured format.",
        `Name: ${form.name}`,
        categoryName ? `Category: ${categoryName}` : "",
        ragExamples ? `Examples: ${JSON.stringify(ragExamples)}` : "",
        ...STRUCTURED_DESCRIPTION_INSTRUCTIONS,
        `Current description: ${form.description}`,
      ]
        .filter(Boolean)
        .join("\n");
      const generated = await generateDescription(prompt);
      const raw =
        generated.text ||
        generated.description ||
        generated.long_description ||
        generated.short_description ||
        "";
      const next = normalizeAiDescription(extractText(raw));
      if (!next) throw new Error("AI nevrátila text.");
      setForm((prev) => ({ ...prev, description: next }));
    } catch (err) {
      const message = err instanceof Error ? err.message : "AI generování selhalo.";
      setAiError(message);
    } finally {
      setAiRewriteLoading(false);
    }
  };

  const handleShortenDescription = async () => {
    if (!form.description.trim()) {
      setAiError("Nejprve vyplňte popis.");
      return;
    }
    setAiError(null);
    setAiShortenLoading(true);
    try {
      const prompt = [
        "Shorten the following Czech product description.",
        "Keep the meaning but make it shorter and more concise.",
        ...STRUCTURED_DESCRIPTION_INSTRUCTIONS,
        form.description,
      ].join("\n");
      const generated = await generateDescription(prompt);
      const raw =
        generated.text ||
        generated.description ||
        generated.long_description ||
        generated.short_description ||
        "";
      const next = normalizeAiDescription(extractText(raw));
      if (!next) throw new Error("AI nevrátila text.");
      setForm((prev) => ({ ...prev, description: next }));
    } catch (err) {
      const message = err instanceof Error ? err.message : "AI generování selhalo.";
      setAiError(message);
    } finally {
      setAiShortenLoading(false);
    }
  };

  const handleImproveTone = async () => {
    if (!form.description.trim()) {
      setAiError("Nejprve vyplňte popis.");
      return;
    }
    setAiError(null);
    setAiToneLoading(true);
    try {
      const prompt = [
        "Vylepšit marketingový tón of the Czech product description.",
        "More emotional and benefit-oriented.",
        ...STRUCTURED_DESCRIPTION_INSTRUCTIONS,
        form.description,
      ].join("\n");
      const generated = await generateDescription(prompt);
      const raw =
        generated.text ||
        generated.description ||
        generated.long_description ||
        generated.short_description ||
        "";
      const next = normalizeAiDescription(extractText(raw));
      if (!next) throw new Error("AI nevrátila text.");
      setForm((prev) => ({ ...prev, description: next }));
    } catch (err) {
      const message = err instanceof Error ? err.message : "AI generování selhalo.";
      setAiError(message);
    } finally {
      setAiToneLoading(false);
    }
  };

  const handleGenerateBullets = async () => {
    if (!form.description.trim()) {
      setAiError("Nejprve vyplňte popis.");
      return;
    }
    setAiError(null);
    setAiBulletsLoading(true);
    try {
      const prompt = [
        "Generate 3-6 benefit bullet points in Czech based on the description.",
        "Keep the same overall structure.",
        ...STRUCTURED_DESCRIPTION_INSTRUCTIONS,
        form.description,
      ].join("\n");
      const generated = await generateDescription(prompt);
      const raw =
        generated.text ||
        generated.description ||
        generated.long_description ||
        generated.short_description ||
        "";
      const next = normalizeAiDescription(extractText(raw));
      if (!next) throw new Error("AI nevrátila body.");
      setForm((prev) => ({ ...prev, description: next }));
    } catch (err) {
      const message = err instanceof Error ? err.message : "AI generování selhalo.";
      setAiError(message);
    } finally {
      setAiBulletsLoading(false);
    }
  };

  const handleSuggestPrice = async () => {
    setAiError(null);
    setAiPriceLoading(true);
    try {
      const categoryName =
        categories.find((cat) => String(cat.id) === String(form.category_id))?.name || "";
      const ragExamples = await callRag();
      const prompt = [
        "Suggest a CZK price as a number for this product.",
        "Return only the numeric price.",
        `Name: ${form.name}`,
        categoryName ? `Category: ${categoryName}` : "",
        form.description ? `Description: ${form.description}` : "",
        ragExamples ? `Examples: ${JSON.stringify(ragExamples)}` : "",
      ]
        .filter(Boolean)
        .join("\n");
      const generated = await generateDescription(prompt);
      const raw =
        generated.text ||
        generated.description ||
        generated.long_description ||
        generated.short_description ||
        "";
      const next = extractPrice(raw);
      if (!next) throw new Error("AI nevrátila cenu.");
      setForm((prev) => ({ ...prev, price_czk: next }));
    } catch (err) {
      const message = err instanceof Error ? err.message : "AI generování selhalo.";
      setAiError(message);
    } finally {
      setAiPriceLoading(false);
    }
  };

  const isVariantBusy = (index: number, action?: string) =>
    !!variantAiAction &&
    variantAiAction.index === index &&
    (!action || variantAiAction.action === action);

  const handleVariantGenerateDescription = async (index: number) => {
    const variant = variants[index];
    if (!variant?.imageFile) {
      setAiError("Vyberte obrázek varianty.");
      return;
    }
    setAiError(null);
    setVariantAiAction({ index, action: "generate" });
    try {
      const formData = new FormData();
      formData.append("image", variant.imageFile);
      const draft = await fetchAiDraftFromUpload(formData);
      const description = (draft.description || "").trim();
      if (!description) {
        throw new Error("AI nevygenerovala popis.");
      }
      updateVariant(index, { description });
    } catch (err) {
      const message = err instanceof Error ? err.message : "AI generování selhalo.";
      setAiError(message);
    } finally {
      setVariantAiAction(null);
    }
  };

  const handleVariantCreateWithAi = async (index: number) => {
    const variant = variants[index];
    if (!variant?.imageFile) {
      setAiError("Vyberte obrázek varianty.");
      return;
    }
    setAiError(null);
    setVariantAiAction({ index, action: "full" });
    try {
      const formData = new FormData();
      formData.append("image", variant.imageFile);
      const draft = await fetchAiDraftFromUpload(formData);

      const nextName = draft.title || variant.variant_name || "";
      const nextDescription = (draft.description || variant.description || "").trim();
      if (!nextName && !nextDescription) {
        throw new Error("AI nevrátila text.");
      }

      updateVariant(index, {
        variant_name: nextName || variant.variant_name,
        description: nextDescription || variant.description,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : "AI generování selhalo.";
      setAiError(message);
    } finally {
      setVariantAiAction(null);
    }
  };

  const handleVariantRewriteDescription = async (index: number) => {
    const variant = variants[index];
    if (!variant?.description?.trim()) {
      setAiError("Nejprve vyplňte popis varianty.");
      return;
    }
    setAiError(null);
    setVariantAiAction({ index, action: "rewrite" });
    try {
      const categoryName =
        categories.find((cat) => String(cat.id) === String(form.category_id))?.name || "";
      const ragExamples = await callRag();
      const prompt = [
        "Rewrite the variant description in Czech.",
        "Keep the same meaning but follow the required structured format.",
        `Variant name: ${variant.variant_name || ""}`,
        categoryName ? `Category: ${categoryName}` : "",
        ragExamples ? `Examples: ${JSON.stringify(ragExamples)}` : "",
        ...STRUCTURED_DESCRIPTION_INSTRUCTIONS,
        `Current description: ${variant.description}`,
      ]
        .filter(Boolean)
        .join("\n");
      const generated = await generateDescription(prompt);
      const raw =
        generated.text ||
        generated.description ||
        generated.long_description ||
        generated.short_description ||
        "";
      const next = normalizeAiDescription(extractText(raw));
      if (!next) throw new Error("AI nevrátila text.");
      updateVariant(index, { description: next });
    } catch (err) {
      const message = err instanceof Error ? err.message : "AI generování selhalo.";
      setAiError(message);
    } finally {
      setVariantAiAction(null);
    }
  };

  const handleVariantShortenDescription = async (index: number) => {
    const variant = variants[index];
    if (!variant?.description?.trim()) {
      setAiError("Nejprve vyplňte popis varianty.");
      return;
    }
    setAiError(null);
    setVariantAiAction({ index, action: "shorten" });
    try {
      const prompt = [
        "Shorten the following Czech variant description.",
        "Keep the meaning but make it shorter and more concise.",
        ...STRUCTURED_DESCRIPTION_INSTRUCTIONS,
        variant.description,
      ].join("\n");
      const generated = await generateDescription(prompt);
      const raw =
        generated.text ||
        generated.description ||
        generated.long_description ||
        generated.short_description ||
        "";
      const next = normalizeAiDescription(extractText(raw));
      if (!next) throw new Error("AI nevrátila text.");
      updateVariant(index, { description: next });
    } catch (err) {
      const message = err instanceof Error ? err.message : "AI generování selhalo.";
      setAiError(message);
    } finally {
      setVariantAiAction(null);
    }
  };

  const handleVariantImproveTone = async (index: number) => {
    const variant = variants[index];
    if (!variant?.description?.trim()) {
      setAiError("Nejprve vyplňte popis varianty.");
      return;
    }
    setAiError(null);
    setVariantAiAction({ index, action: "tone" });
    try {
      const prompt = [
        "Vylepšit marketingový tón of the Czech variant description.",
        "More emotional and benefit-oriented.",
        ...STRUCTURED_DESCRIPTION_INSTRUCTIONS,
        variant.description,
      ].join("\n");
      const generated = await generateDescription(prompt);
      const raw =
        generated.text ||
        generated.description ||
        generated.long_description ||
        generated.short_description ||
        "";
      const next = normalizeAiDescription(extractText(raw));
      if (!next) throw new Error("AI nevrátila text.");
      updateVariant(index, { description: next });
    } catch (err) {
      const message = err instanceof Error ? err.message : "AI generování selhalo.";
      setAiError(message);
    } finally {
      setVariantAiAction(null);
    }
  };

  const handleVariantGenerateBullets = async (index: number) => {
    const variant = variants[index];
    if (!variant?.description?.trim()) {
      setAiError("Nejprve vyplňte popis varianty.");
      return;
    }
    setAiError(null);
    setVariantAiAction({ index, action: "bullets" });
    try {
      const prompt = [
        "Generate 3-6 benefit bullet points in Czech based on the description.",
        "Keep the same overall structure.",
        ...STRUCTURED_DESCRIPTION_INSTRUCTIONS,
        variant.description,
      ].join("\n");
      const generated = await generateDescription(prompt);
      const raw =
        generated.text ||
        generated.description ||
        generated.long_description ||
        generated.short_description ||
        "";
      const next = normalizeAiDescription(extractText(raw));
      if (!next) throw new Error("AI nevrátila body.");
      updateVariant(index, { description: next });
    } catch (err) {
      const message = err instanceof Error ? err.message : "AI generování selhalo.";
      setAiError(message);
    } finally {
      setVariantAiAction(null);
    }
  };

  return (
    <main className="min-h-screen bg-gray-50 text-gray-900">
      <div className="mx-auto max-w-5xl px-6 py-10">
        <div className="mb-6">
          <h1 className="text-2xl font-semibold">Přidat produkt</h1>
          <p className="text-sm text-gray-500">Nový produkt v administraci.</p>
        </div>

        {loading && (
          <div className="rounded-md border border-gray-200 bg-white p-6 text-sm text-gray-600">
            Načítání kategorií...
          </div>
        )}

        {error && (
          <div className="mb-4 rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-600">
            {error}
          </div>
        )}

        {aiError && (
          <div className="mb-4 rounded-md border border-amber-200 bg-amber-50 p-4 text-sm text-amber-700">
            {aiError}
          </div>
        )}

        {success && (
          <div className="mb-4 rounded-md border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700">
            {success}
          </div>
        )}

        {!loading && (
          <form onSubmit={handleSubmit} className="grid gap-6 lg:grid-cols-[2fr_1fr]">
            <div className="space-y-4 rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
              <div>
                <label className="mb-1 block text-sm font-medium">Název produktu</label>
                <input
                  type="text"
                  name="name"
                  value={form.name}
                  onChange={handleChange}
                  required
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                />
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium">Popis</label>
                <textarea
                  name="description"
                  value={form.description}
                  onChange={handleChange}
                  rows={6}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                />
                <div className="mt-3 flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={handleGenerateDescription}
                    disabled={isAnyAiBusy}
                    className="inline-flex items-center gap-2 rounded-md border border-gray-300 px-3 py-2 text-xs font-semibold text-gray-700 hover:bg-gray-100 disabled:opacity-60"
                  >
                    {aiLoading ? "Generuji..." : "Vygenerovat popis z obrázku (AI)"}
                  </button>
                  <button
                    type="button"
                    onClick={handleCreateWithAi}
                    disabled={isAnyAiBusy}
                    className="inline-flex items-center gap-2 rounded-md border border-gray-300 px-3 py-2 text-xs font-semibold text-gray-700 hover:bg-gray-100 disabled:opacity-60"
                  >
                    {aiFullLoading ? "Generuji..." : "Vytvořit produkt pomocí AI"}
                  </button>
                  <button
                    type="button"
                    onClick={handleRewriteDescription}
                    disabled={isAnyAiBusy}
                    className="inline-flex items-center gap-2 rounded-md border border-gray-300 px-3 py-2 text-xs font-semibold text-gray-700 hover:bg-gray-100 disabled:opacity-60"
                  >
                    {aiRewriteLoading ? "Generuji..." : "Přepsat popis (AI)"}
                  </button>
                  <button
                    type="button"
                    onClick={handleShortenDescription}
                    disabled={isAnyAiBusy}
                    className="inline-flex items-center gap-2 rounded-md border border-gray-300 px-3 py-2 text-xs font-semibold text-gray-700 hover:bg-gray-100 disabled:opacity-60"
                  >
                    {aiShortenLoading ? "Generuji..." : "Zkrátit popis"}
                  </button>
                  <button
                    type="button"
                    onClick={handleImproveTone}
                    disabled={isAnyAiBusy}
                    className="inline-flex items-center gap-2 rounded-md border border-gray-300 px-3 py-2 text-xs font-semibold text-gray-700 hover:bg-gray-100 disabled:opacity-60"
                  >
                    {aiToneLoading ? "Generuji..." : "Vylepšit marketingový tón"}
                  </button>
                  <button
                    type="button"
                    onClick={handleGenerateBullets}
                    disabled={isAnyAiBusy}
                    className="inline-flex items-center gap-2 rounded-md border border-gray-300 px-3 py-2 text-xs font-semibold text-gray-700 hover:bg-gray-100 disabled:opacity-60"
                  >
                    {aiBulletsLoading ? "Generuji..." : "Vygenerovat body výhod"}
                  </button>
                </div>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="mb-1 block text-sm font-medium">Cena (Kč)</label>
                  <input
                    type="number"
                    name="price_czk"
                    value={form.price_czk}
                    onChange={handleChange}
                    step="0.01"
                    required
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                  />
                  <button
                    type="button"
                    onClick={handleSuggestPrice}
                    disabled={isAnyAiBusy}
                    className="mt-2 inline-flex items-center gap-2 rounded-md border border-gray-300 px-3 py-2 text-xs font-semibold text-gray-700 hover:bg-gray-100 disabled:opacity-60"
                  >
                    {aiPriceLoading ? "Generuji..." : "Navrhnout lepší cenu"}
                  </button>
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium">Počet kusů (stock)</label>
                  <input
                    type="number"
                    name="stock"
                    value={form.stock}
                    onChange={handleChange}
                    required
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                  />
                </div>
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium">Obvod / velikost produktu</label>
                <input
                  type="text"
                  name="wrist_size"
                  value={form.wrist_size}
                  onChange={handleChange}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                  placeholder="Např. 16 cm nebo 15-17 cm"
                />
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium">Kategorie</label>
                <select
                  name="category_id"
                  value={form.category_id}
                  onChange={handleChange}
                  required
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                >
                  <option value="">-- Vyber kategorii --</option>
                  {categoryOptions.map((option) => (
                    <option key={option.id} value={String(option.id)}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium">Varianty</label>
                <div className="space-y-3">
                  {variants.map((variant, index) => (
                    <div key={index} className="rounded-lg border border-gray-200 p-4">
                      <div className="grid gap-3 md:grid-cols-3">
                        <div>
                          <label className="mb-1 block text-xs font-semibold uppercase text-gray-500">Název varianty</label>
                          <input
                            type="text"
                            value={variant.variant_name || ""}
                            onChange={(e) => updateVariant(index, { variant_name: e.target.value })}
                            className="w-full rounded-md border border-gray-300 px-2 py-1 text-sm"
                          />
                        </div>
                        <div>
                          <label className="mb-1 block text-xs font-semibold uppercase text-gray-500">Obvod / velikost</label>
                          <input
                            type="text"
                            value={variant.wrist_size || ""}
                            onChange={(e) => updateVariant(index, { wrist_size: e.target.value })}
                            className="w-full rounded-md border border-gray-300 px-2 py-1 text-sm"
                          />
                        </div>
                        <div>
                          <label className="mb-1 block text-xs font-semibold uppercase text-gray-500">Cena varianty</label>
                          <input
                            type="number"
                            step="0.01"
                            value={variant.price_czk ?? ""}
                            onChange={(e) =>
                              updateVariant(index, { price_czk: e.target.value ? Number(e.target.value) : null })
                            }
                            className="w-full rounded-md border border-gray-300 px-2 py-1 text-sm"
                          />
                        </div>
                        <div>
                          <label className="mb-1 block text-xs font-semibold uppercase text-gray-500">Sklad varianty</label>
                          <input
                            type="number"
                            value={variant.stock ?? 0}
                            onChange={(e) => updateVariant(index, { stock: Number(e.target.value) })}
                            className="w-full rounded-md border border-gray-300 px-2 py-1 text-sm"
                          />
                        </div>
                        <div className="md:col-span-2">
                          <label className="mb-1 block text-xs font-semibold uppercase text-gray-500">Popis varianty</label>
                          <textarea
                            value={variant.description || ""}
                            onChange={(e) => updateVariant(index, { description: e.target.value })}
                            rows={2}
                            className="w-full rounded-md border border-gray-300 px-2 py-1 text-sm"
                          />
                        </div>
                      </div>

                      <div className="mt-3 flex flex-wrap gap-2">
                        <button
                          type="button"
                          onClick={() => handleVariantGenerateDescription(index)}
                          disabled={isAnyAiBusy}
                          className="inline-flex items-center gap-2 rounded-md border border-gray-300 px-3 py-2 text-xs font-semibold text-gray-700 hover:bg-gray-100 disabled:opacity-60"
                        >
                          {isVariantBusy(index, "generate")
                            ? "Generuji..."
                            : "Vygenerovat popis z obrázku (AI)"}
                        </button>
                        <button
                          type="button"
                          onClick={() => handleVariantCreateWithAi(index)}
                          disabled={isAnyAiBusy}
                          className="inline-flex items-center gap-2 rounded-md border border-gray-300 px-3 py-2 text-xs font-semibold text-gray-700 hover:bg-gray-100 disabled:opacity-60"
                        >
                          {isVariantBusy(index, "full") ? "Generuji..." : "Vytvořit variantu pomocí AI"}
                        </button>
                        <button
                          type="button"
                          onClick={() => handleVariantRewriteDescription(index)}
                          disabled={isAnyAiBusy}
                          className="inline-flex items-center gap-2 rounded-md border border-gray-300 px-3 py-2 text-xs font-semibold text-gray-700 hover:bg-gray-100 disabled:opacity-60"
                        >
                          {isVariantBusy(index, "rewrite") ? "Generuji..." : "Přepsat popis (AI)"}
                        </button>
                        <button
                          type="button"
                          onClick={() => handleVariantShortenDescription(index)}
                          disabled={isAnyAiBusy}
                          className="inline-flex items-center gap-2 rounded-md border border-gray-300 px-3 py-2 text-xs font-semibold text-gray-700 hover:bg-gray-100 disabled:opacity-60"
                        >
                          {isVariantBusy(index, "shorten") ? "Generuji..." : "Zkrátit popis"}
                        </button>
                        <button
                          type="button"
                          onClick={() => handleVariantImproveTone(index)}
                          disabled={isAnyAiBusy}
                          className="inline-flex items-center gap-2 rounded-md border border-gray-300 px-3 py-2 text-xs font-semibold text-gray-700 hover:bg-gray-100 disabled:opacity-60"
                        >
                          {isVariantBusy(index, "tone") ? "Generuji..." : "Vylepšit marketingový tón"}
                        </button>
                        <button
                          type="button"
                          onClick={() => handleVariantGenerateBullets(index)}
                          disabled={isAnyAiBusy}
                          className="inline-flex items-center gap-2 rounded-md border border-gray-300 px-3 py-2 text-xs font-semibold text-gray-700 hover:bg-gray-100 disabled:opacity-60"
                        >
                          {isVariantBusy(index, "bullets") ? "Generuji..." : "Vygenerovat body výhod"}
                        </button>
                      </div>

                      <div className="mt-3">
                        <label className="mb-1 block text-xs font-semibold uppercase text-gray-500">Obrázek varianty</label>
                        {variant.imagePreview && (
                          <div className="mb-2 h-16 w-16 overflow-hidden rounded shadow">
                            <img src={variant.imagePreview} alt="variant preview" className="h-full w-full object-cover" />
                          </div>
                        )}
                        <input
                          type="file"
                          accept="image/*"
                          onChange={(e) => updateVariantImageFile(index, e.target.files?.[0] || null)}
                        />
                      </div>

                      <div className="mt-3">
                        <label className="mb-1 block text-xs font-semibold uppercase text-gray-500">Další fotky varianty</label>
                        {(variant.extraPreviews || []).length > 0 && (
                          <div className="mb-2 flex flex-wrap gap-2">
                            {variant.extraPreviews?.map((url) => (
                              <div key={url} className="h-14 w-14 overflow-hidden rounded bg-gray-100">
                                <img src={url} alt="extra preview" className="h-full w-full object-cover" />
                              </div>
                            ))}
                          </div>
                        )}
                        <input
                          type="file"
                          multiple
                          accept="image/*"
                          onChange={(e) => updateVariantExtraFiles(index, Array.from(e.target.files || []))}
                        />
                      </div>

                      <div className="mt-3 text-right">
                        <button
                          type="button"
                          onClick={() => handleRemoveVariant(index)}
                          className="rounded-md border border-red-200 px-3 py-1 text-xs text-red-700"
                        >
                          Odstranit variantu
                        </button>
                      </div>
                    </div>
                  ))}

                  <button
                    type="button"
                    onClick={handleAddVariant}
                    className="rounded-md border border-gray-300 px-3 py-2 text-xs font-semibold text-gray-700"
                  >
                    + Přidat variantu
                  </button>
                </div>
              </div>
            </div>

            <div className="space-y-4">
              <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
                <label className="mb-2 block text-sm font-medium">Úvodní obrázek</label>
                <input
                  type="file"
                  name="image"
                  accept="image/*"
                  onChange={handleFileChange}
                  className="w-full text-sm"
                />
                {imagePreview && (
                  <div className="mt-4">
                    <div className="h-28 w-28 overflow-hidden rounded-lg border border-gray-200 shadow">
                      <img src={imagePreview} alt="preview" className="h-full w-full object-cover" />
                    </div>
                    <p className="mt-2 text-xs text-gray-500">Náhled hlavního obrázku.</p>
                  </div>
                )}
                <p className="mt-3 text-xs text-gray-500">
                  Upload: /static/uploads/
                </p>
              </div>

              <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
                <label className="mb-2 block text-sm font-medium">Další obrázky nebo videa</label>
                <input
                  type="file"
                  name="media"
                  accept="image/*,video/*"
                  multiple
                  onChange={handleMediaChange}
                  className="w-full text-sm"
                />
                {mediaPreviews.length > 0 && (
                  <div className="mt-4 grid grid-cols-3 gap-2">
                    {mediaPreviews.map((item, idx) => (
                      <div key={idx} className="h-20 w-20 overflow-hidden rounded-lg bg-gray-100">
                        {item.type.startsWith("video") ? (
                          <video src={item.url} className="h-full w-full object-cover" muted />
                        ) : (
                          <img src={item.url} alt="media" className="h-full w-full object-cover" />
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
                <h3 className="text-sm font-semibold text-gray-700">Akce</h3>
                <p className="mt-1 text-xs text-gray-500">
                  Zkontrolujte data, poté potvrďte vytvoření produktu.
                </p>
                <div className="mt-4 flex flex-col gap-2">
                  <button
                    type="submit"
                    disabled={submitting}
                    className="rounded-md bg-gray-900 px-4 py-2 text-sm font-semibold text-white hover:bg-gray-800 disabled:opacity-60"
                  >
                    {submitting ? "Ukládám..." : "Uložit"}
                  </button>
                  <button
                    type="button"
                    onClick={() => router.push("/admin/products")}
                    className="rounded-md border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                  >
                    Zpět
                  </button>
                </div>
              </div>
            </div>
          </form>
        )}
      </div>
    </main>
  );
}
