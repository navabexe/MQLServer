from typing import Dict, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import ValidationError
import MetaTrader5 as mt5
from src.core.order_manager import OrderManager
from src.core.state_manager import get_state_manager, StateManager
from src.core.stop_loss_manager import StopLossManager
from src.api.dependencies import get_mt5_client
from src.data.mt5_client import MT5Client
from src.utils.config import AVAILABLE_SYMBOLS
from src.models.order import OrderRequest
from src.models.price import PriceRequest
from src.models.position import Position
from src.models.mt5_status import MT5Status
from src.models.order_response import OrderResponse
from src.utils.logger import logger

# Initialize the API router with a prefix and tags for better organization
router = APIRouter(
    prefix="/trading",
    tags=["Trading"],
    responses={500: {"description": "Internal Server Error"}}
)

@router.post(
    "/get_price",
    response_model=Dict[str, str | float],
    summary="Get current price for a symbol",
    description="Fetches the current bid and ask prices for a given trading symbol from MetaTrader 5."
)
async def get_price(request: PriceRequest, mt5_client: MT5Client = Depends(get_mt5_client)) -> Dict[str, str | float]:
    """
    Get the current price for a specified trading symbol.

    Args:
        request (PriceRequest): A request body containing the symbol (e.g., "BTCUSD").
        mt5_client (MT5Client): The MT5Client instance (injected via dependency).

    Returns:
        Dict[str, str | float]: A dictionary containing the status, symbol, bid, and ask prices.

    Raises:
        HTTPException: If the symbol is missing (400) or if fetching the price fails (400 or 500).
    """
    try:
        symbol = request.symbol
        if not symbol:
            logger.error("Symbol is required in the request body")
            raise HTTPException(status_code=400, detail="Symbol is required")

        price_info = mt5_client.get_current_price(symbol)
        if not price_info:
            logger.error(f"Failed to fetch price for symbol: {symbol}")
            raise HTTPException(status_code=400, detail="Failed to get price")

        return {
            "status": "success",
            "symbol": symbol,
            "bid": price_info["bid"],
            "ask": price_info["ask"]
        }
    except HTTPException as e:
        raise e  # Re-raise HTTP exceptions to return the correct status code
    except Exception as e:
        logger.error(f"Error getting price for symbol {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post(
    "/place_order",
    response_model=OrderResponse,
    summary="Place a new trading order",
    description="Places a new trading order in MetaTrader 5 with the specified parameters."
)
async def place_order(order: OrderRequest) -> OrderResponse:
    """
    Place a new trading order in MetaTrader 5.

    Args:
        order (OrderRequest): The order details including symbol, entry price, stop loss, etc.

    Returns:
        OrderResponse: A dictionary containing the status, message, and order ID.

    Raises:
        HTTPException: If validation fails (400) or if order placement fails (400 or 500).
    """
    try:
        order_manager = OrderManager()
        response = order_manager.place_order(order)
        if response["status"] == "error":
            logger.error(f"Failed to place order: {response['message']}")
            raise HTTPException(status_code=400, detail=response["message"])
        return response
    except ValidationError as e:
        logger.error(f"Validation error while placing order: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error placing order: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get(
    "/get_all_orders_and_positions",
    response_model=List[Position],
    summary="Retrieve all orders and positions",
    description="Fetches all open positions and pending orders from MetaTrader 5."
)
async def get_all_orders_and_positions() -> List[Position]:
    """
    Retrieve a list of all open positions and pending orders.

    Returns:
        List[Position]: A list of Position objects containing order details.

    Raises:
        HTTPException: If fetching orders fails (500).
    """
    try:
        order_manager = OrderManager()
        orders_and_positions = order_manager.get_all_orders_and_positions()
        return orders_and_positions
    except Exception as e:
        logger.error(f"Error retrieving orders and positions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post(
    "/switch_account",
    response_model=Dict[str, str],
    summary="Switch MetaTrader 5 account",
    description="Switches to a different MetaTrader 5 account."
)
async def switch_account(account: str, mt5_client: MT5Client = Depends(get_mt5_client)) -> Dict[str, str]:
    """
    Switch to a different MetaTrader 5 account.

    Args:
        account (str): The account type to switch to (e.g., "real").
        mt5_client (MT5Client): The MT5Client instance (injected via dependency).

    Returns:
        Dict[str, str]: A dictionary containing the status and message about the account switch.

    Raises:
        HTTPException: If the account is missing (400) or if switching fails (400 or 500).
    """
    try:
        if not account:
            logger.error("Account type is required in the request body")
            raise HTTPException(status_code=400, detail="Account is required")

        response = mt5_client.switch_account(account)
        if response["status"] == "error":
            logger.error(f"Failed to switch account: {response['message']}")
            raise HTTPException(status_code=400, detail=response["message"])
        return response
    except Exception as e:
        logger.error(f"Error switching account: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get(
    "/available_symbols",
    response_model=Dict[str, str | List[str]],
    summary="Retrieve available trading symbols",
    description="Fetches the list of available trading symbols defined in the configuration."
)
async def available_symbols() -> Dict[str, str | List[str]]:
    """
    Retrieve the list of available trading symbols.

    Returns:
        Dict[str, str | List[str]]: A dictionary containing the status and list of symbols.

    Raises:
        HTTPException: If fetching symbols fails (500).
    """
    try:
        return {"status": "success", "symbols": AVAILABLE_SYMBOLS}
    except Exception as e:
        logger.error(f"Error retrieving available symbols: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post(
    "/risk_free",
    response_model=Dict[str, str | int | float],
    summary="Make a position risk-free",
    description="Sets the stop loss of a position to its entry price to make it risk-free."
)
async def risk_free(ticket_id: int) -> Dict[str, str | int | float]:
    """
    Set the stop loss of a position to its entry price to make it risk-free.

    Args:
        ticket_id (int): The ticket ID of the position to make risk-free.

    Returns:
        Dict[str, str | int | float]: A dictionary containing the status, message, ticket ID, and new stop loss.

    Raises:
        HTTPException: If the ticket ID is missing (400) or if the operation fails (400 or 500).
    """
    try:
        if not ticket_id:
            logger.error("Ticket ID is required in the request body")
            raise HTTPException(status_code=400, detail="Ticket ID is required")

        stop_loss_manager = StopLossManager()
        response = stop_loss_manager.make_risk_free(ticket_id)
        if response["status"] == "error":
            logger.error(f"Failed to make position risk-free: {response['message']}")
            raise HTTPException(status_code=400, detail=response["message"])
        return response
    except Exception as e:
        logger.error(f"Error making position risk-free: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get(
    "/mt5_status",
    response_model=MT5Status,
    summary="Get MetaTrader 5 connection status",
    description="Returns the current connection status and account information for MetaTrader 5."
)
async def mt5_status(mt5_client: MT5Client = Depends(get_mt5_client)) -> MT5Status:
    """
    Get the current connection status and account information for MetaTrader 5.

    Args:
        mt5_client (MT5Client): The MT5Client instance (injected via dependency).

    Returns:
        MT5Status: A dictionary containing the connection status and account details.

    Raises:
        HTTPException: If fetching account info fails (500).
    """
    try:
        account_info = mt5.account_info()
        if not account_info:
            logger.error("Failed to retrieve MT5 account info")
            raise HTTPException(status_code=500, detail="Failed to retrieve MT5 account info")

        return MT5Status(
            connected=mt5_client.connected,
            login=account_info.login,
            server=account_info.server,
            company=account_info.company,
            balance=account_info.balance,
            equity=account_info.equity,
            margin=account_info.margin
        )
    except Exception as e:
        logger.error(f"Error retrieving MT5 status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post(
    "/reset_order_count",
    response_model=Dict[str, str],
    summary="Reset daily order count",
    description="Resets the daily order count to allow placing new orders."
)
async def reset_order_count(state_manager: StateManager = Depends(get_state_manager)) -> Dict[str, str]:
    """
    Reset the daily order count to allow placing new orders.

    Args:
        state_manager (StateManager): The StateManager instance (injected via dependency).

    Returns:
        Dict[str, str]: A dictionary containing the status and message about the reset operation.

    Raises:
        HTTPException: If resetting fails (500).
    """
    try:
        state_manager.reset_order_count()
        return {"status": "success", "message": "Daily order count reset successfully"}
    except Exception as e:
        logger.error(f"Error resetting daily order count: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post(
    "/cancel_pending_orders",
    response_model=Dict[str, str | int],
    summary="Cancel all pending orders",
    description="Cancels all pending orders and adjusts the daily order count accordingly."
)
async def cancel_pending_orders() -> Dict[str, str | int]:
    """
    Cancel all pending orders and adjust the daily order count.

    Returns:
        Dict[str, str | int]: A dictionary containing the status, message, and number of canceled orders.

    Raises:
        HTTPException: If canceling fails (500).
    """
    try:
        order_manager = OrderManager()
        response = order_manager.cancel_pending_orders()
        return response
    except Exception as e:
        logger.error(f"Error in cancel_pending_orders API: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")