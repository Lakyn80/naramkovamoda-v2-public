# AI RAG – API KONTRAKT (návrh)

## 1) Upload médií
POST /api/media/upload

Vstup:
- multipart/form-data
- files[] = obrázky

Výstup:
{
  "session_id": "uuid",
  "uploaded_files": [
    {
      "media_id": "uuid",
      "filename": "bracelet1.jpg"
    }
  ]
}

---

## 2) Konverze do WebP + normalizace
POST /api/media/normalize

Vstup:
{
  "session_id": "uuid"
}

Co se stane:
- všechny obrázky v session se převedou na WebP
- původní soubory se zatím NEMAŽOU
- aktualizují se záznamy MediaAsset

Výstup:
{
  "session_id": "uuid",
  "status": "normalized"
}

---

## 3) Vision analýza + clustering
POST /api/media/analyze

Vstup:
{
  "session_id": "uuid"
}

Co se stane:
- zavolá Google Vision pro každý obrázek
- uloží vision_json
- vytvoří embeddingy
- provede clustering obrázků

Výstup:
{
  "session_id": "uuid",
  "status": "analyzed",
  "clusters": [
    {
      "cluster_id": "c1",
      "media_ids": ["m1","m2"]
    }
  ]
}

---

## 4) Generování draftů (RAG + Chroma)
POST /api/ai/generate-drafts

Vstup:
{
  "session_id": "uuid"
}

Co se stane:
- vybere hlavní cluster = návrh produktu
- ostatní podobné clustery = návrh variant
- použije RAG (Chroma) + Redis cache

Výstup:
{
  "session_id": "uuid",
  "draft_product": {
    "title": "...",
    "description": "...",
    "product_type": "bracelet"
  },
  "draft_variants": [
    {
      "variant_key": "color:pink",
      "media_ids": ["m3","m4"],
      "title_suffix": "v růžové barvě"
    }
  ]
}

---

## 5) Potvrzení klientem
POST /api/products/confirm-drafts

Vstup:
{
  "session_id": "uuid",
  "confirmed": true,
  "overrides": {
    "title": "Volitelné přepsání",
    "price": 149
  }
}

Co se stane:
- vytvoří reálný Product
- vytvoří ProductVariant(y)
- přiřadí Media k produktu
- smaže původní ne-webp soubory

Výstup:
{
  "product_id": 315,
  "status": "created"
}
