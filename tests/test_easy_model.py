import pytest
import os
from sqlmodel import Field, select
from datetime import datetime
from async_easy_model import EasyModel, init_db, db_config
import asyncio
import tempfile
from pathlib import Path
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

# Configure SQLite for testing using a temporary directory.
@pytest.fixture(autouse=True)
def setup_test_db():
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "test.db"
        db_config.configure_sqlite(str(db_path))
        yield
        # Cleanup is automatically handled by TemporaryDirectory

# Define a test model.
class TestUser(EasyModel, table=True):
    username: str = Field(unique=True)
    email: str

@pytest.mark.asyncio
async def test_init_db():
    # Test that initializing the database doesn't raise an exception.
    await init_db()

@pytest.mark.asyncio
async def test_crud_operations():
    await init_db()
    
    # Test data for insertion.
    test_data = {
        "username": "test_user",
        "email": "test@example.com"
    }
    
    # --- Insert ---
    user = await TestUser.insert(test_data)
    assert user.username == test_data["username"]
    assert user.email == test_data["email"]
    assert user.created_at is not None
    assert user.updated_at is not None
    # created_at and updated_at should be very close at creation time
    time_diff = abs((user.created_at - user.updated_at).total_seconds())
    assert time_diff < 0.1  # Allow for a small difference
    
    # --- Get by ID ---
    retrieved_user = await TestUser.get_by_id(user.id)
    assert retrieved_user is not None
    assert retrieved_user.username == test_data["username"]
    
    # --- Get by Attribute (single result) ---
    found_user = await TestUser.get_by_attribute(username=test_data["username"])
    assert found_user is not None
    assert found_user.id == user.id

    # --- Update ---
    original_updated_at = found_user.updated_at
    original_created_at = found_user.created_at
    # Wait briefly to ensure a time difference.
    await asyncio.sleep(0.1)
    updated_email = "updated@example.com"
    updated_user = await TestUser.update(user.id, {"email": updated_email})
    assert updated_user is not None
    assert updated_user.email == updated_email
    # Confirm that updated_at has been changed.
    assert updated_user.updated_at is not None
    assert updated_user.updated_at > original_updated_at
    # Confirm that created_at has NOT been changed.
    assert updated_user.created_at is not None
    assert updated_user.created_at == original_created_at
    
    # --- Delete ---
    success = await TestUser.delete(user.id)
    assert success is True
    # Confirm that deletion was successful.
    deleted_user = await TestUser.get_by_id(user.id)
    assert deleted_user is None

@pytest.mark.asyncio
async def test_unique_constraint():
    # Test that a duplicate username violates the unique constraint.
    await init_db()
    
    data = {"username": "duplicate_user", "email": "first@example.com"}
    await TestUser.insert(data)
    
    with pytest.raises(IntegrityError):
        # Attempting to insert another record with the same username should raise an error.
        await TestUser.insert(data)

@pytest.mark.asyncio
async def test_get_by_attribute_nonexistent():
    # Verify that querying for a non-existent record returns None.
    await init_db()
    result = await TestUser.get_by_attribute(username="nonexistent")
    assert result is None

@pytest.mark.asyncio
async def test_get_by_attribute_all():
    # Test that get_by_attribute returns all matching records when 'all=True'.
    await init_db()
    
    users_data = [
        {"username": "user1", "email": "common@example.com"},
        {"username": "user2", "email": "common@example.com"},
    ]
    
    for data in users_data:
        await TestUser.insert(data)
    
    # Use the 'all' flag to get all users with the same email.
    found_users = await TestUser.get_by_attribute(all=True, email="common@example.com")
    assert isinstance(found_users, list)
    assert len(found_users) == 2

@pytest.mark.asyncio
async def test_raw_sqlite_connection():
    """
    Test raw SQLite connectivity using the engine from db_config.
    This ensures that the async engine can execute basic SQL commands.
    """
    engine = db_config.get_engine()
    async with engine.connect() as conn:
        # Create a simple table.
        await conn.execute(text("CREATE TABLE IF NOT EXISTS raw_test (id INTEGER PRIMARY KEY, data TEXT)"))
        await conn.execute(text("INSERT INTO raw_test (data) VALUES ('sqlite_test')"))
        await conn.commit()
        result = await conn.execute(text("SELECT data FROM raw_test WHERE id = 1"))
        data = result.scalar_one()
        assert data == "sqlite_test"
