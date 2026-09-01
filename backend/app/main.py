import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import init_db
from app.api import (
    prompt,
    providers,
    comfyui,
    characters,
    artists,
    loras,
    rules,
    presets,
    history,
    settings as settings_api
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database...")
    init_db()
    logger.info(f"{settings.APP_NAME} backend started.")
    yield
    logger.info("Shutting down...")

app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    description="Anima Prompt Studio - Local-first Anime Prompt & Generation Workbench",
    lifespan=lifespan
)

# CORS middleware for local Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(prompt.router, prefix="/api")
app.include_router(providers.router, prefix="/api")
app.include_router(comfyui.router, prefix="/api")
app.include_router(characters.router, prefix="/api")
app.include_router(artists.router, prefix="/api")
app.include_router(loras.router, prefix="/api")
app.include_router(rules.router, prefix="/api")
app.include_router(presets.router, prefix="/api")
app.include_router(history.router, prefix="/api")
app.include_router(settings_api.router, prefix="/api")

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": "0.1.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
