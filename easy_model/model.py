from sqlmodel import SQLModel, Field, select, metadata
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base, event
from typing import Type, TypeVar, Optional, Any, List, Dict
from sqlalchemy import update as sqlalchemy_update
import contextlib
import os
from datetime import datetime

# Define a TypeVar for the model class
T = TypeVar("T", bound="EasyModel")

# Add event listener for automatic updated_at
@event.listens_for(AsyncSession, "before_flush")
def _update_updated_at(session, flush_context, instances):
    """Automatically update 'updated_at' field for any model that has it."""
    for instance in session.dirty:
        if isinstance(instance, EasyModel) and hasattr(instance, 'updated_at'):
            instance.updated_at = datetime.utcnow()

# DATABASE SETUP & CONFIGURATION
def get_database_url() -> str:
    """Get database URL from environment variables with fallback to default values."""
    user = os.getenv('POSTGRES_USER', 'postgres')
    password = os.getenv('POSTGRES_PASSWORD', 'postgres')
    host = os.getenv('POSTGRES_HOST', 'localhost')
    port = os.getenv('POSTGRES_PORT', '5432')
    db = os.getenv('POSTGRES_DB', 'postgres')
    
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"

# Creating async engine and session with SQLModel
async_engine = create_async_engine(
    get_database_url(),
    pool_size=10,
    max_overflow=30,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True
)

AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def init_db():
    """Initialize the database by creating all declared tables."""
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

class EasyModel(SQLModel):
    """
    Base model class providing common async database operations.
    
    This class extends SQLModel to provide convenient async methods for
    common database operations like create, read, update, and delete.
    """
    
    id: Optional[int] = Field(default=None, primary_key=True)
    updated_at: Optional[datetime] = Field(default=None)
    
    @classmethod
    @contextlib.asynccontextmanager
    async def get_session(cls):
        """Provide a transactional scope around a series of operations."""
        async with AsyncSessionLocal() as session:
            yield session

    @classmethod
    async def get_by_id(cls: Type[T], id: int) -> Optional[T]:
        """
        Retrieve a record by its ID.
        
        Args:
            id: The primary key ID of the record to retrieve.
            
        Returns:
            The record if found, None otherwise.
        """
        async with cls.get_session() as session:
            return await session.get(cls, id)

    @classmethod
    async def get_by_attribute(cls: Type[T], all: bool = False, **kwargs) -> Optional[T]:
        """
        Retrieve record(s) by attribute values.
        
        Args:
            all: If True, returns all matching records. If False, returns only the first match.
            **kwargs: Attribute name-value pairs to filter by.
            
        Returns:
            A single record or list of records depending on the 'all' parameter.
        """
        async with cls.get_session() as session:
            statement = select(cls).filter_by(**kwargs)
            result = await session.execute(statement)
            if all:
                return result.scalars().all()
            return result.scalars().first()

    @classmethod
    async def insert(cls: Type[T], data: Dict[str, Any]) -> T:
        """
        Insert a new record.
        
        Args:
            data: Dictionary of attribute name-value pairs for the new record.
            
        Returns:
            The newly created record.
        """
        async with cls.get_session() as session:
            obj = cls(**data)
            session.add(obj)
            await session.commit()
            await session.refresh(obj)
            return obj

    @classmethod
    async def update(cls: Type[T], id: int, data: Dict[str, Any]) -> Optional[T]:
        """
        Update an existing record by ID.
        
        Args:
            id: The primary key ID of the record to update.
            data: Dictionary of attribute name-value pairs to update.
            
        Returns:
            The updated record if found, None otherwise.
        """
        async with cls.get_session() as session:
            statement = sqlalchemy_update(cls).where(cls.id == id).values(**data).execution_options(synchronize_session="fetch")
            await session.execute(statement)
            await session.commit()
            return await cls.get_by_id(id)

    @classmethod
    async def delete(cls: Type[T], id: int) -> bool:
        """
        Delete a record by ID.
        
        Args:
            id: The primary key ID of the record to delete.
            
        Returns:
            True if the record was deleted, False if not found.
        """
        async with cls.get_session() as session:
            obj = await cls.get_by_id(id)
            if obj:
                await session.delete(obj)
                await session.commit()
                return True
            return False

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the model instance to a dictionary.
        
        Returns:
            Dictionary representation of the model.
        """
        return self.model_dump()
