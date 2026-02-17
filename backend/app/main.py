import re

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.paths import UPLOAD_DIR

from app.modules.auth.router import router as auth_router
from app.modules.admin.router import router as admin_router
from app.modules.users.router import router as users_router
from app.modules.products.router import router as products_router
from app.modules.categories.router import router as categories_router
from app.modules.media.router import router as media_router
from app.modules.media_inbox.router import router as media_inbox_router
from app.modules.media_second_inbox.router import router as media_second_inbox_router
from app.modules.orders.router import router as orders_router
from app.modules.payments.router import router as payments_router
from app.modules.email.router import router as email_router
from app.modules.invoice.router import router as invoice_router
from app.modules.sold.router import router as sold_router
from app.modules.ai.vision.router import router as ai_vision_router
from app.modules.ai.rag.router import router as ai_rag_router
from app.modules.ai.deepseek.router import router as ai_deepseek_router
from app.modules.ai.drafts.router import router as ai_drafts_router
from app.modules.ai.templates.router import router as ai_templates_router
from app.modules.ai.openai_vision.router import router as openai_vision_router
from app.modules.ai.pipeline.router import router as ai_pipeline_router
from app.modules.feeds.gmc.router import router as gmc_feed_router


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
    )

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    if settings.cors_origins.strip():
        allowed_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    else:
        allowed_origins = [
            "http://localhost:3012",
            "http://127.0.0.1:3012",
            "http://localhost:3001",
            "http://127.0.0.1:3001",
            "http://localhost:3002",
            "http://127.0.0.1:3002",
            "http://localhost:8088",
            "http://127.0.0.1:8088",
        ]
    # Regex: libovolný port na localhost / 127.0.0.1 (pro dev a Media Inbox na 3012)
    allow_origin_regex = r"^http://(localhost|127\.0\.0\.1)(:\d+)?$"

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_origin_regex=allow_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    @app.middleware("http")
    async def ensure_cors_headers(request, call_next):
        response = await call_next(request)
        origin = request.headers.get("origin")
        if not origin:
            return response
        if origin in allowed_origins or re.match(allow_origin_regex, origin):
            response.headers["access-control-allow-origin"] = origin
            response.headers["access-control-allow-credentials"] = "true"
            response.headers["vary"] = "Origin"
        return response

    app.mount("/static", StaticFiles(directory="static"), name="static")

    # Core modules
    app.include_router(auth_router)
    app.include_router(admin_router)
    app.include_router(users_router)
    app.include_router(products_router)
    app.include_router(categories_router)
    app.include_router(media_router)
    app.include_router(media_inbox_router)
    app.include_router(media_second_inbox_router)
    app.include_router(orders_router)
    app.include_router(payments_router)
    app.include_router(email_router)
    app.include_router(sold_router)

    # AI modules
    app.include_router(ai_vision_router)
    app.include_router(ai_rag_router)
    app.include_router(ai_deepseek_router)
    app.include_router(ai_drafts_router)
    app.include_router(ai_templates_router)
    app.include_router(openai_vision_router)
    app.include_router(ai_pipeline_router)
    app.include_router(gmc_feed_router)

    # Invoice API is optional and disabled by default
    if settings.expose_invoice_api:
        app.include_router(invoice_router)

    return app


app = create_app()
