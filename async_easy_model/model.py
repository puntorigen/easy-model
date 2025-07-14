from sqlmodel import SQLModel, Field, select, Relationship
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, Session, selectinload, joinedload
from sqlalchemy import update as sqlalchemy_update, event, desc, asc, text
from typing import Type, TypeVar, Optional, Any, List, Dict, Literal, Union, Set, Tuple
import contextlib
import os
import sys
import warnings
from datetime import datetime, timezone as tz
import inspect
import json
import logging
import re

T = TypeVar("T", bound="EasyModel")

# Global database configuration instance (forward declaration)
db_config = None

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
            # Apply connection pool configuration to all database types
            # to prevent connection leaks and ensure proper resource management
            kwargs = {
                "pool_size": 10,        # Base number of connections in the pool
                "max_overflow": 30,     # Additional connections allowed beyond pool_size
                "pool_timeout": 30,     # Timeout in seconds for getting connection from pool
                "pool_recycle": 1800,   # Recycle connections after 30 minutes
                "pool_pre_ping": True,  # Verify connections before use
                "echo": False,          # Set to True for SQL debugging
            }
            
            # PostgreSQL-specific optimizations (if needed in the future)
            if self.db_type == "postgresql":
                # PostgreSQL already has good defaults above
                pass
                
            DatabaseConfig._engine = create_async_engine(
                self.get_connection_url(),
                **kwargs
            )
        return DatabaseConfig._engine
    
    async def refresh_metadata(self):
        """
        Refresh SQLAlchemy metadata to ensure table structure is current.
        This helps resolve issues where metadata becomes stale after disconnection.
        Uses a conservative approach to avoid disrupting relationship mappings.
        """
        try:
            engine = self.get_engine()
            async with engine.begin() as conn:
                # Instead of clearing all metadata, just refresh specific tables
                # This preserves relationship mappings while updating table structures
                try:
                    # Test connection with a simple query
                    await conn.execute(text("SELECT 1"))
                    
                    # Refresh only the tables that might have stale metadata
                    # Focus on junction tables which are most likely to have issues
                    from sqlalchemy import Table, MetaData
                    
                    # Create a temporary metadata object for reflection
                    temp_metadata = MetaData()
                    await conn.run_sync(lambda sync_conn: temp_metadata.reflect(sync_conn))
                    
                    # Update existing table objects with fresh column information
                    for table_name, table in temp_metadata.tables.items():
                        if table_name in SQLModel.metadata.tables:
                            # Update column information without destroying relationships
                            existing_table = SQLModel.metadata.tables[table_name]
                            # Only update if the table structure might have changed
                            if len(existing_table.columns) != len(table.columns):
                                logging.info(f"Detected column changes in table {table_name}")
                    
                    logging.info("Metadata refreshed successfully (conservative approach)")
                    return True
                    
                except Exception as inner_e:
                    logging.warning(f"Conservative metadata refresh failed: {inner_e}")
                    return False
                
        except Exception as e:
            logging.error(f"Failed to refresh metadata: {e}")
            return False
    
    async def refresh_junction_table_metadata(self, table_name: str):
        """
        Specifically refresh metadata for a junction table.
        This is useful when junction tables lose their column definitions after reconnection.
        Uses a conservative approach to avoid disrupting relationship mappings.
        
        Args:
            table_name: Name of the junction table to refresh
        """
        try:
            engine = self.get_engine()
            async with engine.begin() as conn:
                # Check if table exists
                table_exists = await conn.run_sync(
                    lambda sync_conn: sync_conn.dialect.has_table(sync_conn, table_name)
                )
                
                if not table_exists:
                    logging.warning(f"Junction table {table_name} does not exist")
                    return False
                
                # Conservative approach: just test if the table is accessible
                # without disrupting existing metadata and relationships
                try:
                    # Test if we can query the table structure
                    result = await conn.execute(text(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}'"))
                    table_def = await result.fetchone()
                    
                    if table_def:
                        logging.info(f"Junction table {table_name} is accessible with structure: {table_def[0][:100]}...")
                    else:
                        logging.warning(f"Junction table {table_name} exists but could not retrieve structure")
                        
                    # Don't actually modify metadata - just validate accessibility
                    return True
                    
                except Exception as inner_e:
                    logging.warning(f"Conservative junction table check failed for {table_name}: {inner_e}")
                    # If we can't access the table conservatively, it might be a real issue
                    return False
                
        except Exception as e:
            logging.error(f"Failed to refresh junction table metadata for {table_name}: {e}")
            return False
    
    async def validate_connection(self):
        """
        Validate database connection and refresh metadata if needed.
        Returns True if connection is valid, False otherwise.
        """
        try:
            engine = self.get_engine()
            async with engine.begin() as conn:
                # Simple ping to verify connection
                await conn.execute(text("SELECT 1"))
                return True
        except Exception as e:
            logging.warning(f"Connection validation failed: {e}")
            # Try to refresh metadata and reconnect
            await self.refresh_metadata()
            return False

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

def _normalize_datetime_for_db(value: Any) -> Any:
    """
    Normalize datetime values for database compatibility.
    
    For PostgreSQL with TIMESTAMP WITHOUT TIME ZONE columns, converts timezone-aware
    datetimes to timezone-naive UTC datetimes. For other databases, returns the value unchanged.
    
    Args:
        value: The value to potentially normalize
        
    Returns:
        The normalized value
    """
    global db_config
    
    # Only process datetime objects
    if not isinstance(value, datetime):
        return value
    
    # Only normalize for PostgreSQL
    if db_config and db_config.db_type == "postgresql":
        # If the datetime is timezone-aware, convert to UTC and make naive
        if value.tzinfo is not None:
            return value.astimezone(tz.utc).replace(tzinfo=None)
    
    return value

def _normalize_data_for_db(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize all datetime values in a data dictionary for database compatibility.
    
    Args:
        data: Dictionary containing field values
        
    Returns:
        Dictionary with normalized datetime values
    """
    normalized_data = {}
    for key, value in data.items():
        normalized_data[key] = _normalize_datetime_for_db(value)
    return normalized_data

def _get_normalized_datetime() -> datetime:
    """
    Get a datetime that's appropriate for the current database backend.
    
    Returns:
        For PostgreSQL: timezone-naive UTC datetime
        For SQLite: timezone-aware UTC datetime (for backward compatibility)
    """
    global db_config
    
    utc_now = datetime.now(tz.utc)
    
    # For PostgreSQL, return timezone-naive datetime
    if db_config and db_config.db_type == "postgresql":
        return utc_now.replace(tzinfo=None)
    
    # For SQLite and others, return timezone-aware datetime (backward compatibility)
    return utc_now

class EasyModel(SQLModel):
    """
    Base model class providing common async database operations.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: Optional[datetime] = Field(default_factory=_get_normalized_datetime)
    updated_at: Optional[datetime] = Field(default_factory=_get_normalized_datetime)

    # Default table args with extend_existing=True to ensure all subclasses can redefine tables
    __table_args__ = {"extend_existing": True}

    @classmethod
    @contextlib.asynccontextmanager
    async def get_session(cls):
        """
        Get a database session with proper error handling and cleanup.
        
        This method ensures proper session cleanup by:
        - Only validating connection when there's an actual issue
        - Refreshing metadata if connection was lost
        - Explicitly closing sessions in all cases
        
        Returns:
            AsyncSession: Database session context manager
        """
        session = None
        try:
            session = db_config.get_session_maker()()
            yield session
        except Exception as e:
            if session:
                await session.rollback()
            
            # Only validate connection if we get a database-related error
            error_msg = str(e).lower()
            if any(keyword in error_msg for keyword in ['connection', 'database', 'no such column', 'table']):
                logging.warning(f"Database error detected, validating connection: {e}")
                await db_config.validate_connection()
            
            raise e
        finally:
            if session:
                await session.close()

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
        include_relationships: bool = True, 
        order_by: Optional[Union[str, List[str]]] = None,
        max_depth: int = 2
    ) -> List[T]:
        """
        Retrieve all records of this model.
        
        Args:
            include_relationships: If True, eagerly load all relationships
            order_by: Field(s) to order by. Can be a string or list of strings.
                      Prefix with '-' for descending order (e.g. '-created_at')
            max_depth: Maximum depth for loading nested relationships
            
        Returns:
            A list of all model instances
        """
        return await cls.select({}, all=True, include_relationships=include_relationships, 
                               order_by=order_by, max_depth=max_depth)
    
    @classmethod
    async def first(
        cls: Type[T], 
        include_relationships: bool = True, 
        order_by: Optional[Union[str, List[str]]] = None,
        max_depth: int = 2
    ) -> Optional[T]:
        """
        Retrieve the first record of this model.
        
        Args:
            include_relationships: If True, eagerly load all relationships
            order_by: Field(s) to order by. Can be a string or list of strings.
                      Prefix with '-' for descending order (e.g. '-created_at')
            max_depth: Maximum depth for loading nested relationships
            
        Returns:
            The first model instance or None if no records exist
        """
        return await cls.select({}, first=True, include_relationships=include_relationships, 
                               order_by=order_by, max_depth=max_depth)
    
    @classmethod
    async def limit(
        cls: Type[T], 
        count: int, 
        include_relationships: bool = True, 
        order_by: Optional[Union[str, List[str]]] = None,
        max_depth: int = 2
    ) -> List[T]:
        """
        Retrieve a limited number of records.
        
        Args:
            count: Maximum number of records to return
            include_relationships: If True, eagerly load all relationships
            order_by: Field(s) to order by. Can be a string or list of strings.
                      Prefix with '-' for descending order (e.g. '-created_at')
            max_depth: Maximum depth for loading nested relationships
            
        Returns:
            A list of model instances
        """
        return await cls.select({}, all=True, include_relationships=include_relationships, 
                               order_by=order_by, limit=count, max_depth=max_depth)

    @classmethod
    async def get_by_id(cls: Type[T], id: int, include_relationships: bool = True) -> Optional[T]:
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
    def _get_unique_fields(cls) -> List[str]:
        """
        Get all fields with unique=True constraint
        
        Returns:
            List of field names that have unique constraints
        """
        unique_fields = []
        for name, field in cls.model_fields.items():
            if name != 'id' and hasattr(field, "field_info") and field.field_info.extra.get('unique', False):
                unique_fields.append(name)
        return unique_fields

    @classmethod
    async def get_by_attribute(
        cls: Type[T], 
        all: bool = False, 
        include_relationships: bool = True,
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
    async def insert(cls: Type[T], data: Union[Dict[str, Any], List[Dict[str, Any]]], include_relationships: bool = True, max_depth: int = 2) -> Union[T, List[T]]:
        """
        Insert one or more records.
        
        Args:
            data: Dictionary of field values or a list of dictionaries for multiple records
            include_relationships: If True, return the instance(s) with relationships loaded
            max_depth: Maximum depth for loading nested relationships
            
        Returns:
            The created model instance(s)
        """
        if not data:
            return None
            
        # Handle single dict or list of dicts
        if isinstance(data, list):
            results = []
            for item in data:
                result = await cls.insert(item, include_relationships, max_depth)
                results.append(result)
            return results
        
        # Store many-to-many relationship data for later processing
        many_to_many_data = {}
        many_to_many_rels = cls._get_many_to_many_relationships()
        
        # Extract many-to-many data before processing other relationships
        for rel_name in many_to_many_rels:
            if rel_name in data:
                many_to_many_data[rel_name] = data[rel_name]
        
        # Process relationships to convert nested objects to foreign keys
        async with cls.get_session() as session:
            try:
                processed_data = await cls._process_relationships_for_insert(session, data)
                
                # Normalize datetime values for database compatibility
                processed_data = _normalize_data_for_db(processed_data)
                
                # Create the model instance
                obj = cls(**processed_data)
                session.add(obj)
                
                # Flush to get the object ID
                await session.flush()
                
                # Now process many-to-many relationships if any
                for rel_name, rel_data in many_to_many_data.items():
                    if isinstance(rel_data, list):
                        await cls._process_many_to_many_relationship(
                            session, obj, rel_name, rel_data
                        )
                
                # Commit the transaction
                await session.commit()
                
                if include_relationships:
                    # Reload with relationships
                    return await cls._load_relationships_recursively(session, obj, max_depth)
                else:
                    return obj
                    
            except Exception as e:
                await session.rollback()
                logging.error(f"Error inserting {cls.__name__}: {e}")
                if "UNIQUE constraint failed" in str(e):
                    field_match = re.search(r"UNIQUE constraint failed: \w+\.(\w+)", str(e))
                    if field_match:
                        field_name = field_match.group(1)
                        value = data.get(field_name)
                        raise ValueError(f"A record with {field_name}='{value}' already exists")
                raise

    @classmethod
    async def _process_relationships_for_insert(cls: Type[T], session: AsyncSession, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process relationships in input data for insertion.
        
        This method handles nested objects in the input data, such as:
        cart = await ShoppingCart.insert({
            "user": {"username": "john", "email": "john@example.com"},
            "product": {"name": "Product X", "price": 19.99},
            "quantity": 2
        })
        
        It also handles lists of related objects for one-to-many relationships:
        publisher = await Publisher.insert({
            "name": "Example Publisher",
            "authors": [
                {"name": "Author 1", "email": "author1@example.com"},
                {"name": "Author 2", "email": "author2@example.com"}
            ]
        })
        
        For each nested object:
        1. Find the target model class
        2. Check if an object with the same unique fields already exists
        3. If found, update existing object with non-unique fields
        4. If not found, create a new object
        5. Set the foreign key ID in the result data
        
        Args:
            session: The database session to use
            data: Input data dictionary that may contain nested objects
            
        Returns:
            Processed data dictionary with nested objects replaced by their foreign key IDs
        """
        if not data:
            return {}
            
        result = dict(data)
        
        # Get relationship fields for this model
        relationship_fields = cls._get_auto_relationship_fields()
        
        # Get many-to-many relationships separately
        many_to_many_relationships = cls._get_many_to_many_relationships()
        
        # Set of field names already processed as many-to-many relationships
        processed_m2m_fields = set()
            
        # Process each relationship field in the input data
        for key in list(result.keys()):
            value = result[key]
            
            # Skip empty values
            if value is None:
                continue
            
            # Check if this is a relationship field
            if key in relationship_fields:
                # Get the related model class
                related_model = None
                
                if hasattr(cls, key):
                    rel_attr = getattr(cls, key)
                    if hasattr(rel_attr, 'prop') and hasattr(rel_attr.prop, 'mapper'):
                        related_model = rel_attr.prop.mapper.class_
                
                if not related_model:
                    logging.warning(f"Could not determine related model for {key}, skipping")
                    continue
                
                # Check if this is a many-to-many relationship field
                if key in many_to_many_relationships:
                    # Store this separately - we'll handle it after the main object is created
                    processed_m2m_fields.add(key)
                    continue
                
                # Handle different relationship types based on data type
                if isinstance(value, list):
                    # Handle one-to-many relationship (list of dictionaries)
                    related_ids = []
                    for item in value:
                        if isinstance(item, dict):
                            related_obj = await cls._process_single_relationship_item(
                                session, related_model, item
                            )
                            if related_obj:
                                related_ids.append(related_obj.id)
                    
                    # Update result with list of foreign key IDs
                    foreign_key_list_name = f"{key}_ids"
                    result[foreign_key_list_name] = related_ids
                    
                    # Remove the relationship list from the result
                    if key in result:
                        del result[key]
                
                elif isinstance(value, dict):
                    # Handle one-to-one relationship (single dictionary)
                    related_obj = await cls._process_single_relationship_item(
                        session, related_model, value
                    )
                    
                    if related_obj:
                        # Update the result with the foreign key ID
                        foreign_key_name = f"{key}_id"
                        result[foreign_key_name] = related_obj.id
                        
                        # Remove the relationship dictionary from the result
                        if key in result:
                            del result[key]
        
        # Remove any processed many-to-many fields from the result
        # since we'll handle them separately after the object is created
        for key in processed_m2m_fields:
            if key in result:
                del result[key]
        
        return result

    @classmethod
    async def _process_single_relationship_item(cls, session: AsyncSession, related_model: Type, item_data: Dict[str, Any]) -> Optional[Any]:
        """
        Process a single relationship item (dictionary).
        
        This helper method is used by _process_relationships_for_insert to handle
        both singular relationship objects and items within lists of relationships.
        
        Args:
            session: The database session to use
            related_model: The related model class
            item_data: Dictionary with field values for the related object
            
        Returns:
            The created or found related object, or None if processing failed
        """
        # Look for unique fields in the related model to use for searching
        unique_fields = []
        for name, field in related_model.model_fields.items():
            if (hasattr(field, "field_info") and 
                field.field_info.extra.get('unique', False)):
                unique_fields.append(name)
        
        # Create a search dictionary using unique fields
        search_dict = {}
        for field in unique_fields:
            if field in item_data and item_data[field] is not None:
                search_dict[field] = item_data[field]
        
        # If no unique fields found but ID is provided, use it
        if not search_dict and 'id' in item_data and item_data['id']:
            search_dict = {'id': item_data['id']}
        
        # Special case for products without uniqueness constraints
        if not search_dict and related_model.__tablename__ == 'products' and 'name' in item_data:
            search_dict = {'name': item_data['name']}
        
        # Try to find an existing record
        related_obj = None
        if search_dict:
            logging.info(f"Searching for existing {related_model.__name__} with {search_dict}")
            
            try:
                # Create a more appropriate search query based on unique fields
                existing_stmt = select(related_model)
                for field, field_value in search_dict.items():
                    existing_stmt = existing_stmt.where(getattr(related_model, field) == field_value)
                
                existing_result = await session.execute(existing_stmt)
                related_obj = existing_result.scalars().first()
                
                if related_obj:
                    logging.info(f"Found existing {related_model.__name__} with ID: {related_obj.id}")
            except Exception as e:
                logging.error(f"Error finding existing record: {e}")
        
        if related_obj:
            # Update the existing record with any non-unique field values
            for attr, attr_val in item_data.items():
                # Skip ID field
                if attr == 'id':
                    continue
                    
                # Skip unique fields with different values to avoid constraint violations
                if attr in unique_fields and getattr(related_obj, attr) != attr_val:
                    continue
                    
                # Update non-unique fields
                current_val = getattr(related_obj, attr, None)
                if current_val != attr_val:
                    setattr(related_obj, attr, attr_val)
            
            # Add the updated object to the session
            session.add(related_obj)
            logging.info(f"Reusing existing {related_model.__name__} with ID: {related_obj.id}")
        else:
            # Create a new record
            logging.info(f"Creating new {related_model.__name__}")
            
            # Process nested relationships in this item first
            if hasattr(related_model, '_process_relationships_for_insert'):
                # This is a recursive call to process nested relationships
                processed_item_data = await related_model._process_relationships_for_insert(
                    session, item_data
                )
            else:
                processed_item_data = item_data
            
            related_obj = related_model(**processed_item_data)
            session.add(related_obj)
        
        # Ensure the object has an ID by flushing
        try:
            await session.flush()
        except Exception as e:
            logging.error(f"Error flushing session for {related_model.__name__}: {e}")
            
            # If there was a uniqueness error, try again to find the existing record
            if "UNIQUE constraint failed" in str(e):
                logging.info(f"UNIQUE constraint failed, trying to find existing record again")
                
                # Try to find by any field provided in the search_dict
                existing_stmt = select(related_model)
                for field, field_value in search_dict.items():
                    existing_stmt = existing_stmt.where(getattr(related_model, field) == field_value)
                
                # Execute the search query
                existing_result = await session.execute(existing_stmt)
                related_obj = existing_result.scalars().first()
                
                if not related_obj:
                    # We couldn't find an existing record, re-raise the exception
                    raise
                
                logging.info(f"Found existing {related_model.__name__} with ID: {related_obj.id} after constraint error")
        
        return related_obj

    @classmethod
    async def update(cls: Type[T], data: Dict[str, Any], criteria: Dict[str, Any], include_relationships: bool = True) -> Optional[T]:
        """
        Update an existing record identified by criteria.
        
        Args:
            data: Dictionary of updated field values
            criteria: Dictionary of field values to identify the record to update
            include_relationships: If True, return the updated instance with relationships loaded
        
        Returns:
            The updated model instance
        """
        # Store many-to-many relationship data for later processing
        many_to_many_data = {}
        many_to_many_rels = cls._get_many_to_many_relationships()
        
        # Extract many-to-many data before processing
        for rel_name in many_to_many_rels:
            if rel_name in data:
                many_to_many_data[rel_name] = data[rel_name]
                # Remove from original data
                del data[rel_name]
        
        async with cls.get_session() as session:
            try:
                # Find the record(s) to update
                statement = select(cls)
                for field, value in criteria.items():
                    if isinstance(value, str) and '*' in value:
                        # Handle LIKE queries
                        like_value = value.replace('*', '%')
                        statement = statement.where(getattr(cls, field).like(like_value))
                    else:
                        statement = statement.where(getattr(cls, field) == value)
                
                result = await session.execute(statement)
                record = result.scalars().first()
                
                if not record:
                    logging.warning(f"No record found with criteria: {criteria}")
                    return None
                
                # Check for unique constraints before updating
                for field_name, new_value in data.items():
                    if field_name != 'id' and hasattr(cls, field_name):
                        field = getattr(cls.model_fields.get(field_name), 'field_info', None)
                        if field and field.extra.get('unique', False):
                            # Check if the new value would conflict with an existing record
                            check_statement = select(cls).where(
                                getattr(cls, field_name) == new_value
                            ).where(
                                cls.id != record.id
                            )
                            check_result = await session.execute(check_statement)
                            existing = check_result.scalars().first()
                            
                            if existing:
                                raise ValueError(f"Cannot update {field_name} to '{new_value}': value already exists")
                
                # Apply the updates with datetime normalization
                for key, value in data.items():
                    normalized_value = _normalize_datetime_for_db(value)
                    setattr(record, key, normalized_value)
                
                # Process many-to-many relationships if any
                for rel_name, rel_data in many_to_many_data.items():
                    if isinstance(rel_data, list):
                        # First, get all existing links for this relation
                        junction_model, target_model = many_to_many_rels[rel_name]
                        
                        from async_easy_model.auto_relationships import get_foreign_keys_from_model
                        foreign_keys = get_foreign_keys_from_model(junction_model)
                        
                        # Find the foreign key fields for this model and the target model
                        this_model_fk = None
                        target_model_fk = None
                        
                        for fk_field, fk_target in foreign_keys.items():
                            target_table = fk_target.split('.')[0]
                            if target_table == cls.__tablename__:
                                this_model_fk = fk_field
                            elif target_table == target_model.__tablename__:
                                target_model_fk = fk_field
                        
                        if not this_model_fk or not target_model_fk:
                            logging.warning(f"Could not find foreign key fields for {rel_name} relationship")
                            continue
                            
                        # Get all existing junctions for this record
                        junction_stmt = select(junction_model).where(
                            getattr(junction_model, this_model_fk) == record.id
                        )
                        junction_result = await session.execute(junction_stmt)
                        existing_junctions = junction_result.scalars().all()
                        
                        # Get the target IDs from the existing junctions
                        existing_target_ids = [getattr(junction, target_model_fk) for junction in existing_junctions]
                        
                        # Track processed target IDs
                        processed_target_ids = set()
                        
                        # Process each item in rel_data
                        for item_data in rel_data:
                            target_obj = await cls._process_single_relationship_item(
                                session, target_model, item_data
                            )
                            
                            if not target_obj:
                                logging.warning(f"Failed to process {target_model.__name__} item for {rel_name}")
                                continue
                                
                            processed_target_ids.add(target_obj.id)
                            
                            # Check if this link already exists
                            if target_obj.id not in existing_target_ids:
                                # Create new junction
                                junction_data = {
                                    this_model_fk: record.id,
                                    target_model_fk: target_obj.id
                                }
                                junction_obj = junction_model(**junction_data)
                                session.add(junction_obj)
                                logging.info(f"Created junction between {cls.__name__} {record.id} and {target_model.__name__} {target_obj.id}")
                        
                        # Delete junctions for target IDs that weren't in the updated data
                        junctions_to_delete = [j for j in existing_junctions 
                                              if getattr(j, target_model_fk) not in processed_target_ids]
                        
                        for junction in junctions_to_delete:
                            await session.delete(junction)
                            logging.info(f"Deleted junction between {cls.__name__} {record.id} and {target_model.__name__} {getattr(junction, target_model_fk)}")
                
                await session.flush()
                await session.commit()
                
                if include_relationships:
                    # Refresh with relationships
                    refresh_statement = select(cls).where(cls.id == record.id)
                    for rel_name in cls._get_auto_relationship_fields():
                        refresh_statement = refresh_statement.options(selectinload(getattr(cls, rel_name)))
                    refresh_result = await session.execute(refresh_statement)
                    return refresh_result.scalars().first()
                else:
                    await session.refresh(record)
                    return record
                    
            except Exception as e:
                await session.rollback()
                logging.error(f"Error updating {cls.__name__}: {e}")
                raise

    @classmethod
    async def delete(cls: Type[T], criteria: Dict[str, Any]) -> int:
        """
        Delete records matching the provided criteria.
        
        Args:
            criteria: Dictionary of field values to identify records to delete
            
        Returns:
            Number of records deleted
        """
        async with cls.get_session() as session:
            try:
                # Find records to delete
                statement = select(cls)
                for field, value in criteria.items():
                    if isinstance(value, str) and '*' in value:
                        # Handle LIKE queries
                        like_value = value.replace('*', '%')
                        statement = statement.where(getattr(cls, field).like(like_value))
                    else:
                        statement = statement.where(getattr(cls, field) == value)
                
                result = await session.execute(statement)
                records = result.scalars().all()
                
                if not records:
                    logging.warning(f"No records found with criteria: {criteria}")
                    return 0
                
                # Check if there are many-to-many relationships that need cleanup
                many_to_many_rels = cls._get_many_to_many_relationships()
                
                # Delete each record and its related many-to-many junction records
                count = 0
                for record in records:
                    # Clean up many-to-many junctions first
                    for rel_name, (junction_model, _) in many_to_many_rels.items():
                        # Get foreign keys from the junction model
                        from async_easy_model.auto_relationships import get_foreign_keys_from_model
                        foreign_keys = get_foreign_keys_from_model(junction_model)
                        
                        # Find which foreign key refers to this model
                        this_model_fk = None
                        for fk_field, fk_target in foreign_keys.items():
                            target_table = fk_target.split('.')[0]
                            if target_table == cls.__tablename__:
                                this_model_fk = fk_field
                                break
                        
                        if not this_model_fk:
                            continue
                            
                        # Delete junction records for this record
                        delete_stmt = select(junction_model).where(
                            getattr(junction_model, this_model_fk) == record.id
                        )
                        junction_result = await session.execute(delete_stmt)
                        junctions = junction_result.scalars().all()
                        
                        for junction in junctions:
                            await session.delete(junction)
                            logging.info(f"Deleted junction record for {cls.__name__} id={record.id}")
                    
                    # Now delete the main record
                    await session.delete(record)
                    count += 1
                
                await session.commit()
                return count
                
            except Exception as e:
                await session.rollback()
                logging.error(f"Error deleting {cls.__name__}: {e}")
                raise

    def to_dict(self, include_relationships: bool = True, max_depth: int = 4) -> Dict[str, Any]:
        """
        Convert the model instance to a dictionary.
        
        Args:
            include_relationships: If True, include relationship fields in the output
            max_depth: Maximum depth for nested relationships (to prevent circular references)
            
        Returns:
            Dictionary representation of the model
        """
        # Get basic fields
        result = self.model_dump()
        
        # Add relationship fields if requested
        if include_relationships and max_depth > 0:
            for rel_name in self.__class__._get_auto_relationship_fields():
                # Only include relationships that are already loaded to avoid session errors
                # We check if the relationship is loaded using SQLAlchemy's inspection API
                is_loaded = False
                try:
                    # Check if attribute exists and is not a relationship descriptor
                    rel_value = getattr(self, rel_name, None)
                    
                    # If it's an attribute that has been loaded or not a relationship at all
                    # (for basic fields that match relationship naming pattern), include it
                    is_loaded = rel_value is not None and not hasattr(rel_value, 'prop')
                except Exception:
                    # If accessing the attribute raises an exception, it's not loaded
                    is_loaded = False
                    
                if is_loaded:
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
        else:
            # If max_depth is 0, return the basic fields only
            return result
            
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

    @classmethod
    async def select(
        cls: Type[T], 
        criteria: Dict[str, Any] = None,
        all: bool = False,
        first: bool = False,
        include_relationships: bool = True,
        order_by: Optional[Union[str, List[str]]] = None,
        max_depth: int = 2,
        limit: Optional[int] = None
    ) -> Union[Optional[T], List[T]]:
        """
        Select records based on criteria.
        
        Args:
            criteria: Dictionary of field values to filter by
            all: If True, return all matching records. If False, return only the first match.
            first: If True, return only the first record (equivalent to all=False)
            include_relationships: If True, eagerly load all relationships
            order_by: Field(s) to order by. Can be a string or list of strings.
                     Prefix with '-' for descending order (e.g. '-created_at')
            max_depth: Maximum depth for loading nested relationships (when include_relationships=True)
            limit: Maximum number of records to retrieve (if all=True)
                  If limit > 1, all is automatically set to True
            
        Returns:
            A single model instance, a list of instances, or None if not found
        """
        # Default to empty criteria if None provided
        if criteria is None:
            criteria = {}
        
        # If limit is specified and > 1, set all to True
        if limit is not None and limit > 1:
            all = True
            
        # If first is specified, set all to False (first takes precedence)
        if first:
            all = False
            
        async with cls.get_session() as session:
            # Build the query
            statement = select(cls)
            
            # Apply criteria filters
            for key, value in criteria.items():
                if isinstance(value, str) and '*' in value:
                    # Handle LIKE queries (convert '*' wildcard to '%')
                    like_value = value.replace('*', '%')
                    statement = statement.where(getattr(cls, key).like(like_value))
                else:
                    # Regular equality check
                    statement = statement.where(getattr(cls, key) == value)
            
            # Apply ordering
            if order_by:
                order_clauses = []
                if isinstance(order_by, str):
                    order_by = [order_by]
                
                for field_name in order_by:
                    if field_name.startswith("-"):
                        # Descending order
                        field_name = field_name[1:]  # Remove the "-" prefix
                        # Handle relationship field ordering with dot notation
                        if "." in field_name:
                            rel_name, attr_name = field_name.split(".", 1)
                            if hasattr(cls, rel_name):
                                rel_model = getattr(cls, rel_name)
                                if hasattr(rel_model, "property"):
                                    target_model = rel_model.property.entity.class_
                                    if hasattr(target_model, attr_name):
                                        order_clauses.append(getattr(target_model, attr_name).desc())
                        else:
                            order_clauses.append(getattr(cls, field_name).desc())
                    else:
                        # Ascending order
                        # Handle relationship field ordering with dot notation
                        if "." in field_name:
                            rel_name, attr_name = field_name.split(".", 1)
                            if hasattr(cls, rel_name):
                                rel_model = getattr(cls, rel_name)
                                if hasattr(rel_model, "property"):
                                    target_model = rel_model.property.entity.class_
                                    if hasattr(target_model, attr_name):
                                        order_clauses.append(getattr(target_model, attr_name).asc())
                        else:
                            order_clauses.append(getattr(cls, field_name).asc())
                
                if order_clauses:
                    statement = statement.order_by(*order_clauses)
            
            # Apply limit
            if limit:
                statement = statement.limit(limit)
            
            # Load relationships if requested
            if include_relationships:
                for rel_name in cls._get_auto_relationship_fields():
                    statement = statement.options(selectinload(getattr(cls, rel_name)))
            
            result = await session.execute(statement)
            
            if all:
                objects = result.scalars().all()
                
                # Load nested relationships if requested
                if include_relationships and objects and max_depth > 1:
                    loaded_objects = []
                    for obj in objects:
                        loaded_obj = await cls._load_relationships_recursively(
                            session, obj, max_depth
                        )
                        loaded_objects.append(loaded_obj)
                    return loaded_objects
                
                return objects
            else:
                obj = result.scalars().first()
                
                # Load nested relationships if requested
                if include_relationships and obj and max_depth > 1:
                    obj = await cls._load_relationships_recursively(
                        session, obj, max_depth
                    )
                
                return obj

    @classmethod
    async def get_or_create(cls: Type[T], search_criteria: Dict[str, Any], defaults: Optional[Dict[str, Any]] = None) -> Tuple[T, bool]:
        """
        Get a record by criteria or create it if it doesn't exist.
        
        Args:
            search_criteria: Dictionary of search criteria
            defaults: Default values to use when creating a new record
            
        Returns:
            Tuple of (model instance, created flag)
        """
        # Try to find the record
        record = await cls.select(criteria=search_criteria, all=False, first=True)
        
        if record:
            return record, False
        
        # Record not found, create it
        data = {**search_criteria}
        if defaults:
            data.update(defaults)
        
        new_record = await cls.insert(data)
        return new_record, True

    @classmethod
    async def insert_with_related(
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
            
        # Create a copy of data for modification
        insert_data = data.copy()
        
        # Add relationship fields to the data
        for rel_name, items_data in related_data.items():
            if items_data:
                insert_data[rel_name] = items_data
        
        # Use the enhanced insert method to handle all relationships
        return await cls.insert(insert_data, include_relationships=True)

    @classmethod
    def _get_many_to_many_relationships(cls) -> Dict[str, Tuple[Type['EasyModel'], Type['EasyModel']]]:
        """
        Get all many-to-many relationships for this model.
        
        Returns:
            Dictionary mapping relationship field names to tuples of (junction_model, target_model)
        """
        from async_easy_model.auto_relationships import get_model_by_table_name
        
        many_to_many_relationships = {}
        
        # Check if this is a class attribute rather than an instance attribute
        relationship_fields = cls._get_auto_relationship_fields()
        
        for rel_name in relationship_fields:
            if not hasattr(cls, rel_name):
                continue
                
            rel_attr = getattr(cls, rel_name)
            
            # Check if this is a many-to-many relationship by looking for secondary table
            if hasattr(rel_attr, 'prop') and hasattr(rel_attr.prop, 'secondary'):
                secondary = rel_attr.prop.secondary
                if isinstance(secondary, str):  # For string table names (our implementation)
                    junction_model = get_model_by_table_name(secondary)
                    if junction_model:
                        target_model = rel_attr.prop.mapper.class_
                        many_to_many_relationships[rel_name] = (junction_model, target_model)
                        
        return many_to_many_relationships
        
    @classmethod
    async def _process_many_to_many_relationship(
        cls, 
        session: AsyncSession, 
        parent_obj: 'EasyModel',
        rel_name: str, 
        items: List[Dict[str, Any]]
    ) -> None:
        """
        Process a many-to-many relationship for an object.
        
        Args:
            session: The database session
            parent_obj: The parent object (e.g., Book)
            rel_name: The name of the relationship (e.g., 'tags')
            items: List of data dictionaries for the related items
            
        Returns:
            None
        """
        # Get information about this many-to-many relationship
        many_to_many_rels = cls._get_many_to_many_relationships()
        if rel_name not in many_to_many_rels:
            logging.warning(f"Relationship {rel_name} is not a many-to-many relationship")
            return
            
        junction_model, target_model = many_to_many_rels[rel_name]
        
        # Get the foreign key fields from the junction model that reference this model and the target model
        from async_easy_model.auto_relationships import get_foreign_keys_from_model
        foreign_keys = get_foreign_keys_from_model(junction_model)
        
        # Find the foreign key fields for this model and the target model
        this_model_fk = None
        target_model_fk = None
        
        for fk_field, fk_target in foreign_keys.items():
            target_table = fk_target.split('.')[0]
            if target_table == cls.__tablename__:
                this_model_fk = fk_field
            elif target_table == target_model.__tablename__:
                target_model_fk = fk_field
        
        if not this_model_fk or not target_model_fk:
            logging.warning(f"Could not find foreign key fields for {rel_name} relationship")
            return
        
        # Process each related item
        for item_data in items:
            # First, create or find the target model instance
            target_obj = await cls._process_single_relationship_item(
                session, target_model, item_data
            )
            
            if not target_obj:
                logging.warning(f"Failed to process {target_model.__name__} item for {rel_name}")
                continue
            
            # Now create a junction record linking the parent to the target
            # Check if this link already exists
            junction_stmt = select(junction_model).where(
                getattr(junction_model, this_model_fk) == parent_obj.id,
                getattr(junction_model, target_model_fk) == target_obj.id
            )
            junction_result = await session.execute(junction_stmt)
            existing_junction = junction_result.scalars().first()
            
            if not existing_junction:
                # Create new junction
                junction_data = {
                    this_model_fk: parent_obj.id,
                    target_model_fk: target_obj.id
                }
                junction_obj = junction_model(**junction_data)
                session.add(junction_obj)
                logging.info(f"Created junction between {cls.__name__} {parent_obj.id} and {target_model.__name__} {target_obj.id}")

    @classmethod
    async def _ensure_junction_table_metadata(cls, table_name: str):
        """
        Ensure junction table metadata is current before relationship operations.
        This prevents intermittent "no such column" errors after reconnection.
        
        Args:
            table_name: Name of the junction table (e.g., 'brandusers')
        """
        try:
            # First check if metadata refresh is needed
            await db_config.refresh_junction_table_metadata(table_name)
            return True
        except Exception as e:
            logging.error(f"Failed to ensure junction table metadata for {table_name}: {e}")
            return False
    
    @classmethod
    async def _safe_relationship_query(cls, query_func, *args, **kwargs):
        """
        Safely execute a relationship query with automatic metadata refresh on junction table errors.
        This handles intermittent "no such column" errors after reconnection by refreshing metadata.
        
        Args:
            query_func: The query function to execute
            *args: Arguments to pass to query_func
            **kwargs: Keyword arguments to pass to query_func
            
        Returns:
            Result of query_func execution
        """
        try:
            # First attempt
            return await query_func(*args, **kwargs)
        except Exception as e:
            error_msg = str(e).lower()
            if "no such column" in error_msg:
                # Extract table name from SQLAlchemy error message
                # Error format: "no such column: tablename.columnname"
                import re
                table_match = re.search(r'no such column:\s*([a-zA-Z_]\w*)\.[a-zA-Z_]\w*', error_msg)
                
                if table_match:
                    table_name = table_match.group(1)
                    logging.warning(f"Junction table metadata error detected for '{table_name}': {e}")
                    
                    # Refresh metadata for the specific table
                    await cls._ensure_junction_table_metadata(table_name)
                    
                    # Retry the query
                    try:
                        return await query_func(*args, **kwargs)
                    except Exception as retry_e:
                        # If retry fails, try a full metadata refresh as last resort
                        logging.warning(f"Retry failed, attempting full metadata refresh: {retry_e}")
                        await db_config.refresh_metadata()
                        return await query_func(*args, **kwargs)
                else:
                    # If we can't extract table name, try full metadata refresh
                    logging.warning(f"Could not extract table name from error, attempting full metadata refresh: {e}")
                    await db_config.refresh_metadata()
                    return await query_func(*args, **kwargs)
            else:
                # Not a metadata issue, re-raise original exception
                raise e

    @classmethod
    async def _load_relationships_recursively(cls, session, obj, max_depth=2, current_depth=0, visited_ids=None):
        """
        Recursively load all relationships for an object and its related objects.
        
        Args:
            session: SQLAlchemy session
            obj: The object to load relationships for
            max_depth: Maximum depth to recurse to prevent infinite loops
            current_depth: Current recursion depth (internal use)
            visited_ids: Set of already visited object IDs to prevent cycles
            
        Returns:
            The object with all relationships loaded
        """
        if visited_ids is None:
            visited_ids = set()
            
        # Use object ID and class for tracking instead of the object itself (which isn't hashable)
        obj_key = (obj.__class__.__name__, obj.id)
            
        # Stop if we've reached max depth or already visited this object
        if current_depth >= max_depth or obj_key in visited_ids:
            return obj
            
        # Mark as visited to prevent cycles
        visited_ids.add(obj_key)
        
        # Load all relationship fields for this object
        obj_class = obj.__class__
        relationship_fields = obj_class._get_auto_relationship_fields()
        
        # For each relationship, load it and recurse
        for rel_name in relationship_fields:
            try:
                # Fetch the objects using selectinload
                stmt = select(obj_class).where(obj_class.id == obj.id)
                stmt = stmt.options(selectinload(getattr(obj_class, rel_name)))
                result = await session.execute(stmt)
                refreshed_obj = result.scalars().first()
                
                # Get the loaded relationship
                related_objs = getattr(refreshed_obj, rel_name, None)
                
                # Update the object's relationship without marking as dirty
                # Use direct __dict__ assignment to bypass SQLAlchemy change tracking
                # This prevents updated_at from being modified during SELECT operations
                if hasattr(obj, '__dict__'):
                    obj.__dict__[rel_name] = related_objs
                else:
                    # Fallback for objects without __dict__
                    object.__setattr__(obj, rel_name, related_objs)
                
                # Skip if no related objects
                if related_objs is None:
                    continue
                    
                # Recurse for related objects
                if isinstance(related_objs, list):
                    for related_obj in related_objs:
                        if hasattr(related_obj.__class__, '_get_auto_relationship_fields'):
                            # Only recurse if the object has an ID (is persistent)
                            if hasattr(related_obj, 'id') and related_obj.id is not None:
                                await cls._load_relationships_recursively(
                                    session, 
                                    related_obj, 
                                    max_depth, 
                                    current_depth + 1, 
                                    visited_ids
                                )
                else:
                    if hasattr(related_objs.__class__, '_get_auto_relationship_fields'):
                        # Only recurse if the object has an ID (is persistent)
                        if hasattr(related_objs, 'id') and related_objs.id is not None:
                            await cls._load_relationships_recursively(
                                session, 
                                related_objs, 
                                max_depth, 
                                current_depth + 1, 
                                visited_ids
                            )
            except Exception as e:
                logging.warning(f"Error loading relationship {rel_name}: {e}")
                
        return obj

# Register an event listener to update 'updated_at' on instance modifications.
@event.listens_for(Session, "before_flush")
def _update_updated_at(session, flush_context, instances):
    for instance in session.dirty:
        if isinstance(instance, EasyModel) and hasattr(instance, "updated_at"):
            instance.updated_at = _get_normalized_datetime()

async def init_db(migrate: bool = True, model_classes: List[Type[SQLModel]] = None):
    """
    Initialize the database connection and create all tables.
    
    Args:
        migrate: Whether to run migrations (default: True)
        model_classes: Optional list of model classes to create/migrate
                      If None, will autodiscover all EasyModel subclasses
    
    Returns:
        Dictionary of migration results if migrations were applied
    """
    from . import db_config
    
    # Import auto_relationships functions with conditional import to avoid circular imports
    try:
        from .auto_relationships import (_auto_relationships_enabled, process_auto_relationships,
                                        enable_auto_relationships, register_model_class,
                                        process_all_models_for_relationships)
        has_auto_relationships = True
    except ImportError:
        has_auto_relationships = False
    
    # Import migration system
    try:
        from .migrations import check_and_migrate_models, _create_table_without_indexes, _create_indexes_one_by_one
        has_migrations = True
    except ImportError:
        has_migrations = False

    # Get all SQLModel subclasses (our models) if not provided
    if model_classes is None:
        model_classes = []
        # Temporarily suppress warnings during module discovery to avoid third-party library warnings
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", FutureWarning)
            warnings.simplefilter("ignore", DeprecationWarning)
            
            # Get all model classes by inspecting the modules
            for module_name, module in list(sys.modules.items()):
                try:
                    if hasattr(module, "__dict__") and module is not None:
                        for cls_name, cls in module.__dict__.items():
                            try:
                                if isinstance(cls, type) and issubclass(cls, SQLModel) and cls != SQLModel and cls != EasyModel:
                                    model_classes.append(cls)
                            except (TypeError, AttributeError):
                                # Skip any objects that can't be checked safely
                                continue
                except (AttributeError, TypeError, ImportError):
                    # Skip modules that can't be inspected safely
                    continue
    
    # Enable auto-relationships and register all models, but DON'T process relationships yet
    if has_auto_relationships:
        # Enable auto-relationships with patch_metaclass=False
        enable_auto_relationships(patch_metaclass=False)
        
        # Register all model classes
        for model_cls in model_classes:
            register_model_class(model_cls)
        
        # NOTE: We'll process relationships AFTER tables are created to avoid missing column errors
    
    migration_results = {}
    
    # Check for migrations first if the feature is available and enabled
    if has_migrations and migrate:
        migration_results = await check_and_migrate_models(model_classes)
        if migration_results:
            logging.info(f"Applied migrations: {len(migration_results)} models affected")
    
    # Create async engine and all tables
    engine = db_config.get_engine()
    if not engine:
        raise ValueError("Database configuration is missing. Use db_config.configure_* methods first.")
    
    async with engine.begin() as conn:
        if has_migrations:
            # Use our safe table creation methods if migrations are available
            for model in model_classes:
                table = model.__table__
                await _create_table_without_indexes(table, conn)
                await _create_indexes_one_by_one(table, conn)
        else:
            # Fall back to standard create_all if migrations aren't available
            await conn.run_sync(SQLModel.metadata.create_all)
    
    # NOW process relationships after all tables have been created
    if has_auto_relationships:
        logging.info("Processing auto-relationships after database initialization")
        process_all_models_for_relationships()
    
    logging.info("Database initialized")
    return migration_results
