import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.order import Order, OrderStatus
from app.schemas.order import OrderRead
from app.services.event_service import EventService

logger = logging.getLogger(__name__)


class OrderService:
    """
    Service for order-related operations.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.event_service = EventService(db)
    
    def get_user_orders(
        self, user_id: int, skip: int = 0, limit: int = 100, status: Optional[OrderStatus] = None
    ) -> List[Order]:
        """
        Get orders for a specific user.
        """
        query = self.db.query(Order).filter(Order.user_id == user_id)
        
        if status:
            query = query.filter(Order.status == status)
            
        return (
            query
            .order_by(Order.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        
    def get_all_orders(
        self, skip: int = 0, limit: int = 100, status: Optional[OrderStatus] = None
    ) -> List[Order]:
        """
        Get all orders with optional filtering (admin function).
        """
        query = self.db.query(Order)
        
        if status:
            query = query.filter(Order.status == status)
            
        return (
            query
            .order_by(Order.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        

            .order_by(Order.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def create(
        self, user_id: int, event_id: int, quantity: int, payment_method: str, unit_price: float
    ) -> Order:
        """
        Create a new order.
        """
        # Calculate total amount
        total_amount = unit_price * quantity
        
        # Create a new order object
        db_order = Order(
            user_id=user_id,
            event_id=event_id,
            quantity=quantity,
            unit_price=unit_price,
            total_amount=total_amount,
            status=OrderStatus.PENDING,
            payment_method=payment_method,
        )
        
        # Add order to database
        self.db.add(db_order)
        self.db.commit()
        self.db.refresh(db_order)
        
        # Reserve tickets by decreasing available tickets for the event
        success = self.event_service.decrease_available_tickets(
            event_id=event_id, quantity=quantity
        )
        
        if not success:
            # If ticket reservation fails, delete the order and raise an error
            self.db.delete(db_order)
            self.db.commit()
            raise ValueError("Failed to reserve tickets. Not enough available tickets.")
        
        logger.info(f"Created new order: {db_order.id} for user {user_id}, event {event_id}")
        return db_order
    
    def update_status(
        self, order_id: int, status: OrderStatus, payment_id: Optional[str] = None
    ) -> Order:
        """
        Update the status of an order.
        """
        order = self.get(id=order_id)
        
        if not order:
            raise ValueError("Order not found")
        
        # Update order status
        order.status = status
        
        # Update payment ID if provided
        if payment_id:
            order.payment_id = payment_id
        
        # Update paid_at timestamp if status is PAID
        if status == OrderStatus.PAID:
            order.paid_at = datetime.utcnow()
        
        # Commit changes to database
        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)
        
        logger.info(f"Updated order {order.id} status to {status}")
        return order
    
    def cancel_order(self, order_id: int, refund_id: Optional[str] = None) -> Order:
        """
        Cancel an order.
        """
        order = self.get(id=order_id)
        
        if not order:
            raise ValueError("Order not found")
        
        # Update order status to CANCELED
        order.status = OrderStatus.CANCELED
        
        # Update payment ID with refund ID if provided
        if refund_id:
            order.payment_id = f"{order.payment_id}:refund:{refund_id}"
        
        # Commit changes to database
        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)
        
        logger.info(f"Canceled order {order.id}")
        return order
    
    def get_order_with_event_details(self, order_id: int) -> Optional[OrderRead]:
        """
        Get an order with event details.
        """
        order = self.get(id=order_id)
        
        if not order:
            return None
        
        # Get event details
        event = self.event_service.get(id=order.event_id)
        
        if not event:
            return None
        
        # Create OrderRead object
        order_read = OrderRead(
            id=order.id,
            user_id=order.user_id,
            event_id=order.event_id,
            quantity=order.quantity,
            unit_price=order.unit_price,
            total_amount=order.total_amount,
            status=order.status,
            payment_id=order.payment_id,
            payment_method=order.payment_method,
            created_at=order.created_at,
            updated_at=order.updated_at,
            paid_at=order.paid_at,
            event_title=event.title,
            event_date=event.start_date,
        )
        
        return order_read

