"""
Support for automatic relationship detection and setup based on foreign key fields.
"""

import logging
import inflection
import re
from typing import Dict, List, Optional, Type, Any, Union, Set, get_type_hints, Tuple, ClassVar
from sqlmodel import Relationship, SQLModel, Field
from sqlalchemy import Column, ForeignKey, event
from sqlalchemy.orm import declared_attr, registry, relationship

# Import the required SQLModel internal classes for relationship metadata
from sqlmodel.main import RelationshipInfo, SQLModelMetaclass

# Set up logging
logger = logging.getLogger("auto_relationships")

# Global registry of models for relationship setup
_model_registry = {}
_auto_processed_models = set()
_auto_relationships_processed = False

# Flag to enable/disable automatic relationship detection
# Disabled by default and will be enabled during init_db
_auto_relationships_enabled = False

# Automatically disable auto-relationships at module import time
# This ensures models can be defined without immediate processing
def _disable_auto_relationships_on_import():
    # This will be automatically called when the module is imported
    global _auto_relationships_enabled
    _auto_relationships_enabled = False
    logger.info("Auto relationships disabled by default at import")

# Call the function immediately when this module is imported
_disable_auto_relationships_on_import()

def pluralize_name(name: str) -> str:
    """Convert a singular noun to its plural form."""
    # Check if the name already ends with 's'
    if name.endswith('s'):
        return name
    return inflection.pluralize(name)

def singularize_name(name: str) -> str:
    """Convert a plural noun to its singular form."""
    return inflection.singularize(name)

def get_related_name_from_foreign_key(fk_field_name: str) -> str:
    """
    Derive the relationship name from a foreign key field name.
    E.g., 'author_id' -> 'author'
    """
    if fk_field_name.endswith('_id'):
        return fk_field_name[:-3]  # Remove '_id' suffix
    return fk_field_name

def get_model_by_table_name(table_name: str) -> Optional[Type[SQLModel]]:
    """
    Get a model class by its table name.
    
    Args:
        table_name: The name of the table to find the model for.
    
    Returns:
        The model class, or None if not found.
    """
    # First check the registry
    if table_name in _model_registry:
        logger.info(f"Found model for {table_name} in registry")
        return _model_registry[table_name]
    
    # Check all registered models by their __tablename__ attribute
    for model_name, model_cls in _model_registry.items():
        if hasattr(model_cls, "__tablename__") and model_cls.__tablename__ == table_name:
            logger.info(f"Found model {model_cls.__name__} for table {table_name} by __tablename__")
            return model_cls
    
    # Case insensitive check as a fallback
    for model_name, model_cls in _model_registry.items():
        if model_name.lower() == table_name.lower():
            logger.info(f"Found model {model_cls.__name__} for table {table_name} by case-insensitive name")
            return model_cls
    
    logger.warning(f"Could not find model for table name: {table_name}")
    return None

def get_related_model_name_from_foreign_key(foreign_key: str) -> str:
    """
    Extract the related model name from a foreign key.
    
    Args:
        foreign_key: The foreign key string, typically in the format "table.field".
    
    Returns:
        The table name part of the foreign key.
    """
    if "." in foreign_key:
        return foreign_key.split(".")[0]
    return foreign_key

def snake_to_camel(name: str) -> str:
    """Convert snake_case to camelCase."""
    components = name.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])
    
