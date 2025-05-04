from src.data.mt5_client import MT5Client
from fastapi import Depends, HTTPException

# Global MT5Client instance
_mt5_client = None

def get_mt5_client() -> MT5Client:
    """Dependency to get the global MT5Client instance."""
    global _mt5_client
    if _mt5_client is None:
        _mt5_client = MT5Client()
        if not _mt5_client.connect():
            raise HTTPException(status_code=503, detail="Failed to connect to MT5")
    if not _mt5_client.connected:
        if not _mt5_client.connect():
            raise HTTPException(status_code=503, detail="MT5 service unavailable")
    return _mt5_client