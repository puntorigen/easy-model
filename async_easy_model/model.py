from sqlmodel import SQLModel, Field, select, metadata
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base, event
from typing import Type, TypeVar, Optional, Any, List, Dict, Literal
from sqlalchemy import update as sqlalchemy_update
import contextlib
import os
from datetime import datetime
from pathlib import Path

# Define a TypeVar for the model class
T = TypeVar("T", bound="EasyModel")

# Add event listener for automatic updated_at
@event.listens_for(AsyncSession, "before_flush")
def _update_updated_at(session, flush_context, instances):
    """Automatically update 'updated_at' field for any model that has it."""
    for instance in session.dirty:
        if isinstance(instance, EasyModel) and hasattr(instance, 'updated_at'):
            instance.updated_at = datetime.utcnow()

class DatabaseConfig:
    """Configuration for database connection."""
    _instance = None
    _engine = None
    _session_maker = None

    def __init__(self):
        self.db_type: Literal["postgresql", "sqlite"] = "postgresql"
        self.postgres_user: str = os.getenv('POSTGRES_USER', 'postgres')
        self.postgres_password: str = os.getenv('POSTGRES_PASSWORD', 'postgres')
        self.postgres_host: str = os.getenv('POSTGRES_HOST', 'localhost')
        self.postgres_port: str = os.getenv('POSTGRES_PORT', '5432')
        self.postgres_db: str = os.getenv('POSTGRES_DB', 'postgres')
        self.sqlite_file: str = os.getenv('SQLITE_FILE', 'database.db')

    @classmethod
    def get_instance(cls) -> 'DatabaseConfig':
        """Get singleton instance of DatabaseConfig."""
        if cls._instance is None:
            cls._instance = DatabaseConfig()
        return cls._instance

    def configure_sqlite(self, db_file: str) -> None:
        """Configure SQLite database."""
        self.db_type = "sqlite"
        self.sqlite_file = db_file
        self._reset_engine()

    def configure_postgres(
        self,
        user: str = None,
        password: str = None,
        host: str = None,
        port: str = None,
        database: str = None
    ) -> None:
        """Configure PostgreSQL database."""
        self.db_type = "postgresql"
        if user: self.postgres_user = user
        if password: self.postgres_password = password
        if host: self.postgres_host = host
        if port: self.postgres_port = port
        if database: self.postgres_db = database
        self._reset_engine()

    def _reset_engine(self) -> None:
        """Reset engine and session maker."""
        DatabaseConfig._engine = None
        DatabaseConfig._session_maker = None

    def get_connection_url(self) -> str:
        """Get database connection URL based on configuration."""
        if self.db_type == "sqlite":
            return f"sqlite+aiosqlite:///{self.sqlite_file}"
        else:
            return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    def get_engine(self):
        """Get or create SQLAlchemy engine."""
        if DatabaseConfig._engine is None:
            DatabaseConfig._engine = create_async_engine(
                self.get_connection_url(),
                pool_size=10 if self.db_type == "postgresql" else None,
                max_overflow=30 if self.db_type == "postgresql" else None,
                pool_timeout=30 if self.db_type == "postgresql" else None,
                pool_recycle=1800 if self.db_type == "postgresql" else None,
                pool_pre_ping=True,
            )
        return DatabaseConfig._engine

    def get_session_maker(self):
        """Get or create session maker."""
        if DatabaseConfig._session_maker is None:
            DatabaseConfig._session_maker = sessionmaker(
                bind=self.get_engine(),
                class_=AsyncSession,
                expire_on_commit=False
            )
        return DatabaseConfig._session_maker

# Create default instance
db_config = DatabaseConfig.get_instance()

async def init_db():
    """Initialize the database by creating all declared tables."""
    async with db_config.get_engine().begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

class EasyModel(SQLModel):
    """
    Base model class providing common async database operations.
    """
    
    id: Optional[int] = Field(default=None, primary_key=True)
    updated_at: Optional[datetime] = Field(default=None)
    
    @classmethod
    @contextlib.asynccontextmanager
    async def get_session(cls):
        """Provide a transactional scope around a series of operations."""
        async with db_config.get_session_maker()() as session:
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