def get_foreign_keys_from_model(model_cls: Type[SQLModel]) -> Dict[str, str]:
    """
    Extract foreign key fields from a SQLModel model.
    
    Args:
        model_cls: The SQLModel class to extract foreign keys from
        
    Returns:
        A dictionary where keys are field names and values are foreign key targets.
    """
    logger.info(f"Looking for foreign keys in model {model_cls.__name__}")
    
    foreign_keys = {}
    
    # First method: Check SQLModel's model_fields dictionary (Pydantic V2)
    if hasattr(model_cls, "model_fields"):
        logger.info(f"Using model_fields to find foreign keys in {model_cls.__name__}")
        for field_name, field_info in model_cls.model_fields.items():
            # Check if the field has a foreign_key attribute
            if hasattr(field_info, "foreign_key") and field_info.foreign_key:
                foreign_key = field_info.foreign_key
                # Skip PydanticUndefined values
                if str(foreign_key) == "PydanticUndefined":
                    continue
                logger.info(f"Found foreign key in field {field_name}: {foreign_key}")
                foreign_keys[field_name] = foreign_key
                continue
                
            # Try SQLModel's field extra
            if hasattr(field_info, "extra") and "foreign_key" in field_info.extra:
                foreign_key = field_info.extra["foreign_key"]
                # Skip PydanticUndefined values
                if str(foreign_key) == "PydanticUndefined":
                    continue
                logger.info(f"Found foreign key in field extras {field_name}: {foreign_key}")
                foreign_keys[field_name] = foreign_key
                continue
                
            # Check for 'sa_column' attribute
            if hasattr(field_info, "sa_column") and field_info.sa_column:
                sa_column = field_info.sa_column
                if hasattr(sa_column, "foreign_keys") and sa_column.foreign_keys:
                    for fk in sa_column.foreign_keys:
                        target = str(fk.target_fullname)
                        logger.info(f"Found foreign key in sa_column {field_name}: {target}")
                        foreign_keys[field_name] = target
                        break
    
    # Second method: Try to infer foreign keys from field names
    if not foreign_keys:
        logger.info(f"No foreign keys found in model {model_cls.__name__} metadata, trying to detect from field names")
        for field_name in getattr(model_cls, "model_fields", {}):
            if field_name.endswith("_id"):
                # Infer the referenced model from the field name
                model_name = field_name[:-3]  # Remove _id suffix
                # Try to find a registered model that matches this name
                for registered_name in _model_registry.keys():
                    if registered_name == model_name:
                        inferred_fk = f"{registered_name}.id"
                        logger.info(f"Inferred foreign key from field name: {field_name} -> {inferred_fk}")
                        foreign_keys[field_name] = inferred_fk
    
    # Filter out any remaining PydanticUndefined values
    foreign_keys = {k: v for k, v in foreign_keys.items() if str(v) != "PydanticUndefined"}
    
    logger.info(f"Found foreign keys for {model_cls.__name__}: {foreign_keys}")
    return foreign_keys

def setup_relationship_on_class(
    model_cls: Type[SQLModel], 
    relationship_name: str, 
    target_cls: Type[SQLModel], 
    back_populates: str,
    is_list: bool = False,
    through_model: Optional[Type[SQLModel]] = None
) -> None:
    """
    Properly set up a relationship on a SQLModel class that will be recognized by SQLModel.
    This function ensures the relationship is correctly registered for ORM use.
    """
    if hasattr(model_cls, relationship_name):
        logger.info(f"Relationship {relationship_name} already exists on {model_cls.__name__}")
        return
    
    logger.info(f"Setting up relationship {relationship_name} on {model_cls.__name__} -> {target_cls.__name__}")
    
    # Create the core SQLAlchemy relationship directly
    from sqlalchemy.orm import relationship as sa_relationship
    
    # Set up relationship arguments
    rel_args = {
        'back_populates': back_populates
    }
    
    if through_model:
        rel_args['secondary'] = through_model.__tablename__
    
    # Create the SQLAlchemy relationship
    rel_prop = sa_relationship(
        target_cls.__name__, 
        **rel_args,
        collection_class=list if is_list else None
    )
    
    # Set the relationship directly on the class
    setattr(model_cls, relationship_name, rel_prop)
    
    # Update the model's __annotations__ to include the relationship
    # This helps Pydantic with type checking
    if not hasattr(model_cls, "__annotations__"):
        model_cls.__annotations__ = {}
    
    if is_list:
        from typing import List as TypingList
        model_cls.__annotations__[relationship_name] = TypingList[target_cls]
    else:
        from typing import Optional
        model_cls.__annotations__[relationship_name] = Optional[target_cls]
    
    # Also add to SQLModel's internal registry
    if not hasattr(model_cls, "__sqlmodel_relationships__"):
        model_cls.__sqlmodel_relationships__ = {}
    
    model_cls.__sqlmodel_relationships__[relationship_name] = RelationshipInfo(
        back_populates=back_populates,
        link_model=target_cls
    )
    
    logger.info(f"Successfully set up relationship {relationship_name} on {model_cls.__name__}")

