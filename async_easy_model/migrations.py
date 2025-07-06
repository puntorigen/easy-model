import json
import os
import inspect
import logging
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Type, Optional, Any, Tuple
from sqlalchemy import inspect as sa_inspect, Column, Table, MetaData, text, create_engine
from sqlalchemy.schema import CreateTable, DropTable
from sqlalchemy.ext.asyncio import AsyncConnection
from sqlmodel import SQLModel, Field

# Hidden directory for storing migration information
MIGRATIONS_DIR = '.easy_model_migrations'
MODEL_HASHES_FILE = 'model_hashes.json'
MIGRATIONS_HISTORY_FILE = 'migration_history.json'

def _get_sqlite_type(sqla_type):
    """
    Convert SQLAlchemy type to SQLite type for ALTER TABLE statements.
    
    Args:
        sqla_type: SQLAlchemy type object or string representation
        
    Returns:
        SQLite type string
    """
    type_map = {
        "INTEGER": "INTEGER",
        "BIGINT": "INTEGER",
        "SMALLINT": "INTEGER",
        "VARCHAR": "TEXT",
        "NVARCHAR": "TEXT",
        "TEXT": "TEXT", 
        "BOOLEAN": "BOOLEAN",
        "FLOAT": "REAL",
        "REAL": "REAL",
        "NUMERIC": "NUMERIC",
        "DECIMAL": "NUMERIC",
        "TIMESTAMP": "TIMESTAMP",
        "DATETIME": "DATETIME",
        "DATE": "DATE",
        "JSON": "TEXT"  # Handle JSON type
    }
    
    # Get type name - handle both string and type objects
    if isinstance(sqla_type, str):
        type_name = sqla_type.upper()
    else:
        type_name = sqla_type.__class__.__name__.upper()
    
    # Try to match with SQLite type
    for key in type_map:
        if key in type_name:
            return type_map[key]
    
    # Default to TEXT if no match found
    return "TEXT"

async def _create_table_without_indexes(table, connection):
    """
    Create a table without creating its indexes.
    
    Args:
        table: SQLAlchemy Table object
        connection: AsyncConnection
    """
    # Create a copy of the table without indexes
    metadata = MetaData()
    # Manually create columns instead of using deprecated copy() method
    new_columns = []
    for col in table.columns:
        new_col = Column(
            col.name,
            col.type,
            nullable=col.nullable,
            default=col.default,
            server_default=col.server_default,
            primary_key=col.primary_key,
            unique=col.unique,
            autoincrement=col.autoincrement,
            comment=col.comment
        )
        new_columns.append(new_col)
    
    new_table = Table(
        table.name,
        metadata,
        *new_columns,
        schema=table.schema
    )
    
    # Create the table
    await connection.run_sync(lambda sync_conn: new_table.create(sync_conn, checkfirst=True))

async def _create_indexes_one_by_one(table, connection):
    """
    Create indexes one by one, ignoring errors if they already exist.
    
    Args:
        table: SQLAlchemy Table object
        connection: AsyncConnection
    """
    for index in table.indexes:
        try:
            await connection.run_sync(lambda sync_conn: index.create(sync_conn))
            logging.info(f"Created index {index.name}")
        except Exception as e:
            if "already exists" in str(e):
                logging.warning(f"Index {index.name} already exists, skipping")
            else:
                raise

def _serialize_column(column: Column) -> Dict[str, Any]:
    """
    Convert a SQLAlchemy Column object to a JSON-serializable dictionary.
    
    Args:
        column: SQLAlchemy Column object to serialize
        
    Returns:
        Dictionary containing serializable column information
    """
    column_data = {
        "name": column.name,
        "type": str(column.type),
        "nullable": column.nullable,
        "primary_key": column.primary_key,
        "unique": column.unique,
        "autoincrement": column.autoincrement,
        "comment": column.comment
    }
    
    # Handle default values
    if column.default is not None:
        if hasattr(column.default, 'arg'):
            column_data["default"] = column.default.arg
        else:
            column_data["default"] = str(column.default)
    
    # Handle server defaults
    if column.server_default is not None:
        column_data["server_default"] = str(column.server_default)
    
    return column_data

