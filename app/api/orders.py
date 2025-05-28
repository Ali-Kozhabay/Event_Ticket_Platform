from typing import Any, Dict, List,Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_active_user, get_current_admin_user
from app.core.database import get_db
from app.models.order import OrderStatus
from app.models.user import User
from app.schemas.order import OrderCreate, OrderRead, OrderUpdate, PaymentProcess, PaymentResponse
from app.services.event_service import EventService
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService
from app.services.notification_service import NotificationService

router = APIRouter()


@router.get("", response_model=List[OrderRead])
def read_orders(
    skip: int = 0,
    limit: int = 100,
    status: Optional[OrderStatus] = Query(None, description="Filter by order status"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Any:
    """
    Retrieve user's orders with optional filtering.
    """
    order_service = OrderService(db)
    return order_service.get_user_orders(
        user_id=current_user.id, skip=skip, limit=limit, status=status
    )


@router.post("", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
def create_order(
    order_create: OrderCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Any:
    """
    Create a new order.
    """
    # Initialize services
    order_service = OrderService(db)
    event_service = EventService(db)
    notification_service = NotificationService()
    
    # Check if the event exists and is published
    event = event_service.get(id=order_create.event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )
    
    if not event.is_published:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot order tickets for unpublished events",
        )
    
    if event.is_canceled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot order tickets for canceled events",
        )
    
    # Check if there are enough tickets available
    if event.available_tickets < order_create.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Not enough tickets available. Only {event.available_tickets} left.",
        )
    
    try:
        # Create the order (this will reserve the tickets)
        order = order_service.create(
            user_id=current_user.id,
            event_id=order_create.event_id,
            quantity=order_create.quantity,
            payment_method=order_create.payment_method,
            unit_price=event.ticket_price,
        )
        
        # Send order confirmation email in the background
        background_tasks.add_task(
            notification_service.send_order_confirmation,
            order_id=order.id,
            user_email=current_user.email,
        )
        
        return order
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/{order_id}", response_model=OrderRead)
def read_order(
    order_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Any:
    """
    Get order by ID.
    """
    order_service = OrderService(db)
    order = order_service.get(id=order_id)
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )
    
    # Ensure user can only access their own orders
    if order.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to access this order",
        )
    
    return order_service.get_order_with_event_details(order_id=order_id)


@router.put("/{order_id}", response_model=OrderRead)
def update_order(
    order_id: int,
    order_update: OrderUpdate,
    current_user: User = Depends(get_current_admin_user),  # Only admins can update orders
    db: Session = Depends(get_db),
) -> Any:
    """
    Update an order (admin only).
    """
    order_service = OrderService(db)
    order = order_service.get(id=order_id)
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )
    
    # Update the order status
    if order_update.status is not None:
        order = order_service.update_status(
            order_id=order_id,
            status=order_update.status,
            payment_id=order_update.payment_id,
        )
    
    return order_service.get_order_with_event_details(order_id=order_id)


@router.post("/{order_id}/process-payment", response_model=PaymentResponse)
def process_payment(
    order_id: int,
    payment_data: PaymentProcess,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Any:
    """
    Process payment for an order.
    """
    # Initialize services
    order_service = OrderService(db)
    payment_service = PaymentService()
    notification_service = NotificationService()
    
    # Get the order
    order = order_service.get(id=order_id)
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )
    
    # Ensure user can only process their own orders
    if order.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to process this order",
        )
    
    # Check if order is already paid
    if order.status == OrderStatus.PAID:
        return PaymentResponse(
            order_id=order.id,
            status=order.status,
            payment_id=order.payment_id,
            message="Order is already paid",
        )
    
    # Check if order is canceled
    if order.status == OrderStatus.CANCELED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot process payment for a canceled order",
        )
    
    # Process payment
    payment_result = payment_service.process_payment(
        amount=order.total_amount,
        payment_method=payment_data.payment_method,
        payment_details={
            "card_number": payment_data.card_number,
            "card_exp_month": payment_data.card_exp_month,
            "card_exp_year": payment_data.card_exp_year,
            "card_cvc": payment_data.card_cvc,
        },
    )
    
    # Update order with payment result
    if payment_result["success"]:
        # Update order status to paid
        order_service.update_status(
            order_id=order.id,
            status=OrderStatus.PAID,
            payment_id=payment_result["payment_id"],
        )
        
        # Send confirmation email in the background
        background_tasks.add_task(
            notification_service.send_order_confirmation,
            order_id=order.id,
            user_email=current_user.email,
        )
        
        return PaymentResponse(
            order_id=order.id,
            status=OrderStatus.PAID,
            payment_id=payment_result["payment_id"],
            message="Payment successful",
        )
    else:
        return PaymentResponse(
            order_id=order.id,
            status=order.status,
            message=f"Payment failed: {payment_result.get('error', 'Unknown error')}",
        )


