from sqlmodel import SQLModel, Field, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import update as sqlalchemy_update, event
from typing import Type, TypeVar, Optional, Any, List, Dict, Literal, Union
import contextlib
import os
from datetime import datetime, timezone as tz

T = TypeVar("T", bound="EasyModel")

class DatabaseConfig:
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
        if user:
            self.postgres_user = user
        if password:
            self.postgres_password = password
        if host:
            self.postgres_host = host
        if port:
            self.postgres_port = port
        if database:
            self.postgres_db = database
        self._reset_engine()

    def _reset_engine(self) -> None:
        """Reset the engine and session maker so that a new configuration takes effect."""
        DatabaseConfig._engine = None
        DatabaseConfig._session_maker = None

    def get_connection_url(self) -> str:
        """Get the connection URL based on the current configuration."""
        if self.db_type == "sqlite":
            return f"sqlite+aiosqlite:///{self.sqlite_file}"
        else:
            return (
                f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
                f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
            )

    def get_engine(self):
        """Get or create the SQLAlchemy engine."""
        if DatabaseConfig._engine is None:
            kwargs = {}
            if self.db_type == "postgresql":
                kwargs.update({
                    "pool_size": 10,
                    "max_overflow": 30,
                    "pool_timeout": 30,
                    "pool_recycle": 1800,
                    "pool_pre_ping": True,
                })
            DatabaseConfig._engine = create_async_engine(
                self.get_connection_url(),
                **kwargs
            )
        return DatabaseConfig._engine

    def get_session_maker(self):
        """Get or create the session maker."""
        if DatabaseConfig._session_maker is None:
            DatabaseConfig._session_maker = sessionmaker(
                self.get_engine(),
                class_=AsyncSession,
                expire_on_commit=False
            )
        return DatabaseConfig._session_maker

# Global database configuration instance.
db_config = DatabaseConfig()

class EasyModel(SQLModel):
    """
    Base model class providing common async database operations.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    updated_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(tz.utc))

    @classmethod
    @contextlib.asynccontextmanager
    async def get_session(cls):
        """Provide a transactional scope for database operations."""
        async with db_config.get_session_maker()() as session:
            yield session

    @classmethod
    async def get_by_id(cls: Type[T], id: int) -> Optional[T]:
        """
        Retrieve a record by its primary key.
        """
        async with cls.get_session() as session:
            return await session.get(cls, id)

    @classmethod
    async def get_by_attribute(cls: Type[T], all: bool = False, **kwargs) -> Union[Optional[T], List[T]]:
        """
        Retrieve record(s) by matching attribute values.
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
        Update an existing record by its ID.
        """
        async with cls.get_session() as session:
            # Explicitly update updated_at since bulk updates bypass ORM events.
            data["updated_at"] = datetime.now(tz.utc)
            statement = sqlalchemy_update(cls).where(cls.id == id).values(**data).execution_options(synchronize_session="fetch")
            await session.execute(statement)
            await session.commit()
            return await cls.get_by_id(id)

    @classmethod
    async def delete(cls: Type[T], id: int) -> bool:
        """
        Delete a record by its ID.
        """
        async with cls.get_session() as session:
            obj = await session.get(cls, id)
            if obj:
                await session.delete(obj)
                await session.commit()
                return True
            return False

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the model instance to a dictionary.
        """
        return self.model_dump()

# Register an event listener to update 'updated_at' on instance modifications.
@event.listens_for(AsyncSession, "before_flush")
def _update_updated_at(session, flush_context, instances):
    for instance in session.dirty:
        if isinstance(instance, EasyModel) and hasattr(instance, "updated_at"):
            instance.updated_at = datetime.now(tz.utc)

async def init_db():
    """
    Initialize the database by creating all tables defined in the SQLModel metadata.
    """
    engine = db_config.get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