def setup_relationship_between_models(source_model, target_model, foreign_key_name, source_attr_name=None, target_attr_name=None):
    """
    Set up a bidirectional relationship between two models.
    
    Args:
        source_model: The model that has the foreign key.
        target_model: The model that the foreign key references.
        foreign_key_name: The name of the foreign key field in the source model.
        source_attr_name: The name to use for the relationship attribute in the source model.
                         If not provided, it will be derived from the target model name.
        target_attr_name: The name to use for the relationship attribute in the target model.
                         If not provided, it will be derived from the source model name.
    """
    # Get the table names
    source_table = getattr(source_model, "__tablename__")
    target_table = getattr(target_model, "__tablename__")
    
    # Determine attribute names if not provided
    if not source_attr_name:
        # By convention, the name of the to-one relationship is the name of the table without the _id suffix
        source_attr_name = foreign_key_name[:-3] if foreign_key_name.endswith("_id") else foreign_key_name
    
    if not target_attr_name:
        # By convention, the name of the to-many relationship is the pluralized name of the table
        # Use inflection to get the plural form, but remove any prefix from the source table name
        table_name_without_prefix = source_table.split('_')[-1] if '_' in source_table else source_table
        target_attr_name = inflection.pluralize(table_name_without_prefix)
    
    # Set up the to-one relationship on the source model
    logger.info(f"Setting up to-one relationship {source_model.__name__}.{source_attr_name} -> {target_model.__name__}")
    
    # Set up the to-many relationship on the target model
    logger.info(f"Setting up to-many relationship {target_model.__name__}.{target_attr_name} -> List[{source_model.__name__}]")
    
    # Check if relationships already exist (but don't check for type anymore)
    if hasattr(source_model, source_attr_name):
        # Check if it's a relationship descriptor or already set up with SQLAlchemy
        if hasattr(getattr(source_model, source_attr_name), 'prop'):
            logger.info(f"Relationship {source_attr_name} already exists on {source_model.__name__}")
            return
    
    logger.info(f"Setting up relationship {source_attr_name} on {source_model.__name__} -> {target_model.__name__}")
    
    # Create a SQLAlchemy relationship attribute for the source model (to-one)
    rel = relationship(
        target_model.__name__,
        back_populates=target_attr_name,
        uselist=False,
        foreign_keys=[getattr(source_model, foreign_key_name)]
    )
    
    # Add the relationship attribute to the source model
    setattr(source_model, source_attr_name, rel)
    
    # Register relationship in SQLModel metadata
    if not hasattr(source_model, "__sqlmodel_relationships__"):
        source_model.__sqlmodel_relationships__ = {}
    
    # Set the relationship metadata
    relationship_info = RelationshipInfo(
        back_populates=target_attr_name, 
        link_model=target_model
    )
    
    source_model.__sqlmodel_relationships__[source_attr_name] = relationship_info
    
    logger.info(f"Successfully set up relationship {source_attr_name} on {source_model.__name__}")
    
    # Check if relationships already exist (but don't check for type anymore)
    if hasattr(target_model, target_attr_name):
        # Check if it's a relationship descriptor or already set up with SQLAlchemy
        if hasattr(getattr(target_model, target_attr_name), 'prop'):
            logger.info(f"Relationship {target_attr_name} already exists on {target_model.__name__}")
            return
    
    logger.info(f"Setting up relationship {target_attr_name} on {target_model.__name__} -> {source_model.__name__}")
    
    # Create a SQLAlchemy relationship attribute for the target model (to-many)
    rel = relationship(
        source_model.__name__,
        back_populates=source_attr_name,
        uselist=True
    )
    
    # Add the relationship attribute to the target model
    setattr(target_model, target_attr_name, rel)
    
    # Register relationship in SQLModel metadata
    if not hasattr(target_model, "__sqlmodel_relationships__"):
        target_model.__sqlmodel_relationships__ = {}
    
    # Set the relationship metadata
    relationship_info = RelationshipInfo(
        back_populates=source_attr_name, 
        link_model=source_model
    )
    
    target_model.__sqlmodel_relationships__[target_attr_name] = relationship_info
    
    logger.info(f"Successfully set up relationship {target_attr_name} on {target_model.__name__}")

