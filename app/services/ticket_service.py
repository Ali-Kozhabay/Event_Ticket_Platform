import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.order import Order, OrderStatus
from app.models.user import User
from app.services.event_service import EventService
from app.services.order_service import OrderService

logger = logging.getLogger(__name__)


class TicketService:
    """
    Service for ticket-related operations.
    Note: In this implementation, tickets are represented by orders rather than a separate ticket model.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.order_service = OrderService(db)
        self.event_service = EventService(db)
    
    def verify_ticket(self, order_id: int) -> Dict[str, Any]:
        """
        Verify if a ticket (order) is valid.
        """
        order = self.order_service.get(id=order_id)
        
        if not order:
            return {
                "valid": False,
                "message": "Ticket not found",
            }
        
        # Check if order is paid
        if order.status != OrderStatus.PAID:
            return {
                "valid": False,
                "message": f"Ticket is not valid. Order status: {order.status}",
            }
        
        # Get event details
        event = self.event_service.get(id=order.event_id)
        
        if not event:
            return {
                "valid": False,
                "message": "Event not found",
            }
        
        # Check if event is canceled
        if event.is_canceled:
            return {
                "valid": False,
                "message": "Event is canceled",
            }
        
        # Get user details
        user = self.db.query(User).filter(User.id == order.user_id).first()
        
        if not user:
            return {
                "valid": False,
                "message": "User not found",
            }
        
        # Return ticket information
        return {
            "valid": True,
            "order_id": order.id,
            "event_id": event.id,
            "event_title": event.title,
            "event_date": event.start_date,
            "event_location": event.location,
            "user_id": user.id,
            "user_name": f"{user.first_name} {user.last_name}",
            "user_email": user.email,
            "quantity": order.quantity,
            "payment_status": order.status,
            "paid_at": order.paid_at,
        }
    
    def check_in_ticket(self, order_id: int) -> Dict[str, Any]:
        """
        Mark a ticket as used (checked in).
        In a real system, you might have a separate checked_in status for tickets.
        """
        # In a more complex system, you would have a separate Ticket model
        # with a checked_in field. For this implementation, we'll just
        # simulate the check-in process.
        
        # Verify the ticket first
        verification_result = self.verify_ticket(order_id=order_id)
        
        if not verification_result["valid"]:
            return {
                "success": False,
                "message": verification_result["message"],
            }
        
        # In a real system, update the ticket status to checked in
        # For now, just return success
        return {
            "success": True,
            "message": "Ticket checked in successfully",
            "order_id": order_id,
            "event_title": verification_result["event_title"],
            "user_name": verification_result["user_name"],
            "check_in_time": "Current timestamp would be recorded here",
        }
    
    def get_user_tickets(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Get all tickets for a user.
        """
        # Get all paid orders for the user
        orders = (
            self.db.query(Order)
            .filter(Order.user_id == user_id, Order.status == OrderStatus.PAID)
            .all()
        )
        
        tickets = []
        for order in orders:
            # Get event details
            event = self.event_service.get(id=order.event_id)
            
            if not event:
                continue
            
            tickets.append({
                "order_id": order.id,
                "event_id": event.id,
                "event_title": event.title,
                "event_date": event.start_date,
                "event_location": event.location,
                "quantity": order.quantity,
                "total_amount": order.total_amount,
                "payment_status": order.status,
                "is_canceled": event.is_canceled,
            })
        
        return tickets
    
    def get_event_attendees(self, event_id: int) -> List[Dict[str, Any]]:
        """
        Get all attendees for an event.
        """
        # Get all paid orders for the event
        orders = (
            self.db.query(Order)
            .filter(Order.event_id == event_id, Order.status == OrderStatus.PAID)
            .all()
        )
        
        attendees = []
        for order in orders:
            # Get user details
            user = self.db.query(User).filter(User.id == order.user_id).first()
            
            if not user:
                continue
            
            attendees.append({
                "order_id": order.id,
                "user_id": user.id,
                "user_name": f"{user.first_name} {user.last_name}",
                "user_email": user.email,
                "quantity": order.quantity,
                "paid_at": order.paid_at,
            })
        
        return attendees

