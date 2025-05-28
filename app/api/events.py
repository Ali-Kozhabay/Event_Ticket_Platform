from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_active_user, get_current_admin_user, get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.event import EventCreate, EventList, EventRead, EventUpdate
from app.services.event_service import EventService

router = APIRouter()


@router.get("", response_model=List[EventList])
def read_events(
    skip: int = 0,
    limit: int = 100,
    location: Optional[str] = None,
    upcoming: Optional[bool] = Query(None, description="Filter for upcoming events"),
    db: Session = Depends(get_db),
) -> Any:
    """
    Retrieve events with optional filtering.
    """
    event_service = EventService(db)
    return event_service.get_multi(
        skip=skip, limit=limit, location=location, upcoming=upcoming
    )


@router.get("/published", response_model=List[EventList])
def read_published_events(
    skip: int = 0,
    limit: int = 100,
    location: Optional[str] = None,
    upcoming: Optional[bool] = Query(None, description="Filter for upcoming events"),
    db: Session = Depends(get_db),
) -> Any:
    """
    Retrieve published events with optional filtering.
    """
    event_service = EventService(db)
    return event_service.get_multi(
        skip=skip, limit=limit, location=location, upcoming=upcoming, published_only=True
    )


@router.post("", response_model=EventRead, status_code=status.HTTP_201_CREATED)
def create_event(
    event_create: EventCreate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> Any:
    """
    Create new event. Admin only.
    """
    event_service = EventService(db)
    return event_service.create(event_create=event_create)


@router.get("/{event_id}", response_model=EventRead)
def read_event(
    event_id: int,
    db: Session = Depends(get_db),
) -> Any:
    """
    Get event by ID.
    """
    event_service = EventService(db)
    event = event_service.get(id=event_id)
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )
    
    # Only show published events to non-authenticated users
    if not event.is_published:
        # This endpoint could be accessed without authentication, so we need to check
        # for the current user manually
        try:
            # Get the current user, if any
            current_user = get_current_active_user(Depends(get_current_user))
            
            # If not an admin, raise 404
            if not current_user.is_admin:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Event not found",
                )
        except HTTPException:
            # If authentication fails, assume no valid user and hide unpublished event
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found",
            )
    
    return event


@router.put("/{event_id}", response_model=EventRead)
def update_event(
    event_id: int,
    event_update: EventUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> Any:
    """
    Update an event. Admin only.
    """
    event_service = EventService(db)
    event = event_service.get(id=event_id)
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )
    
    return event_service.update(event=event, event_update=event_update)


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(
    event_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> None:
    """
    Delete an event. Admin only.
    """
    event_service = EventService(db)
    event = event_service.get(id=event_id)
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )
    
    # Check if the event has orders
    if event_service.has_orders(event_id=event_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete an event with existing orders. Consider canceling it instead.",
        )
    
    event_service.delete(id=event_id)


@router.post("/{event_id}/publish", response_model=EventRead)
def publish_event(
    event_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> Any:
    """
    Publish an event. Admin only.
    """
    event_service = EventService(db)
    event = event_service.get(id=event_id)
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )
    
    if event.is_published:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Event is already published",
        )
    
    event_update = EventUpdate(is_published=True)
    return event_service.update(event=event, event_update=event_update)


@router.post("/{event_id}/cancel", response_model=EventRead)
def cancel_event(
    event_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> Any:
    """
    Cancel an event. Admin only.
    """
    event_service = EventService(db)
    event = event_service.get(id=event_id)
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )
    
    if event.is_canceled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Event is already canceled",
        )
    
    event_update = EventUpdate(is_canceled=True)
    updated_event = event_service.update(event=event, event_update=event_update)
    
    # Here you would typically trigger notification to all ticket holders
    # and handle refunds through a background task
    
    return updated_event

