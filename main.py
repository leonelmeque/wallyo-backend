"""FastAPI application entry point."""

from fastapi import FastAPI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import core configuration (this will validate required env vars on import)
from app.core.config import settings  # noqa: E402
from app.core.logger import logger  # noqa: E402

# Import and register feature routers
from app.features.storage.routes import router as storage_router  # noqa: E402

# Initialize FastAPI app
app = FastAPI(
    title="Wallyo Server",
    description="Backup Storage API for encrypted SQLite backups",
    version="1.0.0",
)

# Log application startup
logger.info("Starting Wallyo Server")
logger.info(f"Log level: {settings.log_level}")

# Register feature routers
app.include_router(storage_router)
logger.info("Registered feature routers")


@app.get("/")
async def hello_world() -> dict[str, str]:
    """Health check endpoint."""
    logger.info("Health check endpoint accessed")
    return {"message": "Hello World", "status": "ok"}
