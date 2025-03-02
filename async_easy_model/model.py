from sqlmodel import SQLModel, Field, select, Relationship
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, Session, selectinload, joinedload
from sqlalchemy import update as sqlalchemy_update, event, desc, asc
from typing import Type, TypeVar, Optional, Any, List, Dict, Literal, Union, Set, Tuple
import contextlib
import os
from datetime import datetime, timezone as tz
import inspect
import json
import logging

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
    created_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(tz.utc))
    updated_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(tz.utc))

    @classmethod
    @contextlib.asynccontextmanager
    async def get_session(cls):
        """Provide a transactional scope for database operations."""
        async with db_config.get_session_maker()() as session:
            yield session

    @classmethod
    def _get_relationship_fields(cls) -> List[str]:
        """
        Get all relationship fields defined in the model.
        
        This method looks at the model's metadata to find relationship fields.
        
        Returns:
            List[str]: A list of field names that are relationships.
        """
        relationship_fields = []
        
        # For manually defined relationships
        if hasattr(cls, "__sqlmodel_relationships__"):
            for rel_name, rel_info in cls.__sqlmodel_relationships__.items():
                # Get the actual relationship attribute, not just the metadata
                rel_attr = getattr(cls, rel_name, None)
                # Only include it if it's a real SQLAlchemy relationship
                if rel_attr is not None and hasattr(rel_attr, "prop") and hasattr(rel_attr.prop, "mapper"):
                    relationship_fields.append(rel_name)
                # For "auto" relationships we need to check differently
                elif rel_attr is not None and isinstance(rel_attr, Relationship):
                    relationship_fields.append(rel_name)
        
        return relationship_fields
    
    @classmethod
    def _get_auto_relationship_fields(cls) -> List[str]:
        """
        Get all automatically detected relationship fields from class attributes.
        This is needed because auto-relationships may not be in __sqlmodel_relationships__ 
        until they are properly registered.
        """
        # First check normal relationships
        relationship_fields = cls._get_relationship_fields()
        
        # Then check for any relationship attributes created by our auto-relationship system
        for attr_name in dir(cls):
            if attr_name.startswith('__') or attr_name in relationship_fields:
                continue
                
            attr_value = getattr(cls, attr_name)
            if hasattr(attr_value, 'back_populates'):
                relationship_fields.append(attr_name)
                
        return relationship_fields

    @classmethod
    def _apply_order_by(cls, statement, order_by: Optional[Union[str, List[str]]] = None):
        """
        Apply ordering to a select statement.
        
        Args:
            statement: The select statement to apply ordering to
            order_by: Field(s) to order by. Can be a string or list of strings.
                      Prefix with '-' for descending order (e.g. '-created_at')
                      
        Returns:
            The statement with ordering applied
        """
        if not order_by:
            return statement
            
        # Convert single string to list
        if isinstance(order_by, str):
            order_by = [order_by]
            
        for field_name in order_by:
            descending = False
            
            # Check if descending order is requested
            if field_name.startswith('-'):
                descending = True
                field_name = field_name[1:]
                
            # Handle relationship fields (e.g. 'author.name')
            if '.' in field_name:
                rel_name, attr_name = field_name.split('.', 1)
                if hasattr(cls, rel_name) and rel_name in cls._get_relationship_fields():
                    rel_class = getattr(cls, rel_name).prop.mapper.class_
                    if hasattr(rel_class, attr_name):
                        order_attr = getattr(rel_class, attr_name)
                        statement = statement.join(rel_class)
                        statement = statement.order_by(desc(order_attr) if descending else asc(order_attr))
            # Handle regular fields
            elif hasattr(cls, field_name):
                order_attr = getattr(cls, field_name)
                statement = statement.order_by(desc(order_attr) if descending else asc(order_attr))
                
        return statement

    @classmethod
    async def all(
        cls: Type[T], 
        include_relationships: bool = False,
        order_by: Optional[Union[str, List[str]]] = None
    ) -> List[T]:
        """
        Retrieve all records of this model.
        
        Args:
            include_relationships: If True, eagerly load all relationships
            order_by: Field(s) to order by. Can be a string or list of strings.
                      Prefix with '-' for descending order (e.g. '-created_at')
            
        Returns:
            A list of all model instances
        """
        async with cls.get_session() as session:
            statement = select(cls)
            
            # Apply ordering
            statement = cls._apply_order_by(statement, order_by)
            
            if include_relationships:
                # Get all relationship attributes, including auto-detected ones
                for rel_name in cls._get_auto_relationship_fields():
                    statement = statement.options(selectinload(getattr(cls, rel_name)))
                    
            result = await session.execute(statement)
            return result.scalars().all()
    
    @classmethod
    async def first(
        cls: Type[T], 
        include_relationships: bool = False,
        order_by: Optional[Union[str, List[str]]] = None
    ) -> Optional[T]:
        """
        Retrieve the first record of this model.
        
        Args:
            include_relationships: If True, eagerly load all relationships
            order_by: Field(s) to order by. Can be a string or list of strings.
                      Prefix with '-' for descending order (e.g. '-created_at')
            
        Returns:
            The first model instance or None if no records exist
        """
        async with cls.get_session() as session:
            statement = select(cls)
            
            # Apply ordering
            statement = cls._apply_order_by(statement, order_by)
            
            if include_relationships:
                # Get all relationship attributes, including auto-detected ones
                for rel_name in cls._get_auto_relationship_fields():
                    statement = statement.options(selectinload(getattr(cls, rel_name)))
                    
            result = await session.execute(statement)
            return result.scalars().first()
    
    @classmethod
    async def limit(
        cls: Type[T], 
        count: int, 
        include_relationships: bool = False,
        order_by: Optional[Union[str, List[str]]] = None
    ) -> List[T]:
        """
        Retrieve a limited number of records of this model.
        
        Args:
            count: Maximum number of records to retrieve
            include_relationships: If True, eagerly load all relationships
            order_by: Field(s) to order by. Can be a string or list of strings.
                      Prefix with '-' for descending order (e.g. '-created_at')
            
        Returns:
            A list of model instances up to the specified count
        """
        async with cls.get_session() as session:
            statement = select(cls).limit(count)
            
            # Apply ordering
            statement = cls._apply_order_by(statement, order_by)
            
            if include_relationships:
                # Get all relationship attributes, including auto-detected ones
                for rel_name in cls._get_auto_relationship_fields():
                    statement = statement.options(selectinload(getattr(cls, rel_name)))
                    
            result = await session.execute(statement)
            return result.scalars().all()

    @classmethod
    async def get_by_id(cls: Type[T], id: int, include_relationships: bool = False) -> Optional[T]:
        """
        Retrieve a record by its primary key.
        
        Args:
            id: The primary key value
            include_relationships: If True, eagerly load all relationships
            
        Returns:
            The model instance or None if not found
        """
        async with cls.get_session() as session:
            if include_relationships:
                # Get all relationship attributes, including auto-detected ones
                statement = select(cls).where(cls.id == id)
                for rel_name in cls._get_auto_relationship_fields():
                    statement = statement.options(selectinload(getattr(cls, rel_name)))
                result = await session.execute(statement)
                return result.scalars().first()
            else:
                return await session.get(cls, id)

    @classmethod
    async def get_by_attribute(
        cls: Type[T], 
        all: bool = False, 
        include_relationships: bool = False,
        order_by: Optional[Union[str, List[str]]] = None,
        **kwargs
    ) -> Union[Optional[T], List[T]]:
        """
        Retrieve record(s) by matching attribute values.
        
        Args:
            all: If True, return all matching records, otherwise return only the first one
            include_relationships: If True, eagerly load all relationships
            order_by: Field(s) to order by. Can be a string or list of strings.
                      Prefix with '-' for descending order (e.g. '-created_at')
            **kwargs: Attribute filters (field=value)
            
        Returns:
            A single model instance, a list of instances, or None if not found
        """
        async with cls.get_session() as session:
            statement = select(cls).filter_by(**kwargs)
            
            # Apply ordering
            statement = cls._apply_order_by(statement, order_by)
            
            if include_relationships:
                # Get all relationship attributes, including auto-detected ones
                for rel_name in cls._get_auto_relationship_fields():
                    statement = statement.options(selectinload(getattr(cls, rel_name)))
                    
            result = await session.execute(statement)
            if all:
                return result.scalars().all()
            return result.scalars().first()

    @classmethod
    async def get_with_related(
        cls: Type[T], 
        id: int, 
        *related_fields: str
    ) -> Optional[T]:
        """
        Retrieve a record by its primary key with specific related fields eagerly loaded.
        
        Args:
            id: The primary key value
            *related_fields: Names of relationship fields to eagerly load
            
        Returns:
            The model instance with related fields loaded, or None if not found
        """
        async with cls.get_session() as session:
            statement = select(cls).where(cls.id == id)
            
            for field_name in related_fields:
                if hasattr(cls, field_name):
                    statement = statement.options(selectinload(getattr(cls, field_name)))
            
            result = await session.execute(statement)
            return result.scalars().first()

    @classmethod
    async def insert(cls: Type[T], data: Dict[str, Any], include_relationships: bool = False) -> T:
        """
        Insert a new record.
        
        Args:
            data: Dictionary of field values
            include_relationships: If True, return the instance with relationships loaded
            
        Returns:
            The created model instance
        """
        async with cls.get_session() as session:
            obj = cls(**data)
            session.add(obj)
            await session.commit()
            
            if include_relationships:
                # Refresh with relationships
                statement = select(cls).where(cls.id == obj.id)
                for rel_name in cls._get_auto_relationship_fields():
                    statement = statement.options(selectinload(getattr(cls, rel_name)))
                result = await session.execute(statement)
                return result.scalars().first()
            else:
                await session.refresh(obj)
                return obj

    @classmethod
    async def update(
        cls: Type[T], 
        id: int, 
        data: Dict[str, Any], 
        include_relationships: bool = False
    ) -> Optional[T]:
        """
        Update an existing record by its ID.
        
        Args:
            id: The primary key value
            data: Dictionary of field values to update
            include_relationships: If True, return the instance with relationships loaded
            
        Returns:
            The updated model instance or None if not found
        """
        async with cls.get_session() as session:
            # Explicitly update updated_at since bulk updates bypass ORM events.
            data["updated_at"] = datetime.now(tz.utc)
            statement = sqlalchemy_update(cls).where(cls.id == id).values(**data).execution_options(synchronize_session="fetch")
            await session.execute(statement)
            await session.commit()
            
            if include_relationships:
                return await cls.get_with_related(id, *cls._get_auto_relationship_fields())
            else:
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

    @classmethod
    async def create_with_related(
        cls: Type[T], 
        data: Dict[str, Any],
        related_data: Dict[str, List[Dict[str, Any]]] = None
    ) -> T:
        """
        Create a model instance with related objects in a single transaction.
        
        Args:
            data: Dictionary of field values for the main model
            related_data: Dictionary mapping relationship names to lists of data dictionaries
                          for creating related objects
                          
        Returns:
            The created model instance with relationships loaded
        """
        if related_data is None:
            related_data = {}
            
        async with cls.get_session() as session:
            # Create the main object
            obj = cls(**data)
            session.add(obj)
            await session.flush()  # Flush to get the ID
            
            # Create related objects
            for rel_name, items_data in related_data.items():
                if not hasattr(cls, rel_name):
                    continue
                    
                rel_attr = getattr(cls, rel_name)
                if not hasattr(rel_attr, "property"):
                    continue
                    
                # Get the related model class and the back reference attribute
                related_model = rel_attr.property.mapper.class_
                back_populates = getattr(rel_attr.property, "back_populates", None)
                
                # Create each related object
                for item_data in items_data:
                    # Set the back reference if it exists
                    if back_populates:
                        item_data[back_populates] = obj
                        
                    related_obj = related_model(**item_data)
                    session.add(related_obj)
            
            await session.commit()
            
            # Refresh with relationships
            await session.refresh(obj, attribute_names=list(related_data.keys()))
            return obj

    def to_dict(self, include_relationships: bool = False, max_depth: int = 1) -> Dict[str, Any]:
        """
        Convert the model instance to a dictionary.
        
        Args:
            include_relationships: If True, include relationship fields in the output
            max_depth: Maximum depth for nested relationships (to prevent circular references)
            
        Returns:
            Dictionary representation of the model
        """
        if max_depth <= 0:
            return {}
            
        # Get basic fields
        result = self.model_dump()
        
        # Add relationship fields if requested
        if include_relationships and max_depth > 0:
            for rel_name in self.__class__._get_auto_relationship_fields():
                rel_value = getattr(self, rel_name, None)
                
                if rel_value is None:
                    result[rel_name] = None
                elif isinstance(rel_value, list):
                    # Handle one-to-many relationships
                    result[rel_name] = [
                        item.to_dict(include_relationships=True, max_depth=max_depth-1)
                        for item in rel_value
                    ]
                else:
                    # Handle many-to-one relationships
                    result[rel_name] = rel_value.to_dict(
                        include_relationships=True, 
                        max_depth=max_depth-1
                    )
                    
        return result
        
    async def load_related(self, *related_fields: str) -> None:
        """
        Eagerly load specific related fields for this instance.
        
        Args:
            *related_fields: Names of relationship fields to load
        """
        if not related_fields:
            return
            
        async with self.__class__.get_session() as session:
            # Refresh the instance with the specified relationships
            await session.refresh(self, attribute_names=related_fields)

# Register an event listener to update 'updated_at' on instance modifications.
@event.listens_for(Session, "before_flush")
def _update_updated_at(sync_session, flush_context, instances):
    for instance in sync_session.dirty:
        if isinstance(instance, EasyModel) and hasattr(instance, "updated_at"):
            instance.updated_at = datetime.now(tz.utc)

async def init_db():
    """
    Initialize the database connection and create all tables.
    """
    from . import db_config
    
    # Import auto_relationships functions with conditional import to avoid circular imports
    try:
        from .auto_relationships import _auto_relationships_enabled, process_auto_relationships
        has_auto_relationships = True
    except ImportError:
        has_auto_relationships = False
    
    # Process auto-relationships before creating tables if enabled
    if has_auto_relationships and _auto_relationships_enabled:
        process_auto_relationships()
    
    # Create async engine and all tables
    engine = db_config.get_engine()
    if not engine:
        raise ValueError("Database configuration is missing. Use db_config.configure_* methods first.")
    
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    
    logging.info("Database initialized")