def process_all_models_for_relationships():
    """
    Process all registered models for relationships based on foreign keys.
    
    This function:
    1. Looks for foreign keys in all registered models
    2. Sets up relationships automatically based on those foreign keys
    3. Detects junction tables and sets up many-to-many relationships
    """
    logger.info(f"Processing relationships for all registered models: {list(_model_registry.keys())}")
    
    # First, gather all foreign keys for all models
    foreign_keys_map = {}
    junction_models = []
    
    for model_name, model_cls in _model_registry.items():
        logger.info(f"Processing model: {model_name}")
        foreign_keys = get_foreign_keys_from_model(model_cls)
        if foreign_keys:
            foreign_keys_map[model_name] = (model_cls, foreign_keys)
            
            # Check if this model represents a junction table
            if is_junction_table(model_cls):
                logger.info(f"Detected junction table: {model_name}")
                junction_models.append(model_cls)
            
    # Next, set up direct relationships using those foreign keys
    for model_name, (model_cls, foreign_keys) in foreign_keys_map.items():
        for field_name, target_fk in foreign_keys.items():
            # Parse target table and field
            target_table, target_field = target_fk.split(".")
            logger.info(f"Setting up relationship for {model_name}.{field_name} -> {target_table}.{target_field}")
            
            # Get the target model
            target_model = get_model_by_table_name(target_table)
            if target_model:
                logger.info(f"Found target model: {target_model.__name__}")
                # Set up the relationship
                setup_relationship_between_models(model_cls, target_model, field_name)
            else:
                logger.warning(f"Target model not found for {target_table}")
    
    # Finally, set up many-to-many relationships
    for junction_model in junction_models:
        logger.info(f"Processing junction table for many-to-many relationships: {junction_model.__name__}")
        setup_many_to_many_relationships(junction_model)
    
    logger.info("Finished processing relationships")

# Alias for backwards compatibility
process_auto_relationships = process_all_models_for_relationships

# Export the process_all_models_for_relationships function
process_auto_relationships = process_all_models_for_relationships

def register_model_class(cls: Type[SQLModel]) -> None:
    """
    Register a model class in the global registry.
    
    Args:
        cls: The SQLModel class to register.
    """
    if not hasattr(cls, '__tablename__'):
        logger.warning(f"Could not register model {cls.__name__}: no __tablename__ attribute")
        return
        
    table_name = cls.__tablename__
    _model_registry[table_name] = cls
    logger.info(f"Registered model {cls.__name__} with table name {table_name}")

# Monkey patch the SQLModel metaclass to register models
original_sqlmodel_new = None
_auto_relationships_enabled = False

def patched_sqlmodel_new(mcs, name, bases, namespace, **kwargs):
    """
    Patched version of SQLModel's __new__ method to automatically
    register all SQLModel classes.
    """
    # Call the original SQLModel.__new__ method
    cls = original_sqlmodel_new(mcs, name, bases, namespace, **kwargs)
    
    # Only register actual SQLModel classes with a table
    if 'table' in kwargs and kwargs['table']:
        register_model_class(cls)
        
        # Also try to find any defined foreign keys
        foreign_keys = get_foreign_keys_from_model(cls)
        if foreign_keys and _auto_relationships_enabled:
            logger.info(f"Found foreign keys in model {cls.__name__}: {foreign_keys}")
            
            # Process relationships immediately for this model
            for field_name, target_fk in foreign_keys.items():
                target_table = get_related_model_name_from_foreign_key(target_fk)
                target_model = get_model_by_table_name(target_table)
                
                if target_model:
                    logger.info(f"Setting up relationship for {cls.__name__}.{field_name} -> {target_model.__name__}")
                    setup_relationship_between_models(cls, target_model, field_name)
                else:
                    logger.warning(f"Target model not found for {target_table}")
    
    return cls

