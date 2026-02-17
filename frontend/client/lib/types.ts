export interface ProductVariantMedia {
  id: number;
  image_url?: string | null;
  image_full_url?: string | null;
  image_thumb_url?: string | null;
  image?: string | null;
}

export interface ProductVariant {
  id: number;
  variant_name?: string | null;
  wrist_size?: string | null;
  stock?: number | null;
  price?: number | null;
  price_czk?: number | null;
  description?: string | null;
  image_url?: string | null;
  image_full_url?: string | null;
  image_thumb_url?: string | null;
  image?: string | null;
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
  price_czk?: number | null;
  stock?: number | null;
  active?: boolean | null;
  wrist_size?: number | string | null;
  category_id?: number | null;
  category_name?: string | null;
  category_slug?: string | null;
  image_url?: string | null;
  image_full_url?: string | null;
  image_thumb_url?: string | null;
  image?: string | null;
  media?: string[];
  media_items?: { id: number; filename: string; media_type: string; url: string }[];
  images?: string[];
  variants?: ProductVariant[];
  created_at?: string | null;
}

export interface Category {
  id: number;
  name: string;
  description?: string | null;
  slug?: string | null;
  group?: string | null;
  category?: string | null;
  products?: Product[];
}

export interface OrderItem {
  id: number;
  variantId?: number;
  name: string;
  quantity: number;
  price: number;
}

export interface Order {
  name: string;
  email: string;
  address: string;
  note?: string;
  vs: number;
  totalCzk: number;
  shippingCzk: number;
  shippingMode: "post" | "pickup";
  items: OrderItem[];
}
