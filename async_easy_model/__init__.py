"""
Async EasyModel: A simple, lightweight ORM for SQLModel with async support.
"""

import warnings
from sqlalchemy.exc import SAWarning

# Suppress SQLAlchemy relationship warnings globally for EasyModel users
warnings.filterwarnings('ignore', category=SAWarning)

from typing import Optional, Any
from .model import EasyModel, init_db, db_config
from sqlmodel import Field, Relationship as SQLModelRelationship

__version__ = "0.3.8"
__all__ = ["EasyModel", "init_db", "db_config", "Field", "Relationship", "Relation", "enable_auto_relationships", "disable_auto_relationships", "process_auto_relationships", "MigrationManager", "check_and_migrate_models", "ModelVisualizer"]

# Create a more user-friendly Relationship function
def Relationship(
    *,
    back_populates: Optional[str] = None,
    link_model: Optional[Any] = None,
    sa_relationship: Optional[Any] = None,
    **kwargs: Any,
) -> Any:
    """
    Define a relationship between two models.
    
    Args:
        back_populates: Name of the attribute on the related model that refers back to this relationship
        link_model: The model class that this relationship links to
        sa_relationship: SQLAlchemy relationship object
        **kwargs: Additional keyword arguments to pass to SQLModel's Relationship
        
    Returns:
        A SQLModel Relationship object
    """
    return SQLModelRelationship(
        back_populates=back_populates,
        link_model=link_model,
        sa_relationship=sa_relationship,
        **kwargs
    )

# Import the relationship helpers
from .relationships import Relation

# Import the automatic relationship features
from .auto_relationships import enable_auto_relationships, disable_auto_relationships, process_auto_relationships

# Add to __init__.py
from .migrations import MigrationManager, check_and_migrate_models

# Import the visualization helper
from .visualization import ModelVisualizer