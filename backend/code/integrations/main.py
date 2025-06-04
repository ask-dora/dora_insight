import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel

from ..database import get_db_session
from ..models import User, UserIntegration

# Initialize router
router = APIRouter(prefix="/api/integrations", tags=["integrations"])

# Import routers from specific integrations
# These will be imported here and included in the main router

# Temporary storage for OAuth state (in production, use Redis or database)
oauth_states: Dict[str, Dict[str, Any]] = {}

# --- Base Pydantic Models ---
class IntegrationBase(BaseModel):
    integration_type: str
    is_connected: bool
    connected_at: Optional[datetime] = None
    integration_username: Optional[str] = None

class IntegrationStatus(BaseModel):
    integrations: list[IntegrationBase]

# --- Helper Functions ---
async def get_user_by_firebase_uid(db: AsyncSession, user_identifier: str) -> Optional[User]:
    """Get user by Firebase UID"""
    result = await db.execute(select(User).where(User.user_identifier == user_identifier))
    return result.scalar_one_or_none()

async def get_user_integration(db: AsyncSession, user_id: int, integration_type: str) -> Optional[UserIntegration]:
    """Get user's integration by type"""
    result = await db.execute(
        select(UserIntegration).where(
            UserIntegration.user_id == user_id,
            UserIntegration.integration_type == integration_type
        )
    )
    return result.scalar_one_or_none()

# --- API Endpoints ---
@router.get("/status", response_model=IntegrationStatus)
async def get_integration_status(
    user_identifier: str = Header(..., alias="X-User-ID"),
    db: AsyncSession = Depends(get_db_session)
):
    """Get the status of all integrations for the current user"""
    print(f"Getting integration status for user: {user_identifier}")
    user = await get_user_by_firebase_uid(db, user_identifier)
    if not user:
        # Create user if they don't exist
        print(f"Creating new user with Firebase UID: {user_identifier}")
        user = User(user_identifier=user_identifier)
        db.add(user)
        await db.commit()
        await db.refresh(user)
        print(f"Created user with ID: {user.id}")
    
    print(f"Found user: {user.id}")
    
    # Get all user integrations from database
    result = await db.execute(
        select(UserIntegration).where(
            UserIntegration.user_id == user.id,
            UserIntegration.is_active == True
        )
    )
    user_integrations = result.scalars().all()
    print(f"Found {len(user_integrations)} active integrations in DB")
    
    # List of available integrations
    # In the future, this could be dynamic based on what integration modules are loaded
    available_integrations = ["github"]
    integrations = []
    
    # Import integration status checking functions dynamically
    from .github import check_github_connection_status
    
    for integration_type in available_integrations:
        if integration_type == "github":
            # Check GitHub connection status
            github_status = await check_github_connection_status(user_identifier)
            integrations.append(github_status)
        else:
            # For other integrations, fall back to database check
            db_integration = next((i for i in user_integrations if i.integration_type == integration_type), None)
            if db_integration:
                integrations.append(IntegrationBase(
                    integration_type=integration_type,
                    is_connected=True,
                    connected_at=db_integration.connected_at,
                    integration_username=db_integration.integration_username
                ))
            else:
                integrations.append(IntegrationBase(
                    integration_type=integration_type,
                    is_connected=False
                ))
    
    return IntegrationStatus(integrations=integrations)

# Clean up expired OAuth states (call this periodically)
async def cleanup_oauth_states():
    """Clean up expired OAuth states"""
    current_time = datetime.utcnow()
    expired_states = [
        state for state, data in oauth_states.items()
        if current_time - data["created_at"] > timedelta(minutes=10)
    ]
    for state in expired_states:
        del oauth_states[state]
