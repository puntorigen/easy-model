from .model import EasyModel, init_db, db_config
from sqlmodel import Field, Relationship as SQLModelRelationship
from typing import Optional, Any

# Re-export Field directly
__version__ = "0.0.6"
__all__ = ["EasyModel", "init_db", "db_config", "Field", "Relationship", "Relation"]

# Create a more user-friendly Relationship function
def Relationship(
    *,
    back_populates: Optional[str] = None,
    link_model: Optional[Any] = None,
    sa_relationship: Optional[Any] = None,
    **kwargs: Any,
) -> Any:
    """
    A more convenient wrapper around SQLModel's Relationship function.
    
    This makes it easier to define relationships in async-easy-model models.
    
    Args:
        back_populates: Name of the attribute in the related model that refers back to this relationship
        link_model: For many-to-many relationships, specify the linking model
        sa_relationship: Pass custom SQLAlchemy relationship options
        **kwargs: Additional keyword arguments to pass to SQLAlchemy's relationship function
        
    Returns:
        A relationship object that can be used in a SQLModel class
    """
    return SQLModelRelationship(
        back_populates=back_populates,
        link_model=link_model,
        sa_relationship=sa_relationship,
        **kwargs
    )

# Import the enhanced relationship helpers
from .relationships import Relation
