from sqlmodel import SQLModel, Field, select, Relationship
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, Session, selectinload, joinedload
from sqlalchemy import update as sqlalchemy_update, event, desc, asc
from typing import Type, TypeVar, Optional, Any, List, Dict, Literal, Union, Set, Tuple
import contextlib
import os
import sys
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

    # Default table args with extend_existing=True to ensure all subclasses can redefine tables
    __table_args__ = {"extend_existing": True}

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
        include_relationships: bool = True,
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
        include_relationships: bool = True,
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
        include_relationships: bool = True,
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
    async def insert(cls: Type[T], data: Union[Dict[str, Any], List[Dict[str, Any]]], include_relationships: bool = True) -> Union[T, List[T]]:
        """
        Insert one or more records.
        
        Args:
            data: Dictionary of field values or a list of dictionaries for multiple records
            include_relationships: If True, return the instance(s) with relationships loaded
            
        Returns:
            The created model instance(s)
        """
        # Handle list of records
        if isinstance(data, list):
            objects = []
            async with cls.get_session() as session:
                for item in data:
                    try:
                        # Process relationships first
                        processed_item = await cls._process_relationships_for_insert(session, item)
                        
                        # Extract special _related_* fields for post-processing
                        related_fields = {}
                        for key in list(processed_item.keys()):
                            if key.startswith("_related_"):
                                rel_name = key[9:]  # Remove "_related_" prefix
                                related_fields[rel_name] = processed_item.pop(key)
                        
                        # Check if a record with unique constraints already exists
                        unique_fields = cls._get_unique_fields()
                        existing_obj = None
                        
                        if unique_fields:
                            unique_criteria = {field: processed_item[field] 
                                              for field in unique_fields 
                                              if field in processed_item}
                            
                            if unique_criteria:
                                # Try to find existing record with these unique values
                                statement = select(cls)
                                for field, value in unique_criteria.items():
                                    statement = statement.where(getattr(cls, field) == value)
                                result = await session.execute(statement)
                                existing_obj = result.scalars().first()
                        
                        if existing_obj:
                            # Update existing object with new values
                            for key, value in processed_item.items():
                                if key != 'id':  # Don't update ID
                                    setattr(existing_obj, key, value)
                            obj = existing_obj
                        else:
                            # Create new object
                            obj = cls(**processed_item)
                            session.add(obj)
                            
                        # Flush to get the ID for this object
                        await session.flush()
                        
                        # Now handle any one-to-many relationships
                        for rel_name, related_objects in related_fields.items():
                            # Check if the relationship attribute exists in the class (not the instance)
                            if hasattr(cls, rel_name):
                                # Get the relationship attribute from the class
                                rel_attr = getattr(cls, rel_name)
                                
                                # Check if it's a SQLAlchemy relationship
                                if hasattr(rel_attr, 'property') and hasattr(rel_attr.property, 'back_populates'):
                                    back_attr = rel_attr.property.back_populates
                                    
                                    # For each related object, set the back reference to this object
                                    for related_obj in related_objects:
                                        setattr(related_obj, back_attr, obj)
                                        # Make sure the related object is in the session
                                        session.add(related_obj)
                        
                        objects.append(obj)
                    except Exception as e:
                        logging.error(f"Error inserting record: {e}")
                        await session.rollback()
                        raise
                
                try:
                    await session.flush()
                    await session.commit()
                    
                    # Refresh with relationships if requested
                    if include_relationships:
                        for obj in objects:
                            await session.refresh(obj)
                except Exception as e:
                    logging.error(f"Error committing transaction: {e}")
                    await session.rollback()
                    raise
                        
                return objects
        else:
            # Single record case
            async with cls.get_session() as session:
                try:
                    # Process relationships first
                    processed_data = await cls._process_relationships_for_insert(session, data)
                    
                    # Extract special _related_* fields for post-processing
                    related_fields = {}
                    for key in list(processed_data.keys()):
                        if key.startswith("_related_"):
                            rel_name = key[9:]  # Remove "_related_" prefix
                            related_fields[rel_name] = processed_data.pop(key)
                    
                    # Check if a record with unique constraints already exists
                    unique_fields = cls._get_unique_fields()
                    existing_obj = None
                    
                    if unique_fields:
                        unique_criteria = {field: processed_data[field] 
                                          for field in unique_fields 
                                          if field in processed_data}
                        
                        if unique_criteria:
                            # Try to find existing record with these unique values
                            statement = select(cls)
                            for field, value in unique_criteria.items():
                                statement = statement.where(getattr(cls, field) == value)
                            result = await session.execute(statement)
                            existing_obj = result.scalars().first()
                    
                    if existing_obj:
                        # Update existing object with new values
                        for key, value in processed_data.items():
                            if key != 'id':  # Don't update ID
                                setattr(existing_obj, key, value)
                        obj = existing_obj
                    else:
                        # Create new object
                        obj = cls(**processed_data)
                        session.add(obj)
                    
                    await session.flush()  # Flush to get the ID
                    
                    # Now handle any one-to-many relationships
                    for rel_name, related_objects in related_fields.items():
                        # Check if the relationship attribute exists in the class (not the instance)
                        if hasattr(cls, rel_name):
                            # Get the relationship attribute from the class
                            rel_attr = getattr(cls, rel_name)
                            
                            # Check if it's a SQLAlchemy relationship
                            if hasattr(rel_attr, 'property') and hasattr(rel_attr.property, 'back_populates'):
                                back_attr = rel_attr.property.back_populates
                                
                                # For each related object, set the back reference to this object
                                for related_obj in related_objects:
                                    setattr(related_obj, back_attr, obj)
                                    # Make sure the related object is in the session
                                    session.add(related_obj)
                    
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
                except Exception as e:
                    logging.error(f"Error inserting record: {e}")
                    await session.rollback()
                    raise

    @classmethod
    def _get_unique_fields(cls) -> List[str]:
        """
        Get all fields with unique=True constraint
        
        Returns:
            List of field names that have unique constraints
        """
        unique_fields = []
        for name, field in cls.__fields__.items():
            if name != 'id' and hasattr(field, 'field_info') and field.field_info.extra.get('unique', False):
                unique_fields.append(name)
        return unique_fields

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
        import copy
        result = copy.deepcopy(data)
        
        # Get all relationship fields for this model
        relationship_fields = cls._get_auto_relationship_fields()
        
        # Get foreign key fields
        foreign_key_fields = []
        for field_name, field_info in cls.__fields__.items():
            if field_name.endswith("_id") and hasattr(field_info, "field_info"):
                if field_info.field_info.extra.get("foreign_key"):
                    foreign_key_fields.append(field_name)
        
        # Handle nested relationship objects
        for key, value in data.items():
            # Skip if None
            if value is None:
                continue
                
            # Check if this is a relationship field (either by name or derived from foreign key)
            is_rel_field = key in relationship_fields
            related_key = f"{key}_id"
            is_derived_rel = related_key in foreign_key_fields
            
            # If it's a relationship field or derived from a foreign key
            if is_rel_field or is_derived_rel or related_key in cls.__fields__:
                # Find the related model class
                related_model = None
                
                # Try to get the related model from the attribute
                if hasattr(cls, key) and hasattr(getattr(cls, key), 'property'):
                    # Get from relationship attribute
                    rel_attr = getattr(cls, key)
                    related_model = rel_attr.property.mapper.class_
                else:
                    # Try to find it from foreign key definition
                    fk_definition = None
                    for field_name, field_info in cls.__fields__.items():
                        if field_name == related_key and hasattr(field_info, "field_info"):
                            fk_definition = field_info.field_info.extra.get("foreign_key")
                            break
                    
                    if fk_definition:
                        # Parse foreign key definition (e.g. "users.id")
                        target_table, _ = fk_definition.split(".")
                        # Try to find the target model
                        from async_easy_model.auto_relationships import get_model_by_table_name, singularize_name
                        related_model = get_model_by_table_name(target_table)
                        if not related_model:
                            # Try with the singular form
                            singular_table = singularize_name(target_table)
                            related_model = get_model_by_table_name(singular_table)
                    else:
                        # Try to infer from field name (e.g., "user_id" -> Users)
                        base_name = related_key[:-3]  # Remove "_id"
                        from async_easy_model.auto_relationships import get_model_by_table_name, singularize_name, pluralize_name
                        
                        # Try singular and plural forms
                        related_model = get_model_by_table_name(base_name)
                        if not related_model:
                            plural_table = pluralize_name(base_name)
                            related_model = get_model_by_table_name(plural_table)
                        if not related_model:
                            singular_table = singularize_name(base_name)
                            related_model = get_model_by_table_name(singular_table)
                
                if not related_model:
                    logging.warning(f"Could not find related model for {key} in {cls.__name__}")
                    continue
                
                # Check if the value is a list (one-to-many) or dict (one-to-one)
                if isinstance(value, list):
                    # Handle one-to-many relationship (list of dictionaries)
                    related_objects = []
                    
                    for item in value:
                        if not isinstance(item, dict):
                            logging.warning(f"Skipping non-dict item in list for {key}")
                            continue
                            
                        related_obj = await cls._process_single_relationship_item(
                            session, related_model, item
                        )
                        if related_obj:
                            related_objects.append(related_obj)
                    
                    # For one-to-many, we need to keep a list of related objects to be attached later
                    # We'll store them in a special field that will be removed before creating the model
                    result[f"_related_{key}"] = related_objects
                    
                    # Remove the original field from the result
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
        for field_name, field_info in related_model.__fields__.items():
            if (hasattr(field_info, "field_info") and 
                field_info.field_info.extra.get('unique', False)):
                unique_fields.append(field_name)
        
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
                        field = getattr(cls.__fields__.get(field_name), 'field_info', None)
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
                
                # Apply the updates
                for key, value in data.items():
                    setattr(record, key, value)
                
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
                logging.error(f"Error updating record: {e}")
                await session.rollback()
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
                # Find the record(s) to delete
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
                
                # Get a list of related tables that might need to be cleared first
                # This helps with foreign key constraints
                relationship_fields = cls._get_auto_relationship_fields()
                to_many_relationships = []
                
                # Find to-many relationships that need to be handled first
                for rel_name in relationship_fields:
                    rel_attr = getattr(cls, rel_name, None)
                    if rel_attr and hasattr(rel_attr, 'property'):
                        # Check if this is a to-many relationship (one-to-many or many-to-many)
                        if hasattr(rel_attr.property, 'uselist') and rel_attr.property.uselist:
                            to_many_relationships.append(rel_name)
                
                # For each record, delete related records first (cascade delete)
                for record in records:
                    # First load all related collections
                    if to_many_relationships:
                        await session.refresh(record, attribute_names=to_many_relationships)
                    
                    # Delete related records in collections
                    for rel_name in to_many_relationships:
                        related_collection = getattr(record, rel_name, [])
                        if related_collection:
                            for related_item in related_collection:
                                await session.delete(related_item)
                    
                    # Now delete the main record
                    await session.delete(record)
                
                # Commit the changes
                await session.flush()
                await session.commit()
                
                return len(records)
            except Exception as e:
                logging.error(f"Error deleting records: {e}")
                await session.rollback()
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
        limit: Optional[int] = None
    ) -> Union[Optional[T], List[T]]:
        """
        Retrieve record(s) by matching attribute values.
        
        Args:
            criteria: Dictionary of search criteria
            all: If True, return all matching records, otherwise return only the first one
            first: If True, return only the first record (equivalent to all=False)
            include_relationships: If True, eagerly load all relationships
            order_by: Field(s) to order by. Can be a string or list of strings.
                     Prefix with '-' for descending order (e.g. '-created_at')
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
            
            # Apply criteria
            for field, value in criteria.items():
                if isinstance(value, str) and '*' in value:
                    # Handle LIKE queries (convert '*' wildcard to '%')
                    like_value = value.replace('*', '%')
                    statement = statement.where(getattr(cls, field).like(like_value))
                else:
                    # Regular equality check
                    statement = statement.where(getattr(cls, field) == value)
            
            # Apply ordering
            if order_by:
                statement = cls._apply_order_by(statement, order_by)
            
            # Apply limit
            if limit:
                statement = statement.limit(limit)
            
            # Include relationships if requested
            if include_relationships:
                for rel_name in cls._get_auto_relationship_fields():
                    statement = statement.options(selectinload(getattr(cls, rel_name)))
            
            # Execute the query
            result = await session.execute(statement)
            
            if all:
                # Return all results
                instances = result.scalars().all()
                
                # Materialize relationships if requested - this ensures they're fully loaded
                if include_relationships:
                    for instance in instances:
                        # For each relationship, access it once to ensure it's loaded
                        for rel_name in cls._get_auto_relationship_fields():
                            try:
                                # This will force loading the relationship while session is active
                                _ = getattr(instance, rel_name)
                            except Exception:
                                # Skip if the relationship can't be loaded
                                pass
                
                return instances
            else:
                # Return only the first result
                instance = result.scalars().first()
                
                # Materialize relationships if requested and instance exists
                if include_relationships and instance:
                    # For each relationship, access it once to ensure it's loaded
                    for rel_name in cls._get_auto_relationship_fields():
                        try:
                            # This will force loading the relationship while session is active
                            _ = getattr(instance, rel_name)
                        except Exception:
                            # Skip if the relationship can't be loaded
                            pass
                            
                return instance

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

# Register an event listener to update 'updated_at' on instance modifications.
@event.listens_for(Session, "before_flush")
def _update_updated_at(session, flush_context, instances):
    for instance in session.dirty:
        if isinstance(instance, EasyModel) and hasattr(instance, "updated_at"):
            instance.updated_at = datetime.now(tz.utc)

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
        # Get all model classes by inspecting the modules
        for module_name, module in sys.modules.items():
            if hasattr(module, "__dict__"):
                for cls_name, cls in module.__dict__.items():
                    if isinstance(cls, type) and issubclass(cls, SQLModel) and cls != SQLModel and cls != EasyModel:
                        model_classes.append(cls)
    
    # Enable auto-relationships and register all models
    if has_auto_relationships:
        # Enable auto-relationships with patch_metaclass=False
        enable_auto_relationships(patch_metaclass=False)
        
        # Register all model classes
        for model_cls in model_classes:
            register_model_class(model_cls)
        
        # Process relationships for all registered models
        process_all_models_for_relationships()
    
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
    
    logging.info("Database initialized")
    return migration_results