class MigrationManager:
    """Manages schema migrations for EasyModel classes."""
    
    def __init__(self, base_dir: str = None):
        """
        Initialize the migration manager.
        
        Args:
            base_dir: Base directory for storing migration files. Defaults to current directory.
        """
        self.base_dir = base_dir or os.getcwd()
        self.migrations_dir = Path(self.base_dir) / MIGRATIONS_DIR
        self.models_hash_file = self.migrations_dir / MODEL_HASHES_FILE
        self.history_file = self.migrations_dir / MIGRATIONS_HISTORY_FILE
        self._ensure_migrations_dir()
        
    def _ensure_migrations_dir(self) -> None:
        """Ensure the migrations directory exists."""
        if not self.migrations_dir.exists():
            self.migrations_dir.mkdir(parents=True)
            # Create empty files for model hashes and migration history
            self.models_hash_file.write_text(json.dumps({}))
            self.history_file.write_text(json.dumps({"migrations": []}))
            
    def _get_model_hash(self, model_class: Type[SQLModel]) -> str:
        """
        Generate a hash for a model class based on its structure.
        
        Args:
            model_class: SQLModel class to hash
        
        Returns:
            A string hash representing the model's structure
        """
        model_dict = {
            "name": model_class.__name__,
            "tablename": getattr(model_class, "__tablename__", None),
            "columns": {}
        }
        
        # Get table from model
        table = model_class.__table__
        
        # Process columns
        for name, column in table.columns.items():
            col_dict = {
                "type": str(column.type),
                "nullable": column.nullable,
                "default": str(column.default) if column.default is not None else None,
                "primary_key": column.primary_key,
                "foreign_keys": [str(fk) for fk in column.foreign_keys] if column.foreign_keys else [],
                "unique": column.unique
            }
            model_dict["columns"][name] = col_dict
        
        # Process indexes
        if hasattr(table, "indexes"):
            indexes = []
            for idx in table.indexes:
                idx_dict = {
                    "name": idx.name,
                    "columns": [col.name for col in idx.columns],
                    "unique": idx.unique
                }
                indexes.append(idx_dict)
            model_dict["indexes"] = indexes
        
        # Relationships
        if hasattr(model_class, "__sqlmodel_relationships__"):
            relationships = {}
            for rel_name, rel_info in model_class.__sqlmodel_relationships__.items():
                # Safely extract relationship information
                rel_dict = {
                    "back_populates": getattr(rel_info, "back_populates", None),
                    "sa_relationship_args": str(getattr(rel_info, "sa_relationship_args", {}))
                }
                
                # Handle target model differently based on available attributes
                if hasattr(rel_info, "argument"):
                    target = rel_info.argument
                    if hasattr(target, "__name__"):
                        rel_dict["target"] = target.__name__
                    else:
                        rel_dict["target"] = str(target)
                else:
                    # Try to extract information from other attributes
                    if hasattr(rel_info, "_relationship_args"):
                        args = rel_info._relationship_args
                        if args and len(args) > 0:
                            rel_dict["target"] = str(args[0])
                    else:
                        rel_dict["target"] = "unknown"
                
                # Handle link_model
                if hasattr(rel_info, "link_model") and rel_info.link_model:
                    if hasattr(rel_info.link_model, "__name__"):
                        rel_dict["link_model"] = rel_info.link_model.__name__
                    else:
                        rel_dict["link_model"] = str(rel_info.link_model)
                else:
                    rel_dict["link_model"] = None
                
                relationships[rel_name] = rel_dict
                
            model_dict["relationships"] = relationships
        
        # Generate JSON string and hash it
        model_json = json.dumps(model_dict, sort_keys=True)
        return hashlib.sha256(model_json.encode()).hexdigest()
    
    def _load_model_hashes(self) -> Dict[str, str]:
        """Load stored model hashes from file."""
        if not self.models_hash_file.exists():
            return {}
        
        try:
            return json.loads(self.models_hash_file.read_text())
        except json.JSONDecodeError:
            logging.warning(f"Invalid JSON in {self.models_hash_file}, starting with empty hashes")
            return {}
            
    def _save_model_hashes(self, hashes: Dict[str, str]) -> None:
        """Save model hashes to file."""
        self.models_hash_file.write_text(json.dumps(hashes, indent=2))
        
    def _record_migration(self, model_name: str, changes: List[Dict[str, Any]]) -> None:
        """
        Record a migration in the history file.
        
        Args:
            model_name: Name of the model being migrated
            changes: List of changes applied
        """
        if not self.history_file.exists():
            history = {"migrations": []}
        else:
            try:
                history = json.loads(self.history_file.read_text())
            except json.JSONDecodeError:
                history = {"migrations": []}
                
        history["migrations"].append({
            "timestamp": datetime.now().isoformat(),
            "model": model_name,
            "changes": changes
        })
        
        self.history_file.write_text(json.dumps(history, indent=2))
        
    async def detect_model_changes(self, models: List[Type[SQLModel]]) -> Dict[str, Dict[str, Any]]:
        """
        Detect changes in model definitions compared to stored hashes.
        
        Args:
            models: List of SQLModel classes to check
            
        Returns:
            Dictionary mapping model names to their change status
        """
        stored_hashes = self._load_model_hashes()
        changes = {}
        
        for model in models:
            model_name = model.__name__
            current_hash = self._get_model_hash(model)
            
            if model_name not in stored_hashes:
                changes[model_name] = {
                    "status": "new",
                    "hash": current_hash
                }
            elif stored_hashes[model_name] != current_hash:
                changes[model_name] = {
                    "status": "modified",
                    "old_hash": stored_hashes[model_name],
                    "new_hash": current_hash
                }
                
        return changes
    
    async def generate_migration_plan(self, model: Type[SQLModel], connection: AsyncConnection) -> List[Dict[str, Any]]:
        """
        Generate a migration plan for a model.
        
        Args:
            model: The model to generate migrations for
            connection: SQLAlchemy async connection to use
            
        Returns:
            List of migration operations to perform
        """
        operations = []
        
        # Get inspector for database introspection
        inspector = await connection.run_sync(lambda sync_conn: sa_inspect(sync_conn))
        
        # Get table name from model
        table_name = model.__tablename__
        
        # Check if table exists
        table_exists = await connection.run_sync(lambda sync_conn: inspector.has_table(table_name))
        
        if not table_exists:
            # If table doesn't exist, create it with all columns
            operations.append({
                "operation": "create_table",
                "table_name": table_name
            })
        else:
            # If table exists, check for new columns
            existing_columns = await connection.run_sync(lambda sync_conn: inspector.get_columns(table_name))
            existing_column_names = [col['name'] for col in existing_columns]
            
            # Get column objects from model's __table__
            model_columns = model.__table__.columns
            
            # Add columns that don't exist yet
            for col_name, column in model_columns.items():
                if col_name not in existing_column_names:
                    operations.append({
                        "operation": "add_column",
                        "table_name": table_name,
                        "column_name": col_name,
                        "column_data": _serialize_column(column)
                    })
        
        return operations
    
    async def apply_migration(self, model: Type[SQLModel], operations: List[Dict[str, Any]], connection: AsyncConnection) -> None:
        """
        Apply migration operations to the database.
        
        Args:
            model: The model being migrated
            operations: List of migration operations to perform
            connection: SQLAlchemy async connection to use for executing migrations
        """
        applied_changes = []
        
        for op in operations:
            try:
                if op["operation"] == "create_table":
                    # Create table but handle indexes separately to avoid conflicts
                    table = model.__table__
                    
                    # First create the table structure without indexes
                    await _create_table_without_indexes(table, connection)
                    logging.info(f"Created table structure: {op['table_name']}")
                    
                    # Then create indexes one by one, handling "already exists" errors
                    await _create_indexes_one_by_one(table, connection)
                    
                    applied_changes.append(op)
                    
                elif op["operation"] == "add_column":
                    # Add column to existing table
                    table_name = op["table_name"]
                    column_data = op["column_data"]
                    col_name = op["column_name"]
                    
                    # Check if column already exists
                    inspector = await connection.run_sync(lambda sync_conn: sa_inspect(sync_conn))
                    existing_columns = await connection.run_sync(lambda sync_conn: inspector.get_columns(table_name))
                    existing_column_names = [col['name'] for col in existing_columns]
                    
                    if col_name in existing_column_names:
                        logging.info(f"Column {col_name} already exists in table {table_name}, skipping")
                        applied_changes.append(op)
                        continue
                    
                    # Get SQLite type for the column
                    col_type = _get_sqlite_type(column_data["type"])
                    
                    # Prepare nullable constraint
                    nullable = "" if column_data["nullable"] else "NOT NULL"
                    
                    # Prepare default value
                    default = ""
                    if "default" in column_data and column_data["default"] is not None:
                        if isinstance(column_data["default"], str):
                            default = f"DEFAULT '{column_data['default']}'"
                        else:
                            default = f"DEFAULT {column_data['default']}"
                    
                    # Create SQLite-compatible ALTER TABLE statement
                    alter_stmt = f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type} {nullable} {default}"
                    await connection.execute(text(alter_stmt.strip()))
                    
                    logging.info(f"Added column {col_name} to table {table_name}")
                    applied_changes.append(op)
            
            except Exception as e:
                error_msg = str(e)
                logging.error(f"Error applying migration operation {op['operation']}: {error_msg}")
                
                # Handle expected errors
                if "already exists" in error_msg:
                    # Skip errors for objects that already exist
                    logging.warning(f"Ignoring 'already exists' error: {error_msg}")
                    applied_changes.append(op)
                else:
                    raise
        
        # Record the migration in history
        if applied_changes:
            self._record_migration(model.__name__, applied_changes)
            
            # Update model hash
            hashes = self._load_model_hashes()
            hashes[model.__name__] = self._get_model_hash(model)
            self._save_model_hashes(hashes)

    async def migrate_models(self, models: List[Type[SQLModel]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Check for changes and migrate all models if needed.
        
        Args:
            models: List of SQLModel classes to migrate
            
        Returns:
            Dictionary mapping model names to lists of applied migration operations
        """
        from async_easy_model.model import db_config
        
        changes = await self.detect_model_changes(models)
        results = {}
        
        if not changes:
            return results
            
        engine = db_config.get_engine()
        async with engine.begin() as connection:
            for model_name, change_info in changes.items():
                if change_info["status"] in ["new", "modified"]:
                    # Find the model class
                    model = next((m for m in models if m.__name__ == model_name), None)
                    if model:
                        try:
                            operations = await self.generate_migration_plan(model, connection)
                            if operations:
                                await self.apply_migration(model, operations, connection)
                                results[model_name] = operations
                        except Exception as e:
                            logging.error(f"Error migrating model {model_name}: {str(e)}")
                            raise
        
        return results

# Function to register with the EasyModel system
async def check_and_migrate_models(models: List[Type[SQLModel]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Check for model changes and apply migrations if needed.
    
    Args:
        models: List of SQLModel classes to check and migrate
        
    Returns:
        Dictionary of applied migrations
    """
    migration_manager = MigrationManager()
    return await migration_manager.migrate_models(models)