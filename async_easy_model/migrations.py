import hashlib
import json
import os
import inspect
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Type, Optional, Any, Tuple
from sqlalchemy import inspect as sa_inspect, Column, Table, MetaData
from sqlalchemy.schema import CreateTable, DropTable, AddColumn, DropColumn, AlterColumn
from sqlalchemy.ext.asyncio import AsyncConnection
from sqlmodel import SQLModel, Field

# Hidden directory for storing migration information
MIGRATIONS_DIR = '.easy_model_migrations'
MODEL_HASHES_FILE = 'model_hashes.json'
MIGRATIONS_HISTORY_FILE = 'migration_history.json'

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
        # Get model attributes relevant to the database schema
        model_dict = {}
        
        # Table name
        table_name = model_class.__tablename__
        model_dict["table_name"] = table_name
        
        # Fields
        fields = {}
        for name, column in model_class.__table__.columns.items():
            field_info = {
                "type": str(column.type),
                "nullable": column.nullable,
                "primary_key": column.primary_key,
                "default": str(column.default) if column.default is not None else None,
                "unique": column.unique,
                "foreign_keys": [str(fk) for fk in column.foreign_keys] if column.foreign_keys else []
            }
            fields[name] = field_info
            
        model_dict["fields"] = fields
        
        # Relationships
        if hasattr(model_class, "__sqlmodel_relationships__"):
            relationships = {}
            for rel_name, rel_info in model_class.__sqlmodel_relationships__.items():
                rel_dict = {
                    "target": rel_info.argument.__name__ if hasattr(rel_info.argument, "__name__") else str(rel_info.argument),
                    "back_populates": rel_info.back_populates,
                    "link_model": rel_info.link_model.__name__ if rel_info.link_model else None,
                    "sa_relationship_args": str(rel_info.sa_relationship_args)
                }
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
        Generate a plan for migrating a model.
        
        Args:
            model: The model class to generate a migration plan for
            connection: SQLAlchemy async connection to use for introspection
            
        Returns:
            List of migration operations to perform
        """
        # Get current database schema for the table
        table_name = model.__tablename__
        inspector = await connection.run_sync(lambda sync_conn: sa_inspect(sync_conn))
        
        if not await connection.run_sync(lambda sync_conn: inspector.has_table(table_name)):
            # Table doesn't exist, create it
            return [{
                "operation": "create_table",
                "table_name": table_name
            }]
            
        # Table exists, check for column changes
        db_columns = await connection.run_sync(lambda sync_conn: {
            col["name"]: col for col in inspector.get_columns(table_name)
        })
        
        model_columns = {name: column for name, column in model.__table__.columns.items()}
        
        operations = []
        
        # Find columns to add (in model but not in DB)
        for name, column in model_columns.items():
            if name not in db_columns:
                operations.append({
                    "operation": "add_column",
                    "table_name": table_name,
                    "column_name": name,
                    "column_type": str(column.type),
                    "nullable": column.nullable
                })
            else:
                # Check for column modifications
                db_col = db_columns[name]
                # This is a simplified check - in a full implementation you'd compare more attributes
                if str(column.type) != str(db_col["type"]):
                    operations.append({
                        "operation": "alter_column",
                        "table_name": table_name,
                        "column_name": name,
                        "old_type": str(db_col["type"]),
                        "new_type": str(column.type)
                    })
        
        # Find columns to drop (in DB but not in model)
        for name in db_columns:
            if name not in model_columns:
                operations.append({
                    "operation": "drop_column",
                    "table_name": table_name,
                    "column_name": name
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
        metadata = MetaData()
        
        for op in operations:
            if op["operation"] == "create_table":
                # Create table using model's __table__ definition
                table_def = model.__table__
                create_stmt = CreateTable(table_def)
                await connection.execute(create_stmt)
                applied_changes.append(op)
                
            elif op["operation"] == "add_column":
                # Add column to existing table
                table = Table(op["table_name"], metadata)
                column_def = None
                
                # Find the column definition from the model
                for name, column in model.__table__.columns.items():
                    if name == op["column_name"]:
                        column_def = column
                        break
                
                if column_def:
                    add_stmt = AddColumn(op["table_name"], column_def)
                    await connection.execute(add_stmt)
                    applied_changes.append(op)
                    
            elif op["operation"] == "alter_column":
                # Alter column type - this is simplified
                # In real implementation, you'd create appropriate ALTER TABLE statements
                # based on your specific database (PostgreSQL, SQLite, etc.)
                # This is one area where Alembic has a lot of complexity
                table = op["table_name"]
                column = op["column_name"]
                new_type = op["new_type"]
                
                # This is a placeholder - actual implementation depends on database type
                alter_stmt = f"ALTER TABLE {table} ALTER COLUMN {column} TYPE {new_type}"
                await connection.execute(alter_stmt)
                applied_changes.append(op)
                
            elif op["operation"] == "drop_column":
                # Drop column from table
                table = op["table_name"]
                column = op["column_name"]
                
                drop_stmt = DropColumn(table, Column(column))
                await connection.execute(drop_stmt)
                applied_changes.append(op)
        
        # Record the migration in history
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
        from ..model import db_config  # Import here to avoid circular imports
        
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
                        operations = await self.generate_migration_plan(model, connection)
                        if operations:
                            await self.apply_migration(model, operations, connection)
                            results[model_name] = operations
        
        return results

# Function to register with the EasyModel system
async def check_and_migrate_models(models: List[Type[SQLModel]]) -> None:
    """
    Check for model changes and apply migrations if needed.
    
    Args:
        models: List of SQLModel classes to check and migrate
    """
    migration_manager = MigrationManager()
    await migration_manager.migrate_models(models)