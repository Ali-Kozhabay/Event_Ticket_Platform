import logging
import time
from datetime import datetime
from functools import wraps
from typing import Any, Dict, Optional

from app.services.payment_service import PaymentService
from app.services.order_service import OrderService
from app.models.order import OrderStatus

logger = logging.getLogger(__name__)


def retry(max_attempts: int = 3, delay: float = 2.0, backoff: float = 2.0, exceptions: tuple = (Exception,)):
    """
    Retry decorator with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Backoff multiplier (e.g., 2.0 means delay doubles after each retry)
        exceptions: Tuple of exceptions to catch and retry on
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            mtries, mdelay = max_attempts, delay
            while mtries > 1:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    logger.warning(
                        f"Retry: {func.__name__} failed with {str(e)}. "
                        f"Retrying in {mdelay:.2f} seconds... ({mtries-1} attempts left)"
                    )
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            return func(*args, **kwargs)
        return wrapper
    return decorator


class PaymentTasks:
    """
    Background tasks for payment processing.
    """
    
    def __init__(self):
        """
        Initialize payment tasks with payment service.
        """
        self.payment_service = PaymentService()
        logger.info("Payment tasks initialized")
    
    @retry(max_attempts=3, delay=2.0, backoff=2.0)
    def process_payment_async(
        self, 
        order_id: int, 
        amount: float, 
        payment_method: str, 
        payment_details: Dict[str, Any],
        db_session
    ) -> Dict[str, Any]:
        """
        Process payment asynchronously.
        
        Args:
            order_id: Order ID
            amount: Payment amount
            payment_method: Payment method
            payment_details: Payment details
            db_session: Database session
            
        Returns:
            Dictionary with payment result
        """
        logger.info(f"Task: Processing payment for order {order_id}, amount ${amount:.2f}")
        
        try:
            # Process payment
            payment_result = self.payment_service.process_payment(
                amount=amount,
                payment_method=payment_method,
                payment_details=payment_details
            )
            
            # Update order status based on payment result
            order_service = OrderService(db_session)
            
            if payment_result["success"]:
                order_service.update_status(
                    order_id=order_id,
                    status=OrderStatus.PAID,
                    payment_id=payment_result["payment_id"]
                )
                logger.info(f"Payment successful for order {order_id}: {payment_result['payment_id']}")
            else:
                logger.warning(f"Payment failed for order {order_id}: {payment_result.get('error', 'Unknown error')}")
            
            return payment_result
            
        except Exception as e:
            logger.error(f"Error processing payment for order {order_id}: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": f"Payment processing error: {str(e)}"
            }
    
    @retry(max_attempts=3, delay=2.0, backoff=2.0)
    def process_refund_async(
        self, 
        order_id: int, 
        payment_id: str, 
        amount: Optional[float] = None,
        db_session = None
    ) -> Dict[str, Any]:
        """
        Process refund asynchronously.
        
        Args:
            order_id: Order ID
            payment_id: Payment ID
            amount: Refund amount (if None, full refund is assumed)
            db_session: Database session
            
        Returns:
            Dictionary with refund result
        """
        logger.info(f"Task: Processing refund for order {order_id}, payment {payment_id}")
        
        try:
            # Process refund
            refund_result = self.payment_service.process_refund(
                payment_id=payment_id,
                amount=amount,
                reason=f"Order {order_id} cancellation"
            )
            
            # Update order status based on refund result
            if db_session and refund_result["success"]:
                order_service = OrderService(db_session)
                order_service.update_status(
                    order_id=order_id,
                    status=OrderStatus.REFUNDED,
                    payment_id=f"{payment_id}:refund:{refund_result['refund_id']}"
                )
                logger.info(f"Refund successful for order {order_id}: {refund_result['refund_id']}")
            elif not refund_result["success"]:
                logger.warning(f"Refund failed for order {order_id}: {refund_result.get('error', 'Unknown error')}")
            
            return refund_result
            
        except Exception as e:
            logger.error(f"Error processing refund for order {order_id}: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": f"Refund processing error: {str(e)}"
            }


# Initialize payment tasks
payment_tasks = PaymentTasks()


# Export functions that can be called directly as background tasks

def process_payment(
    order_id: int, 
    amount: float, 
    payment_method: str, 
    payment_details: Dict[str, Any],
    db_session
) -> Dict[str, Any]:
    """
    Background task to process payment.
    """
    return payment_tasks.process_payment_async(
        order_id=order_id,
        amount=amount,
        payment_method=payment_method,
        payment_details=payment_details,
        db_session=db_session
    )


def process_refund(
    order_id: int, 
    payment_id: str, 
    amount: Optional[float] = None,
    db_session = None
) -> Dict[str, Any]:
    """
    Background task to process refund.
    """
    return payment_tasks.process_refund_async(
        order_id=order_id,
        payment_id=payment_id,
        amount=amount,
        db_session=db_session
    )

