import pytest
import os
from sqlmodel import Field
from datetime import datetime
from easy_model import EasyModel, init_db
import asyncio

# Test model
class TestUser(EasyModel, table=True):
    username: str = Field(unique=True)
    email: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default=None)

@pytest.mark.asyncio
async def test_init_db():
    # Initialize database
    await init_db()
    # If no exception is raised, the test passes

@pytest.mark.asyncio
async def test_crud_operations():
    # Test data
    test_data = {
        "username": "test_user",
        "email": "test@example.com"
    }
    
    # Test insert
    user = await TestUser.insert(test_data)
    assert user.username == test_data["username"]
    assert user.email == test_data["email"]
    
    # Test get by id
    retrieved_user = await TestUser.get_by_id(user.id)
    assert retrieved_user is not None
    assert retrieved_user.username == test_data["username"]
    
    # Test get by attribute
    found_user = await TestUser.get_by_attribute(username=test_data["username"])
    assert found_user is not None
    assert found_user.id == user.id

    # Store the current updated_at
    original_updated_at = found_user.updated_at
    
    # Wait a bit to ensure updated_at will be different
    await asyncio.sleep(0.1)
    
    # Test update
    updated_email = "updated@example.com"
    updated_user = await TestUser.update(user.id, {"email": updated_email})
    assert updated_user is not None
    assert updated_user.email == updated_email
    # Verify updated_at was changed
    assert updated_user.updated_at is not None
    assert updated_user.updated_at > original_updated_at
    
    # Test delete
    success = await TestUser.delete(user.id)
    assert success is True
    
    # Verify deletion
    deleted_user = await TestUser.get_by_id(user.id)
    assert deleted_user is None
