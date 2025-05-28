import logging
import time
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, List, Optional

from app.services.notification_service import NotificationService

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


class EmailTasks:
    """
    Background tasks for sending emails.
    """
    
    def __init__(self):
        """
        Initialize email tasks with notification service.
        """
        self.notification_service = NotificationService()
        logger.info("Email tasks initialized")
    
    @retry(max_attempts=3, delay=2.0, backoff=2.0)
    def send_order_confirmation_email(self, order_id: int, user_email: str) -> bool:
        """
        Send order confirmation email.
        
        Args:
            order_id: Order ID
            user_email: User's email address
            
        Returns:
            True if email was sent successfully, False otherwise
        """
        logger.info(f"Task: Sending order confirmation email for order {order_id} to {user_email}")
        
        # In a real implementation, you might fetch order details from the database here
        # For this example, we'll use the notification service directly
        
        result = self.notification_service.send_order_confirmation(
            order_id=order_id,
            user_email=user_email
        )
        
        if result:
            logger.info(f"Successfully sent order confirmation email for order {order_id}")
        else:
            logger.error(f"Failed to send order confirmation email for order {order_id}")
            
        return result
    
    @retry(max_attempts=3, delay=2.0, backoff=2.0)
    def send_order_cancellation_email(self, order_id: int, user_email: str) -> bool:
        """
        Send order cancellation email.
        
        Args:
            order_id: Order ID
            user_email: User's email address
            
        Returns:
            True if email was sent successfully, False otherwise
        """
        logger.info(f"Task: Sending order cancellation email for order {order_id} to {user_email}")
        
        result = self.notification_service.send_order_cancellation(
            order_id=order_id,
            user_email=user_email
        )
        
        if result:
            logger.info(f"Successfully sent order cancellation email for order {order_id}")
        else:
            logger.error(f"Failed to send order cancellation email for order {order_id}")
            
        return result
    
    @retry(max_attempts=3, delay=2.0, backoff=2.0)
    def send_event_cancellation_emails(
        self, event_id: int, event_title: str, event_date: str, user_emails: List[str]
    ) -> Dict[str, Any]:
        """
        Send event cancellation emails to all affected users.
        
        Args:
            event_id: Event ID
            event_title: Event title
            event_date: Event date
            user_emails: List of user email addresses
            
        Returns:
            Dictionary with results
        """
        logger.info(f"Task: Sending event cancellation emails for event {event_id} to {len(user_emails)} users")
        
        result = self.notification_service.send_event_cancellation_notification(
            event_id=event_id,
            event_title=event_title,
            event_date=event_date,
            user_emails=user_emails
        )
        
        logger.info(
            f"Event cancellation email task completed: "
            f"{result['successful']} successful, {result['failed']} failed"
        )
        
        return result
    
    @retry(max_attempts=3, delay=2.0, backoff=2.0)
    def send_event_reminder_emails(
        self, event_id: int, event_title: str, event_date: str, 
        event_location: str, user_emails: List[str]
    ) -> Dict[str, Any]:
        """
        Send event reminder emails to all ticket holders.
        
        Args:
            event_id: Event ID
            event_title: Event title
            event_date: Event date
            event_location: Event location
            user_emails: List of user email addresses
            
        Returns:
            Dictionary with results
        """
        logger.info(f"Task: Sending event reminder emails for event {event_id} to {len(user_emails)} users")
        
        results = {
            "total": len(user_emails),
            "successful": 0,
            "failed": 0,
            "failed_emails": []
        }
        
        for email in user_emails:
            try:
                success = self.notification_service.send_ticket_reminder(
                    event_id=event_id,
                    event_title=event_title,
                    event_date=event_date,
                    event_location=event_location,
                    user_email=email
                )
                
                if success:
                    results["successful"] += 1
                else:
                    results["failed"] += 1
                    results["failed_emails"].append(email)
            except Exception as e:
                logger.error(f"Error sending reminder email to {email}: {str(e)}")
                results["failed"] += 1
                results["failed_emails"].append(email)
        
        logger.info(
            f"Event reminder email task completed: "
            f"{results['successful']} successful, {results['failed']} failed"
        )
        
        return results


# Initialize email tasks
email_tasks = EmailTasks()


# Export functions that can be called directly as background tasks

def send_order_confirmation(order_id: int, user_email: str) -> bool:
    """
    Background task to send order confirmation email.
    """
    return email_tasks.send_order_confirmation_email(order_id, user_email)


def send_order_cancellation(order_id: int, user_email: str) -> bool:
    """
    Background task to send order cancellation email.
    """
    return email_tasks.send_order_cancellation_email(order_id, user_email)


def send_event_cancellation(event_id: int, event_title: str, event_date: str, user_emails: List[str]) -> Dict[str, Any]:
    """
    Background task to send event cancellation emails.
    """
    return email_tasks.send_event_cancellation_emails(event_id, event_title, event_date, user_emails)


def send_event_reminder(
    event_id: int, event_title: str, event_date: str, event_location: str, user_emails: List[str]
) -> Dict[str, Any]:
    """
    Background task to send event reminder emails.
    """
    return email_tasks.send_event_reminder_emails(event_id, event_title, event_date, event_location, user_emails)