@router.post("/{order_id}/cancel", response_model=OrderRead)
def cancel_order(
    order_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Any:
    """
    Cancel an order.
    """
    # Initialize services
    order_service = OrderService(db)
    event_service = EventService(db)
    notification_service = NotificationService()
    
    # Get the order
    order = order_service.get(id=order_id)
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )
    
    # Ensure user can only cancel their own orders (or admin)
    if order.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to cancel this order",
        )
    
    # Check if order can be canceled
    if order.status == OrderStatus.CANCELED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order is already canceled",
        )
    
    # If order is paid, initiate refund (in a real system)
    refund_id = None
    if order.status == OrderStatus.PAID:
        # In a real system, you would process the refund through the payment gateway
        # and get a refund ID
        refund_id = "refund_123"  # Placeholder
    
    # Cancel the order
    updated_order = order_service.cancel_order(order_id=order.id, refund_id=refund_id)
    
    # Release the tickets back to the event
    event_service.increase_available_tickets(
        event_id=order.event_id, quantity=order.quantity
    )
    
    # Send cancellation email in the background
    background_tasks.add_task(
        notification_service.send_order_cancellation,
        order_id=order.id,
        user_email=current_user.email,
    )
    
    return order_service.get_order_with_event_details(order_id=order_id)


@router.get("/admin/all", response_model=List[OrderRead])
def read_all_orders(
    skip: int = 0,
    limit: int = 100,
    status: Optional[OrderStatus] = Query(None, description="Filter by order status"),
    current_user: User = Depends(get_current_admin_user),  # Only admins can access all orders
    db: Session = Depends(get_db),
) -> Any:
    """
    Retrieve all orders (admin only).
    """
    order_service = OrderService(db)
    
    # Get all orders
    orders = []
    db_orders = order_service.get_all_orders(skip=skip, limit=limit, status=status)
    
    # Get order details
    for order in db_orders:
        order_read = order_service.get_order_with_event_details(order_id=order.id)
        if order_read:
            orders.append(order_read)
    
    return orders

from typing import Any, List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_active_user
from app.core.database import get_db
from app.models.order import OrderStatus
from app.models.user import User
from app.schemas.order import OrderCreate, OrderRead, PaymentProcess, PaymentResponse
from app.services.event_service import EventService
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService
from app.services.notification_service import NotificationService

router = APIRouter()


@router.get("", response_model=List[OrderRead])
def read_orders(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Any:
    """
    Retrieve user's orders.
    """
    order_service = OrderService(db)
    return order_service.get_user_orders(user_id=current_user.id, skip=skip, limit=limit)


@router.post("", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
def create_order(
    order_create: OrderCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Any:
    """
    Create a new order.
    """
    # Initialize services
    order_service = OrderService(db)
    event_service = EventService(db)
    
    # Check if the event exists and is published
    event = event_service.get(id=order_create.event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )
    
    if not event.is_published:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot order tickets for unpublished events",
        )
    
    if event.is_canceled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot order tickets for canceled events",
        )
    
    # Check if there are enough tickets available
    if event.available_tickets < order_create.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Not enough tickets available. Only {event.available_tickets} left.",
        )
    
    # Create the order (this will reserve the tickets)
    return order_service.create(
        user_id=current_user.id,
        event_id=order_create.event_id,
        quantity=order_create.quantity,
        payment_method=order_create.payment_method,
        unit_price=event.ticket_price,
    )


