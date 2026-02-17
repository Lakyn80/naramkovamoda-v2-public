# Jak spustit a otestovat Vision + RAG + LLM

## Běh přes Docker (doporučeno)

### 1. Spuštění backendu v Dockeru

Z **kořene projektu** (tam, kde je `docker-compose.dev.yml`):

```bash
docker compose -f docker-compose.dev.yml up -d backend
```

Backend poběží na **http://localhost:8088** (port 8080 v kontejneru je mapovaný na 8088).

- Databáze: `./data` je namountovaná jako `/app/data` (v `.env.dev` je `NMM_DATABASE_URL=sqlite:////app/data/database.db`).
- Uploady: `./backend/static/uploads` → `/app/static/uploads`.
- Chroma (RAG): volume `rag_chroma_data` – seed šablony přežijí restart kontejneru.
- V kontejneru je nastavené `RUNNING_IN_DOCKER=1`, takže cesty k uploadům jsou správně `/app/static/uploads`.

### 2. Seed RAG šablon (jednou po startu, nebo po změně kategorií)

```bash
curl -X POST http://localhost:8088/api/ai/rag/seed-templates
```

Očekávaná odpověď:

```json
{"status":"ok","outcomes":{"bracelet":true,"candle":true,"necklace":true,"earrings":true,"decor":true,"other":true}}
```

### 3. Test generování draftu

Produkt musí mít v DB záznamy v `product_media` a soubory v `backend/static/uploads/`.

```bash
curl http://localhost:8088/api/ai/rag/drafts/284
```

(Číslo `284` nahraď reálným `product_id`.)

### 4. Volitelně – LLM (DeepSeek) v Dockeru

V `docker-compose.dev.yml` u služby `backend` můžeš přidat do `environment`:

```yaml
environment:
  RUNNING_IN_DOCKER: "1"
  DEEPSEEK_API_KEY: "sk-tvůj-klíč"
```

Nebo klíč předat z hosta (bez zápisu do souboru):

```bash
docker compose -f docker-compose.dev.yml run -e DEEPSEEK_API_KEY=sk-... backend ...
```

Pro trvalé použití LLM je nejčistší doplnit `DEEPSEEK_API_KEY` do `.env.dev` a v docker-compose použít `env_file: [.env.dev]` (už tam je) – do `.env.dev` přidej řádek `DEEPSEEK_API_KEY=sk-...`.

### 5. Google Vision v Dockeru

Pro analýzu obrázků musí kontejner mít přístup k Google Cloud credentials. Můžeš namountovat soubor s JSON klíčem:

V `docker-compose.dev.yml` u `backend` přidej do `volumes`:

```yaml
- ./path/to/your-google-credentials.json:/app/gcp-credentials.json
```

A do `environment`:

```yaml
GOOGLE_APPLICATION_CREDENTIALS: "/app/gcp-credentials.json"
```

### 6. Užitečné příkazy

- Logy backendu:  
  `docker compose -f docker-compose.dev.yml logs -f backend`
- Zastavení:  
  `docker compose -f docker-compose.dev.yml down`
- Restart pouze backendu:  
  `docker compose -f docker-compose.dev.yml up -d --build backend`

---

## Lokální běh (bez Dockeru)

### 1. Závislosti

```bash
cd backend
pip install -r requirements.txt
```

### 2. Proměnné prostředí

- **Databáze:**  
  `NMM_DATABASE_URL=sqlite:///C:/Users/.../data/database.db`
- **Nepoužívej** `RUNNING_IN_DOCKER` – uploady půjdou do `backend/static/uploads`.
- **LLM:** `DEEPSEEK_API_KEY=sk-...` (volitelné).
- **Vision:** `GOOGLE_APPLICATION_CREDENTIALS` (cesta k JSON klíči).

### 3. Spuštění

```bash
cd backend
uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8080 --reload
```

Backend: **http://localhost:8080**.

### 4. Seed a test

```bash
curl -X POST http://localhost:8080/api/ai/rag/seed-templates
curl http://localhost:8080/api/ai/rag/drafts/284
```

---

## Časté problémy

- **„Soubor nenalezen“** – v Dockeru musí být volume `./backend/static/uploads` namountované; v `product_media` musí být `filename` = jen název souboru (např. `xxx.webp`).
- **Prázdné `combined_tags`** – Vision API: zkontroluj Google credentials (v Dockeru mount + `GOOGLE_APPLICATION_CREDENTIALS`).
- **Draft bez LLM stylu** – není nastavený `DEEPSEEK_API_KEY`; použije se fallback šablona.
- **Chyba při seedu** – v DB musí být produkty s vyplněným názvem, popisem a kategorií.
