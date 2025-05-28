import logging
from typing import List, Optional

from sqlalchemy.orm import Session

from app.core.security import get_password_hash, verify_password
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate

logger = logging.getLogger(__name__)


class UserService:
    """
    Service for user-related operations.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def get(self, id: int) -> Optional[User]:
        """
        Get a user by ID.
        """
        return self.db.query(User).filter(User.id == id).first()
    
    def get_by_email(self, email: str) -> Optional[User]:
        """
        Get a user by email.
        """
        return self.db.query(User).filter(User.email == email).first()
    
    def get_multi(self, skip: int = 0, limit: int = 100) -> List[User]:
        """
        Get multiple users with pagination.
        """
        return self.db.query(User).offset(skip).limit(limit).all()
    
    def create(self, user_create: UserCreate) -> User:
        """
        Create a new user.
        """
        # Create a new user object
        db_user = User(
            email=user_create.email,
            hashed_password=get_password_hash(user_create.password),
            first_name=user_create.first_name,
            last_name=user_create.last_name,
            is_active=user_create.is_active,
        )
        
        # Add user to database
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        
        logger.info(f"Created new user: {db_user.email}")
        return db_user
    
    def update(self, user: User, user_update: UserUpdate) -> User:
        """
        Update a user.
        """
        # Update user attributes
        update_data = user_update.dict(exclude_unset=True)
        
        # Hash password if provided
        if "password" in update_data:
            update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
        
        # Update user attributes
        for field, value in update_data.items():
            setattr(user, field, value)
        
        # Commit changes to database
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        
        logger.info(f"Updated user: {user.email}")
        return user
    
    def delete(self, id: int) -> None:
        """
        Delete a user.
        """
        user = self.get(id=id)
        if user:
            self.db.delete(user)
            self.db.commit()
            logger.info(f"Deleted user: {user.email}")
    
    def authenticate(self, email: str, password: str) -> Optional[User]:
        """
        Authenticate a user by email and password.
        """
        user = self.get_by_email(email=email)
        
        # Check if user exists and password is correct
        if not user or not verify_password(password, user.hashed_password):
            return None
        
        return user

