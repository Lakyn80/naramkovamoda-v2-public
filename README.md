# Naramkova Moda v2 (Public)

Production-oriented ecommerce project for custom bracelet sales.

This repository contains:
- FastAPI backend (`backend/`)
- Next.js 14 client storefront (`frontend/client/`)
- Next.js 14 admin panel (`frontend/admin/`)
- Docker setup for local development and production-style deployment (`docker/`, `docker-compose*.yml`)

## Tech Stack
- Backend: Python 3.11, FastAPI, SQLAlchemy, Pydantic
- Frontend: Next.js 14, React 18, TypeScript, Tailwind CSS
- Infra: Docker Compose, Redis

## Project Structure
- `backend/` API, modules, DB models, tests
- `frontend/client/` customer-facing storefront
- `frontend/admin/` admin UI
- `docker/` Dockerfiles for backend/client/admin
- `docker-compose.dev.yml` local development stack
- `docker-compose.prod.yml` production-style compose definition

## Main Features
- Product catalog, categories, variants, media
- Cart and checkout flow
- Admin CRUD for products/categories/media/payments/orders
- Media inbox workflows
- AI-related helper modules (template generation / pipelines)

## Local Development (Docker)
Requirements:
- Docker Desktop

1. Create env file for backend (do not commit secrets):
```bash
cp .env.example .env.dev
```

2. Start full dev stack:
```bash
docker compose -f docker-compose.dev.yml up --build
```

Default local ports:
- Backend API: `http://localhost:8088`
- Client FE: `http://localhost:3002`
- Admin FE: `http://localhost:3012`

## Local Development (Without Docker)
### Backend
```bash
cd backend
python -m venv .venv
# Windows
.\\.venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080
```

### Client FE
```bash
cd frontend/client
npm ci
npm run dev
```

### Admin FE
```bash
cd frontend/admin
npm ci
npm run dev
```

## Tests
```bash
pytest backend/tests
```

## Security Notes
- This public repository intentionally excludes runtime data, uploaded media, and secret files.
- Do not commit real `.env*` files or private keys.

## License
No license file is included yet. Add one before commercial/public reuse.