def enable_auto_relationships(patch_metaclass=False):
    """
    Enable automatic relationship detection for SQLModel models.
    This should be called before any models are defined.
    
    Args:
        patch_metaclass: Whether to patch SQLModel's metaclass to auto-register models.
                        Set to False to avoid conflicts with SQLModel's own relationship handling.
    """
    global _auto_relationships_enabled
    if _auto_relationships_enabled:
        logger.info("Automatic relationship detection already enabled")
        return
    
    _auto_relationships_enabled = True
    
    logger.info("Enabling automatic relationship detection")
    
    # Optionally patch SQLModel metaclass to register models
    if patch_metaclass:
        logger.info("Patching SQLModel metaclass for auto-registration")
        patch_sqlmodel_metaclass()
    
    # Automatically process relationships when db is initialized
    from async_easy_model.model import init_db as original_init_db
    
    async def patched_init_db(*args, **kwargs):
        """Patches the init_db function to process relationships after initialization."""
        result = await original_init_db(*args, **kwargs)
        
        # Process relationships after initialization
        logger.info("Processing auto-relationships after database initialization")
        process_all_models_for_relationships()
        
        return result
    
    # Replace the original init_db with our patched version
    import sys
    sys.modules['async_easy_model.model'].init_db = patched_init_db
    
    logger.info("Automatic relationship detection enabled")
    
def patch_sqlmodel_metaclass():
    global original_sqlmodel_new
    if original_sqlmodel_new is None:
        # Avoid double patching
        logger.info("Patching SQLModel metaclass")
        
        # Store the original SQLModel.__new__ method
        try:
            import sqlmodel.main as sqlmodel_main
            original_sqlmodel_new = sqlmodel_main.SQLModelMetaclass.__new__
            
            # Replace it with our patched version
            sqlmodel_main.SQLModelMetaclass.__new__ = patched_sqlmodel_new
            
            logger.info("SQLModel metaclass patched")
        except ImportError as e:
            logger.error(f"Failed to patch SQLModel metaclass: {e}")

def disable_auto_relationships():
    """
    Disable automatic relationship detection for SQLModel models.
    
    This function restores the original SQLModel metaclass behavior.
    """
    global _auto_relationships_enabled
    
    if not _auto_relationships_enabled:
        logger.info("Auto relationships already disabled")
        return
    
    logger.info("Disabling automatic relationship detection")
    
    # Restore original metaclass method
    if SQLModelMetaclass.__new__ is patched_sqlmodel_new:
        SQLModelMetaclass.__new__ = original_sqlmodel_new
    
    _auto_relationships_enabled = False
    
    return True

def setup_auto_relationships_for_model(model_cls):
    """
    Set up automatic relationships for a single model.
    
    Args:
        model_cls: The model class to process.
    """
    if not _auto_relationships_enabled:
        return
        
    logger.info(f"Setting up auto relationships for model {model_cls.__name__}")
    
    # Register the model first
    if hasattr(model_cls, "__tablename__"):
        register_model_class(model_cls)
    
    # Get foreign keys
    foreign_keys = get_foreign_keys_from_model(model_cls)
    if not foreign_keys:
        logger.info(f"No foreign keys found in model {model_cls.__name__}")
        return
        
    logger.info(f"Found foreign keys in model {model_cls.__name__}: {foreign_keys}")
    
    # Set up relationships for each foreign key
    for field_name, target_fk in foreign_keys.items():
        target_table = get_related_model_name_from_foreign_key(target_fk)
        target_model = get_model_by_table_name(target_table)
        
        if target_model:
            logger.info(f"Setting up relationship for {model_cls.__name__}.{field_name} -> {target_model.__name__}")
            try:
                setup_relationship_between_models(model_cls, target_model, field_name)
            except Exception as e:
                logger.error(f"Error setting up relationship: {e}")
        else:
            logger.warning(f"Target model not found for {target_table}")

