export interface ProductMediaItem {
  id?: number | null;
  filename?: string | null;
  media_type?: string | null;
  url?: string | null;
}

export interface ProductVariantMedia {
  id?: number | null;
  image?: string | null;
  image_url?: string | null;
}

export interface ProductVariant {
  id?: number | null;
  variant_name?: string | null;
  wrist_size?: string | null;
  description?: string | null;
  price_czk?: number | null;
  stock?: number | null;
  image?: string | null;
  image_url?: string | null;
  media?: ProductVariantMedia[];
}

export interface Product {
  id: number;
  name: string;
  description?: string | null;
  seo_title?: string | null;
  seo_description?: string | null;
  seo_keywords?: string | null;
  price?: number | null;
  stock?: number | null;
  active?: boolean | null;
  category_id?: number | null;
  category_name?: string | null;
  category_slug?: string | null;
  wrist_size?: string | null;
  image_url?: string | null;
  media?: string[];
  media_items?: ProductMediaItem[];
  categories?: string[];
  category_group?: string | null;
  variants?: ProductVariant[];
  created_at?: string | null;
}

export interface AiDraft {
  title?: string | null;
  description?: string | null;
  product_type?: string | null;
  combined_tags?: string[];
  suggested_price_czk?: number | null;
  suggested_variant_price_czk?: number | null;
  seo_title?: string | null;
  seo_description?: string | null;
  seo_keywords?: string | null;
}

export interface AiTemplateItem {
  id: string;
  product_id?: number | null;
  title?: string | null;
  product_type?: string | null;
  price_czk?: number | null;
  created_at?: string | null;
}

export interface Category {
  id: number;
  name: string;
  description?: string | null;
  slug?: string | null;
  group?: string | null;
  category?: string | null;
}

export interface VisionResult {
  labels?: string[];
  colors?: string[];
  dominant_colors?: string[];
  dominantColors?: string[];
  objects?: string[];
}

export interface DeepseekResult {
  short_description?: string;
  long_description?: string;
  description?: string;
  text?: string;
}



export interface PaymentItem {
  id: number;
  vs?: string | null;
  variable_symbol?: string | null;
  amount?: number | null;
  amount_czk?: number | null;
  total_amount?: number | null;
  status?: string | null;
  received_at?: string | null;
  created_at?: string | null;
}

export interface PaymentListResponse {
  items: PaymentItem[];
  total?: number | null;
  page?: number | null;
  per_page?: number | null;
}

export interface PaymentSummary {
  count?: number | null;
  total_amount?: number | null;
}

export interface SoldRow {
  id?: number | null;
  order_id?: number | null;
  product_name?: string | null;
  quantity?: number | null;
  total_czk?: number | null;
  unit_price_czk?: number | null;
  unit_price?: number | null;
  price_czk?: number | null;
  price?: number | null;
  status?: string | null;
  customer_email?: string | null;
  vs?: string | null;
  sold_at?: string | null;
}

export interface SoldSummary {
  count?: number | null;
  total_amount?: number | null;
}

export interface SoldListResponse {
  rows: SoldRow[];
  summary?: SoldSummary | null;
}
