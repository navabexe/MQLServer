from fastapi import FastAPI
from src.api.routes import router
from src.utils.logger import logger
from src.data.mt5_client import MT5Client

app = FastAPI(title="Trading API", description="API for trading operations with MetaTrader 5")
app.include_router(router, prefix="/trading")

def start_api():
    """Start the FastAPI server."""
    try:
        mt5_client = MT5Client()
        if not mt5_client.connect():
            logger.error("Failed to connect to MT5")
            return
        logger.info("Starting FastAPI server...")
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=5000)
    except Exception as e:
        logger.error(f"Error starting API server: {e}")