import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models.event import Event
from app.models.order import Order
from app.schemas.event import EventCreate, EventUpdate

logger = logging.getLogger(__name__)


class EventService:
    """
    Service for event-related operations.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def get(self, id: int) -> Optional[Event]:
        """
        Get an event by ID.
        """
        return self.db.query(Event).filter(Event.id == id).first()
    
    def get_multi(
        self,
        skip: int = 0,
        limit: int = 100,
        location: Optional[str] = None,
        upcoming: Optional[bool] = None,
        published_only: bool = False,
    ) -> List[Event]:
        """
        Get multiple events with optional filtering.
        """
        query = self.db.query(Event)
        
        # Apply filters
        if published_only:
            query = query.filter(Event.is_published == True)
        
        if location:
            query = query.filter(Event.location.ilike(f"%{location}%"))
        
        if upcoming is True:
            now = datetime.utcnow()
            query = query.filter(Event.start_date > now)
        elif upcoming is False:
            now = datetime.utcnow()
            query = query.filter(Event.start_date <= now)
        
        # Order by date (closest upcoming first)
        query = query.order_by(Event.start_date)
        
        # Apply pagination
        return query.offset(skip).limit(limit).all()
    
    def create(self, event_create: EventCreate) -> Event:
        """
        Create a new event.
        """
        # Create a new event object
        db_event = Event(
            title=event_create.title,
            description=event_create.description,
            location=event_create.location,
            start_date=event_create.start_date,
            end_date=event_create.end_date,
            image_url=event_create.image_url,
            total_capacity=event_create.total_capacity,
            available_tickets=event_create.total_capacity,  # Initially all tickets are available
            ticket_price=event_create.ticket_price,
            is_published=event_create.is_published,
        )
        
        # Add event to database
        self.db.add(db_event)
        self.db.commit()
        self.db.refresh(db_event)
        
        logger.info(f"Created new event: {db_event.title}")
        return db_event
    
    def update(self, event: Event, event_update: EventUpdate) -> Event:
        """
        Update an event.
        """
        # Update event attributes
        update_data = event_update.dict(exclude_unset=True)
        
        # If total_capacity is being changed, adjust available_tickets accordingly
        if "total_capacity" in update_data:
            # Calculate the difference in capacity
            capacity_diff = update_data["total_capacity"] - event.total_capacity
            
            # Adjust available tickets by the same amount
            new_available = event.available_tickets + capacity_diff
            
            # Ensure we don't have negative available tickets
            if new_available < 0:
                # Check if tickets have already been sold beyond the new capacity
                tickets_sold = event.total_capacity - event.available_tickets
                if tickets_sold > update_data["total_capacity"]:
                    raise ValueError(
                        f"Cannot reduce capacity below tickets already sold ({tickets_sold})"
                    )
                new_available = 0
            
            update_data["available_tickets"] = new_available
        
        # Update event attributes
        for field, value in update_data.items():
            setattr(event, field, value)
        
        # Commit changes to database
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        
        logger.info(f"Updated event: {event.title}")
        return event
    
    def delete(self, id: int) -> None:
        """
        Delete an event.
        """
        event = self.get(id=id)
        if event:
            self.db.delete(event)
            self.db.commit()
            logger.info(f"Deleted event: {event.title}")
    
    def has_orders(self, event_id: int) -> bool:
        """
        Check if an event has any orders.
        """
        return self.db.query(Order).filter(Order.event_id == event_id).first() is not None
    
    def decrease_available_tickets(self, event_id: int, quantity: int) -> bool:
        """
        Decrease available tickets for an event.
        Returns True if successful, False if not enough tickets available.
        """
        event = self.get(id=event_id)
        
        if not event or event.is_canceled:
            return False
        
        if event.available_tickets < quantity:
            return False
        
        # Decrease available tickets
        event.available_tickets -= quantity
        
        # Commit changes to database
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        
        logger.info(f"Decreased available tickets for event {event.title} by {quantity}")
        return True
    
    def increase_available_tickets(self, event_id: int, quantity: int) -> bool:
        """
        Increase available tickets for an event (e.g., after order cancellation).
        """
        event = self.get(id=event_id)
        
        if not event:
            return False
        
        # Increase available tickets, but don't exceed total capacity
        new_available = min(event.available_tickets + quantity, event.total_capacity)
        event.available_tickets = new_available
        
        # Commit changes to database
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        
        logger.info(f"Increased available tickets for event {event.title} by {quantity}")
        return True