def is_junction_table(model_cls: Type[SQLModel]) -> bool:
    """
    Determine if a model represents a junction table (many-to-many relationship).
    
    A junction table typically has:
    - Only foreign key fields (plus perhaps id, created_at, etc.)
    - Exactly two foreign keys pointing to different tables
    
    Args:
        model_cls: The model class to check
        
    Returns:
        True if the model appears to be a junction table, False otherwise
    """
    foreign_keys = get_foreign_keys_from_model(model_cls)
    
    # A junction table should have at least two foreign keys
    if len(foreign_keys) < 2:
        return False
    
    # Get the tables referenced by the foreign keys
    referenced_tables = set()
    for field_name, target_fk in foreign_keys.items():
        target_table = get_related_model_name_from_foreign_key(target_fk)
        referenced_tables.add(target_table)
    
    # A true junction table should reference at least two different tables
    # (some junction tables might have multiple FKs to the same table)
    if len(referenced_tables) < 2:
        return False
    
    # Check if all non-standard fields are foreign keys
    standard_fields = {'id', 'created_at', 'updated_at'}
    model_fields = set(getattr(model_cls, 'model_fields', {}).keys())
    non_standard_fields = model_fields - standard_fields
    foreign_key_fields = set(foreign_keys.keys())
    
    # Allow for a few extra fields beyond the foreign keys
    # Some junction tables might have additional metadata
    non_fk_fields = non_standard_fields - foreign_key_fields
    return len(non_fk_fields) <= 2  # Allow for up to 2 additional fields

def setup_many_to_many_relationships(junction_model: Type[SQLModel]) -> None:
    """
    Set up many-to-many relationships using a junction table.
    
    This creates relationships between the two entities connected by the junction table.
    For example, if we have Book, Tag, and BookTag, this would set up:
    - Book.tags -> List[Tag]
    - Tag.books -> List[Book]
    
    Args:
        junction_model: The junction model class (e.g., BookTag)
    """
    logger.info(f"Setting up many-to-many relationships for junction table: {junction_model.__name__}")
    
    # Get the foreign keys from the junction model
    foreign_keys = get_foreign_keys_from_model(junction_model)
    if len(foreign_keys) < 2:
        logger.warning(f"Junction table {junction_model.__name__} has fewer than 2 foreign keys")
        return
    
    # Get the models referenced by the foreign keys
    referenced_models = []
    for field_name, target_fk in foreign_keys.items():
        target_table = get_related_model_name_from_foreign_key(target_fk)
        target_model = get_model_by_table_name(target_table)
        if target_model:
            referenced_models.append((field_name, target_model))
        else:
            logger.warning(f"Could not find model for table {target_table}")
    
    # We need at least two different models for a many-to-many relationship
    if len(referenced_models) < 2:
        logger.warning(f"Junction table {junction_model.__name__} references fewer than 2 valid models")
        return
    
    # For each pair of models, set up the many-to-many relationship
    # For simplicity, we'll just use the first two models found
    model_a_field, model_a = referenced_models[0]
    model_b_field, model_b = referenced_models[1]
    
    # Determine relationship names
    # For model_a -> model_b relationship (e.g., Book.tags)
    model_a_to_b_name = pluralize_name(model_b.__tablename__)
    
    # For model_b -> model_a relationship (e.g., Tag.books)
    model_b_to_a_name = pluralize_name(model_a.__tablename__)
    
    logger.info(f"Setting up many-to-many: {model_a.__name__}.{model_a_to_b_name} <-> {model_b.__name__}.{model_b_to_a_name}")
    
    # Set up relationship from model_a to model_b (e.g., Book.tags)
    setup_relationship_on_class(
        model_cls=model_a,
        relationship_name=model_a_to_b_name,
        target_cls=model_b,
        back_populates=model_b_to_a_name,
        is_list=True,
        through_model=junction_model
    )
    
    # Set up relationship from model_b to model_a (e.g., Tag.books)
    setup_relationship_on_class(
        model_cls=model_b,
        relationship_name=model_b_to_a_name,
        target_cls=model_a,
        back_populates=model_a_to_b_name,
        is_list=True,
        through_model=junction_model
    )
    
    logger.info(f"Successfully set up many-to-many relationships for {junction_model.__name__}")
