# Event Ticket Platform

A FastAPI-based platform for event ticket management with features for event creation, ticket purchasing, and payment processing.

## Features

- User authentication and management
- Event creation and management
- Ticket purchasing
- Payment processing (mock implementation)
- Email notifications (mock implementation)
- Background tasks for email and payment processing

## Tech Stack

- **FastAPI**: High-performance web framework
- **SQLAlchemy**: ORM for database interactions
- **Pydantic**: Data validation and settings management
- **PostgreSQL**: Database (can be replaced with other SQL databases)
- **JWT**: Token-based authentication
- **Celery** (optional): For background task processing

## Prerequisites

- Python 3.9+
- PostgreSQL
- Redis (optional, for Celery)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/Ali-Kozhabay/Event_Ticket_Platform.git
   cd event_ticket_platform
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file from the example:
   ```bash
   cp .env.example .env
   ```
   Then edit the `.env` file to set your configuration values.

5. Create the database:
   ```bash
   # In PostgreSQL
   createdb event_ticket_db
   ```

## Running the Application

1. Run database migrations (first time setup):
   ```bash
   # TODO: Add Alembic migration commands
   ```

2. Start the application:
   ```bash
   uvicorn app.main:app --reload
   ```

3. Access the API documentation:
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

## API Endpoints

The API is organized into several modules:

- **Authentication**: `/api/auth`
  - Register: `POST /api/auth/register`
  - Login: `POST /api/auth/login`

- **Users**: `/api/users`
  - Get current user: `GET /api/users/me`
  - Update current user: `PUT /api/users/me`
  - Admin user management: Various endpoints

- **Events**: `/api/events`
  - List events: `GET /api/events`
  - Create event: `POST /api/events`
  - Get event details: `GET /api/events/{event_id}`
  - Update event: `PUT /api/events/{event_id}`
  - Delete event: `DELETE /api/events/{event_id}`

- **Orders**: `/api/orders`
  - Create order: `POST /api/orders`
  - Get user orders: `GET /api/orders`
  - Get order details: `GET /api/orders/{order_id}`
  - Process payment: `POST /api/orders/{order_id}/process-payment`
  - Cancel order: `POST /api/orders/{order_id}/cancel`

- **Tickets**: `/api/tickets`
  - Get user tickets: `GET /api/tickets/my`
  - Validate ticket: `GET /api/tickets/{order_id}/validate`
  - Check-in ticket: `POST /api/tickets/{order_id}/check-in`

## Project Structure

```
app/
├── __init__.py
├── main.py
├── core/
│   ├── config.py
│   ├── security.py
│   └── database.py
├── models/
│   ├── user.py
│   ├── event.py
│   └── order.py
├── schemas/
│   ├── user.py
│   ├── event.py
│   └── order.py
├── api/
│   ├── auth.py
│   ├── users.py
│   ├── events.py
│   ├── tickets.py
│   └── orders.py
├── services/
│   ├── user_service.py
│   ├── event_service.py
│   ├── order_service.py
│   ├── ticket_service.py
│   ├── payment_service.py
│   └── notification_service.py
└── tasks/
    ├── email_tasks.py
    └── payment_tasks.py
```

## Development

### Adding New Endpoints

1. Create a new router in the `app/api` directory
2. Implement the necessary service methods in the `app/services` directory
3. Register the router in `app/main.py`

### Database Migrations

TODO: Add instructions for using Alembic for database migrations

## Testing

Run tests using pytest:

```bash
pytest
```

## Deployment

This application can be deployed using various methods:

- Docker
- Traditional deployment on a server
- Cloud platforms (AWS, Google Cloud, Azure)

For Docker deployment, a Dockerfile is provided in the repository.

## License

[MIT License](LICENSE)

