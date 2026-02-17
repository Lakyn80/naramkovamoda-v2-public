import type { AiDraft, AiTemplateItem, Category, DeepseekResult, Product, VisionResult } from "./types";

const RAW_API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ||
  (process.env.NODE_ENV === "production" ? "/api" : "http://localhost:8080");
export function resolveApiBase(): string {
  // In production browser runtime always use same-origin API proxy.
  if (typeof window !== "undefined" && process.env.NODE_ENV === "production") {
    return "/api";
  }

  let base = RAW_API_BASE;

  if (typeof window !== "undefined") {
    const isLocalAdmin =
      window.location.hostname === "localhost" && window.location.port === "3012";
    if (isLocalAdmin && (base === "/api" || !base)) {
      return "http://localhost:8088";
    }

    // Prevent mixed-content requests if an absolute http API base leaked
    // into a production build served over HTTPS.
    if (window.location.protocol === "https:" && /^http:\/\//i.test(base)) {
      base = base.replace(/^http:\/\//i, "https://");
    }
  }
  if (base.includes("backend")) {
    return "/api";
  }
  return base;
}
export const API_BASE = resolveApiBase();
export const STATIC_BASE = API_BASE === "/api" ? "" : API_BASE;

export function buildApiUrl(path: string): string {
  const normalized = path.startsWith("/") ? path : `/${path}`;
  if (API_BASE === "/api") {
    if (normalized.startsWith("/api/") || normalized === "/api") {
      return normalized;
    }
    return `/api${normalized}`;
  }
  return `${API_BASE}${normalized}`;
}

export async function fetchProducts(): Promise<Product[]> {
  const res = await fetch(buildApiUrl("/api/products/?include_inactive=1"), { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Nepodařilo se načíst produkty (${res.status})`);
  }
  return (await res.json()) as Product[];
}

export async function fetchProduct(productId: number): Promise<Product> {
  const res = await fetch(buildApiUrl(`/api/products/${productId}`), { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Nepodařilo se načíst produkt (${res.status})`);
  }
  return (await res.json()) as Product;
}


export async function fetchCategory(categoryId: number): Promise<Category> {
  const res = await fetch(buildApiUrl(`/api/categories/${categoryId}`), { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Nepodařilo se načíst kategorii (${res.status})`);
  }
  return (await res.json()) as Category;
}

export async function fetchCategories(): Promise<Category[]> {
  const res = await fetch(buildApiUrl("/api/categories/"), { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Nepodařilo se načíst kategorie (${res.status})`);
  }
  return (await res.json()) as Category[];
}

export async function createCategory(payload: Partial<Category>): Promise<Category> {
  const res = await fetch(buildApiUrl("/api/categories/"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    let message = `Nepodařilo se vytvořit kategorii (${res.status})`;
    try {
      const data = (await res.json()) as { error?: string; message?: string; detail?: string };
      message = data?.error || data?.message || data?.detail || message;
    } catch {
      // ignore
    }
    throw new Error(message);
  }
  return (await res.json()) as Category;
}

export async function updateCategory(categoryId: number, payload: Partial<Category>): Promise<Category> {
  const res = await fetch(buildApiUrl(`/api/categories/${categoryId}`), {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    let message = `Nepodařilo se uložit kategorii (${res.status})`;
    try {
      const data = (await res.json()) as { error?: string; message?: string; detail?: string };
      message = data?.error || data?.message || data?.detail || message;
    } catch {
      // ignore
    }
    throw new Error(message);
  }
  return (await res.json()) as Category;
}

export async function deleteCategory(categoryId: number, force = false): Promise<void> {
  const url = force ? `/api/categories/${categoryId}?force=true` : `/api/categories/${categoryId}`;
  const res = await fetch(buildApiUrl(url), {
    method: "DELETE",
  });
  if (!res.ok) {
    let message = `Nepodařilo se smazat kategorii (${res.status})`;
    try {
      const data = (await res.json()) as { error?: string; message?: string; detail?: string };
      message = data?.error || data?.message || data?.detail || message;
    } catch {
      // ignore
    }
    throw new Error(message);
  }
}

export async function createProduct(formData: FormData): Promise<Product> {
  const res = await fetch(buildApiUrl("/api/products/"), {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    let message = `Nepodařilo se vytvořit produkt (${res.status})`;
    try {
      const data = (await res.json()) as { error?: string; message?: string; detail?: string };
      message = data?.error || data?.message || data?.detail || message;
    } catch {
      // ignore
    }
    throw new Error(message);
  }

  return (await res.json()) as Product;
}

export async function updateProduct(productId: number, formData: FormData): Promise<Product> {
  const res = await fetch(buildApiUrl(`/api/products/${productId}`), {
    method: "PUT",
    body: formData,
  });

  if (!res.ok) {
    let message = `Nepodařilo se uložit produkt (${res.status})`;
    try {
      const data = (await res.json()) as { error?: string; message?: string; detail?: string };
      message = data?.error || data?.message || data?.detail || message;
    } catch {
      // ignore
    }
    throw new Error(message);
  }

  return (await res.json()) as Product;
}

export async function deleteProduct(productId: number): Promise<void> {
  const res = await fetch(buildApiUrl(`/api/products/${productId}`), {
    method: "DELETE",
  });

  if (!res.ok) {
    let message = `Nepodařilo se smazat produkt (${res.status})`;
    try {
      const data = (await res.json()) as { error?: string; message?: string; detail?: string };
      message = data?.error || data?.message || data?.detail || message;
    } catch {
      // ignore
    }
    throw new Error(message);
  }
}

export async function analyzeImage(formData: FormData): Promise<VisionResult> {
  const res = await fetch(buildApiUrl("/api/ai/vision/analyze"), {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    let message = `Analýza obrázku selhala (${res.status})`;
    try {
      const data = (await res.json()) as { error?: string; message?: string; detail?: string };
      message = data?.error || data?.message || data?.detail || message;
    } catch {
      // ignore
    }
    throw new Error(message);
  }

  return (await res.json()) as VisionResult;
}

export async function generateDescription(context: string): Promise<DeepseekResult> {
  const formData = new FormData();
  formData.append("context", context);
  const res = await fetch(buildApiUrl("/api/ai/describe"), {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    let message = `Generování popisu selhalo (${res.status})`;
    try {
      const data = (await res.json()) as { error?: string; message?: string; detail?: string };
      message = data?.error || data?.message || data?.detail || message;
    } catch {
      // ignore
    }
    throw new Error(message);
  }

  return (await res.json()) as DeepseekResult;
}

export async function ingestRag(payload: {
  category: string;
  attributes: { labels: string[]; colors: string[]; objects: string[] };
  description: string;
}): Promise<void> {
  await fetch(buildApiUrl("/api/ai/rag/ingest"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function searchRag(payload: {
  category: string;
  attributes: { labels: string[]; colors: string[]; objects: string[] };
}): Promise<unknown> {
  const res = await fetch(buildApiUrl("/api/ai/rag/search"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    let message = `Vyhledávání v RAG selhalo (${res.status})`;
    try {
      const data = (await res.json()) as { error?: string; message?: string; detail?: string };
      message = data?.error || data?.message || data?.detail || message;
    } catch {
      // ignore
    }
    throw new Error(message);
  }
  return res.json();
}

export async function deleteMedia(mediaId: number): Promise<void> {
  const res = await fetch(buildApiUrl(`/api/media/${mediaId}`), {
    method: "DELETE",
  });

  if (!res.ok) {
    let message = `Smazání média selhalo (${res.status})`;
    try {
      const data = (await res.json()) as { error?: string; message?: string; detail?: string };
      message = data?.error || data?.message || data?.detail || message;
    } catch {
      // ignore
    }
    throw new Error(message);
  }
}

export async function fetchAiProductDraft(productId: number): Promise<AiDraft> {
  const res = await fetch(buildApiUrl(`/api/ai/products/${productId}/draft`), {
    method: "POST",
  });
  if (!res.ok) {
    let message = `AI draft selhal (${res.status})`;
    try {
      const data = (await res.json()) as { error?: string; message?: string; detail?: string };
      message = data?.error || data?.message || data?.detail || message;
    } catch {
      // ignore
    }
    throw new Error(message);
  }
  return (await res.json()) as AiDraft;
}

export async function fetchAiVariantDraft(variantId: number): Promise<AiDraft> {
  const res = await fetch(buildApiUrl(`/api/ai/variants/${variantId}/draft`), {
    method: "POST",
  });
  if (!res.ok) {
    let message = `AI draft selhal (${res.status})`;
    try {
      const data = (await res.json()) as { error?: string; message?: string; detail?: string };
      message = data?.error || data?.message || data?.detail || message;
    } catch {
      // ignore
    }
    throw new Error(message);
  }
  return (await res.json()) as AiDraft;
}

export async function fetchAiDraftFromUpload(formData: FormData): Promise<AiDraft> {
  const res = await fetch(buildApiUrl("/api/ai/drafts/from-upload"), {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    let message = `AI draft selhal (${res.status})`;
    try {
      const data = (await res.json()) as { error?: string; message?: string; detail?: string };
      message = data?.error || data?.message || data?.detail || message;
    } catch {
      // ignore
    }
    throw new Error(message);
  }
  return (await res.json()) as AiDraft;
}

export async function storeAiTemplate(productId: number): Promise<AiTemplateItem> {
  const res = await fetch(buildApiUrl("/api/ai/templates/store"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ product_id: productId }),
  });
  if (!res.ok) {
    let message = `Uložení vzoru selhalo (${res.status})`;
    try {
      const data = (await res.json()) as { error?: string; message?: string; detail?: string };
      message = data?.error || data?.message || data?.detail || message;
    } catch {
      // ignore
    }
    throw new Error(message);
  }
  return (await res.json()) as AiTemplateItem;
}

export async function fetchAiTemplates(): Promise<AiTemplateItem[]> {
  const res = await fetch(buildApiUrl("/api/ai/templates/list"), { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Nepodařilo se načíst AI vzory (${res.status})`);
  }
  const data = (await res.json()) as { items?: AiTemplateItem[] };
  return data.items || [];
}



export async function loginAdmin(payload: { username: string; password: string }): Promise<void> {
  const res = await fetch(buildApiUrl("/api/auth/login"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    let message = `Přihlášení selhalo (${res.status})`;
    try {
      const data = (await res.json()) as { error?: string; message?: string; detail?: string };
      message = data?.error || data?.message || data?.detail || message;
    } catch {
      // ignore
    }
    throw new Error(message);
  }
}

export async function forgotPassword(payload: { email: string }): Promise<void> {
  const res = await fetch(buildApiUrl("/api/auth/forgot"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    let message = `Odeslání odkazu selhalo (${res.status})`;
    try {
      const data = (await res.json()) as { error?: string; message?: string; detail?: string };
      message = data?.error || data?.message || data?.detail || message;
    } catch {
      // ignore
    }
    throw new Error(message);
  }
}

export async function resetPassword(payload: { token: string; password: string; password2: string }): Promise<void> {
  const res = await fetch(buildApiUrl("/api/auth/reset"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    let message = `Reset hesla selhal (${res.status})`;
    try {
      const data = (await res.json()) as { error?: string; message?: string; detail?: string };
      message = data?.error || data?.message || data?.detail || message;
    } catch {
      // ignore
    }
    throw new Error(message);
  }
}

export async function fetchPayments(params: {
  vs?: string;
  status?: string;
  limit?: number;
}): Promise<import("./types").PaymentListResponse> {
  const query = new URLSearchParams();
  if (params.vs) query.set("vs", params.vs);
  if (params.status && params.status !== "all") query.set("status", params.status);
  if (params.limit) query.set("per_page", String(params.limit));
  const res = await fetch(buildApiUrl(`/api/payments?${query.toString()}`), { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Nepodařilo se načíst platby (${res.status})`);
  }
  const data = (await res.json()) as any;
  const items = data?.items || data?.rows || data?.data || [];
  return {
    items,
    total: data?.total ?? data?.count ?? null,
    page: data?.page ?? null,
    per_page: data?.per_page ?? null,
  };
}

export async function fetchPaymentsSummary(): Promise<import("./types").PaymentSummary | null> {
  const res = await fetch(buildApiUrl("/api/payments/summary"), { cache: "no-store" });
  if (!res.ok) {
    return null;
  }
  const data = (await res.json()) as any;
  return {
    count: data?.count ?? null,
    total_amount: data?.total_amount ?? data?.totalAmount ?? null,
  };
}

export async function updatePaymentStatus(paymentId: number, status: string): Promise<void> {
  const res = await fetch(buildApiUrl("/api/payments/update-status"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ payment_id: paymentId, order_id: paymentId, status }),
  });
  if (!res.ok) {
    let message = `Uložení stavu selhalo (${res.status})`;
    try {
      const data = (await res.json()) as { error?: string; message?: string; detail?: string };
      message = data?.error || data?.message || data?.detail || message;
    } catch {
      // ignore
    }
    throw new Error(message);
  }
}

export async function deleteOrder(orderId: number): Promise<void> {
  const res = await fetch(buildApiUrl(`/api/payments/order/${orderId}`), {
    method: "DELETE",
  });
  if (!res.ok) {
    let message = `Smazání objednávky selhalo (${res.status})`;
    try {
      const data = (await res.json()) as { error?: string; message?: string; detail?: string };
      message = data?.error || data?.message || data?.detail || message;
    } catch {
      // ignore
    }
    throw new Error(message);
  }
}

export async function fetchSold(params: Record<string, string>): Promise<import("./types").SoldListResponse> {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value) query.set(key, value);
  });
  const res = await fetch(buildApiUrl(`/api/sold?${query.toString()}`), { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Nepodařilo se načíst prodané (${res.status})`);
  }
  const data = (await res.json()) as any;
  const rows = data?.rows || data?.items || data?.data || [];
  const summary = data?.summary || null;
  return { rows, summary };
}

export function buildSoldExportUrl(kind: "xlsx" | "pdf", params: Record<string, string>): string {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value) query.set(key, value);
  });
  return buildApiUrl(`/api/sold/export/${kind}?${query.toString()}`);
}

export function buildInvoicePreviewUrl(soldId: number): string {
  return buildApiUrl(`/api/sold/${soldId}/invoice-preview`);
}

export async function sendInvoiceEmail(soldId: number): Promise<void> {
  const res = await fetch(buildApiUrl(`/api/sold/${soldId}/invoice-send`), { method: "POST" });
  if (!res.ok) {
    let message = `Odeslání faktury selhalo (${res.status})`;
    try {
      const data = (await res.json()) as { error?: string; message?: string; detail?: string };
      message = data?.error || data?.message || data?.detail || message;
    } catch {
      // ignore
    }
    throw new Error(message);
  }
}