@router.get("/{order_id}", response_model=OrderRead)
def read_order(
    order_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Any:
    """
    Get order by ID.
    """
    order_service = OrderService(db)
    order = order_service.get(id=order_id)
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )
    
    # Ensure user can only access their own orders
    if order.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to access this order",
        )
    
    return order


@router.post("/{order_id}/process-payment", response_model=PaymentResponse)
def process_payment(
    order_id: int,
    payment_data: PaymentProcess,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Any:
    """
    Process payment for an order.
    """
    # Initialize services
    order_service = OrderService(db)
    payment_service = PaymentService()
    notification_service = NotificationService()
    
    # Get the order
    order = order_service.get(id=order_id)
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )
    
    # Ensure user can only process their own orders
    if order.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to process this order",
        )
    
    # Check if order is already paid
    if order.status == OrderStatus.PAID:
        return PaymentResponse(
            order_id=order.id,
            status=order.status,
            payment_id=order.payment_id,
            message="Order is already paid",
        )
    
    # Check if order is canceled
    if order.status == OrderStatus.CANCELED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot process payment for a canceled order",
        )
    
    # Process payment
    payment_result = payment_service.process_payment(
        amount=order.total_amount,
        payment_method=payment_data.payment_method,
        payment_details={
            "card_number": payment_data.card_number,
            "card_exp_month": payment_data.card_exp_month,
            "card_exp_year": payment_data.card_exp_year,
            "card_cvc": payment_data.card_cvc,
        },
    )
    
    # Update order with payment result
    if payment_result["success"]:
        # Update order status to paid
        order_service.update_status(
            order_id=order.id,
            status=OrderStatus.PAID,
            payment_id=payment_result["payment_id"],
        )
        
        # Send confirmation email in the background
        background_tasks.add_task(
            notification_service.send_order_confirmation,
            order_id=order.id,
            user_email=current_user.email,
        )
        
        return PaymentResponse(
            order_id=order.id,
            status=OrderStatus.PAID,
            payment_id=payment_result["payment_id"],
            message="Payment successful",
        )
    else:
        return PaymentResponse(
            order_id=order.id,
            status=order.status,
            message=f"Payment failed: {payment_result['error']}",
        )


@router.post("/{order_id}/cancel", response_model=OrderRead)
def cancel_order(
    order_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Any:
    """
    Cancel an order.
    """
    # Initialize services
    order_service = OrderService(db)
    event_service = EventService(db)
    notification_service = NotificationService()
    
    # Get the order
    order = order_service.get(id=order_id)
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )
    
    # Ensure user can only cancel their own orders
    if order.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to cancel this order",
        )
    
    # Check if order can be canceled
    if order.status == OrderStatus.CANCELED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order is already canceled",
        )
    
    # If order is paid, initiate refund (in a real system)
    refund_id = None
    if order.status == OrderStatus.PAID:
        # In a real system, you would process the refund through the payment gateway
        # and get a refund ID
        refund_id = "refund_123"  # Placeholder
    
    # Cancel the order
    updated_order = order_service.cancel_order(order_id=order.id, refund_id=refund_id)
    
    # Release the tickets back to the event
    event_service.increase_available_tickets(
        event_id=order.event_id, quantity=order.quantity
    )
    
    # Send cancellation email in the background
    background_tasks.add_task(
        notification_service.send_order_cancellation,
        order_id=order.id,
        user_email=current_user.email,
    )
    
    return updated_order

