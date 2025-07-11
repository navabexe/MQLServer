from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.routes import router
from src.utils.scheduler import start_scheduler
from src.utils.logger import logger
from src.api.dependencies import get_mt5_client
import threading
import MetaTrader5 as mt5

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage the lifespan of the FastAPI application."""
    # Startup tasks
    try:
        # Initialize MT5 connection
        mt5_client = get_mt5_client()

        # Log MT5 connection details
        account_info = mt5.account_info()
        if account_info:
            logger.info("MT5 Connection Details", extra={
                "login": account_info.login,
                "server": account_info.server,
                "company": account_info.company,
                "balance": account_info.balance,
                "equity": account_info.equity,
                "margin": account_info.margin,
                "connected": mt5_client.connected
            })
        else:
            logger.error("Failed to retrieve MT5 account info")

        # Start scheduler in a separate thread
        scheduler_thread = threading.Thread(target=start_scheduler, daemon=True)
        scheduler_thread.start()
        logger.info("Scheduler started")

        logger.info("Trading API started")
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise

    yield  # Application is running

    # Shutdown tasks
    logger.info("Trading API stopped")

# Create FastAPI app instance
app = FastAPI(
    title="Trading API",
    version="1.0.0",
    description="API for trading operations with MetaTrader 5",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (modify as needed)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
try:
    app.include_router(router)
    logger.info("Successfully included trading routers")
except Exception as e:
    logger.error(f"Failed to include trading routers: {e}")
    raise