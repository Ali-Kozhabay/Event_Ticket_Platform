from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_active_user, get_current_admin_user
from app.core.database import get_db
from app.models.user import User
from app.services.ticket_service import TicketService

router = APIRouter()


@router.get("/my", response_model=Dict[str, List[Dict[str, Any]]])
def get_my_tickets(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Any:
    """
    Get all tickets for the current user.
    """
    ticket_service = TicketService(db)
    tickets = ticket_service.get_user_tickets(user_id=current_user.id)
    return {"tickets": tickets}


@router.get("/{order_id}/validate", response_model=Dict[str, Any])
def validate_ticket(
    order_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Any:
    """
    Validate a ticket's authenticity and status.
    """
    ticket_service = TicketService(db)
    
    # Verify the ticket
    verification_result = ticket_service.verify_ticket(order_id=order_id)
    
    if not verification_result["valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=verification_result["message"],
        )
    
    # Only allow ticket owner or admin to validate
    if verification_result["user_id"] != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to validate this ticket",
        )
    
    return verification_result


@router.post("/{order_id}/check-in", response_model=Dict[str, Any])
def check_in_ticket(
    order_id: int,
    current_user: User = Depends(get_current_admin_user),  # Only admins can check in tickets
    db: Session = Depends(get_db),
) -> Any:
    """
    Check in a ticket at the event (mark as used).
    """
    ticket_service = TicketService(db)
    
    # Verify the ticket first
    verification_result = ticket_service.verify_ticket(order_id=order_id)
    
    if not verification_result["valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=verification_result["message"],
        )
    
    # Check in the ticket
    check_in_result = ticket_service.check_in_ticket(order_id=order_id)
    
    if not check_in_result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=check_in_result["message"],
        )
    
    return check_in_result


@router.get("/event/{event_id}/attendees", response_model=Dict[str, List[Dict[str, Any]]])
def get_event_attendees(
    event_id: int,
    current_user: User = Depends(get_current_admin_user),  # Only admins can see attendees
    db: Session = Depends(get_db),
) -> Any:
    """
    Get all attendees for an event (for event organizers).
    """
    ticket_service = TicketService(db)
    attendees = ticket_service.get_event_attendees(event_id=event_id)
    return {"attendees": attendees}


@router.post("/{order_id}/transfer", response_model=Dict[str, Any])
def transfer_ticket(
    order_id: int,
    new_owner_email: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Any:
    """
    Transfer a ticket to another user.
    """
    # This is a simplified implementation. In a real system, you would:
    # 1. Verify the ticket belongs to the current user
    # 2. Check if the new owner exists (or create a new account)
    # 3. Transfer ownership
    # 4. Send notifications to both parties
    
    ticket_service = TicketService(db)
    
    # Verify the ticket first
    verification_result = ticket_service.verify_ticket(order_id=order_id)
    
    if not verification_result["valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=verification_result["message"],
        )
    
    # Check if the current user is the ticket owner
    if verification_result["user_id"] != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to transfer this ticket",
        )
    
    # This is a placeholder - in a real application, you would implement
    # the ticket transfer logic here.
    # For now, we'll just return a placeholder response
    
    return {
        "success": True,
        "message": "Ticket transfer feature is not implemented yet",
        "order_id": order_id,
        "original_owner": current_user.email,
        "new_owner": new_owner_email,
    }

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_active_user, get_current_admin_user
from app.core.database import get_db
from app.models.user import User
from app.services.order_service import OrderService
from app.services.ticket_service import TicketService

router = APIRouter()


@router.get("/{order_id}/verify", response_model=Dict[str, Any])
def verify_ticket(
    order_id: int,
    current_user: User = Depends(get_current_admin_user),  # Only admins can verify tickets
    db: Session = Depends(get_db),
) -> Any:
    """
    Verify ticket validity (for event staff).
    Returns information about the ticket and its validity.
    """
    # Initialize services
    ticket_service = TicketService(db)
    
    # Verify the ticket
    verification_result = ticket_service.verify_ticket(order_id=order_id)
    
    if not verification_result["valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=verification_result["message"],
        )
    
    return verification_result


@router.post("/{order_id}/check-in", response_model=Dict[str, Any])
def check_in_ticket(
    order_id: int,
    current_user: User = Depends(get_current_admin_user),  # Only admins can check in tickets
    db: Session = Depends(get_db),
) -> Any:
    """
    Check in a ticket (mark as used).
    """
    # Initialize services
    ticket_service = TicketService(db)
    
    # Verify the ticket first
    verification_result = ticket_service.verify_ticket(order_id=order_id)
    
    if not verification_result["valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=verification_result["message"],
        )
    
    # Check in the ticket
    check_in_result = ticket_service.check_in_ticket(order_id=order_id)
    
    if not check_in_result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=check_in_result["message"],
        )
    
    return check_in_result


@router.get("/my-tickets", response_model=Dict[str, Any])
def get_user_tickets(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Any:
    """
    Get all tickets for the current user.
    """
    # Initialize services
    ticket_service = TicketService(db)
    
    # Get user's tickets
    return {
        "tickets": ticket_service.get_user_tickets(user_id=current_user.id)
    }


@router.get("/event/{event_id}/attendees", response_model=Dict[str, Any])
def get_event_attendees(
    event_id: int,
    current_user: User = Depends(get_current_admin_user),  # Only admins can see attendees
    db: Session = Depends(get_db),
) -> Any:
    """
    Get all attendees for an event.
    """
    # Initialize services
    ticket_service = TicketService(db)
    
    # Get event attendees
    return {
        "attendees": ticket_service.get_event_attendees(event_id=event_id)
    }

