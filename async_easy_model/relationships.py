from typing import Optional, Any, List, TypeVar, Generic, Type, get_origin, get_args
from sqlmodel import Relationship as SQLModelRelationship

T = TypeVar('T')

class Relation(Generic[T]):
    """
    Enhanced relationship helper for async-easy-model.
    
    This class makes it easier to define relationships with proper type annotations.
    
    Example:
        ```python
        class Author(EasyModel, table=True):
            name: str
            books: Relation["Book"] = Relation.many("author")
        
        class Book(EasyModel, table=True):
            title: str
            author_id: Optional[int] = Field(default=None, foreign_key="author.id")
            author: Relation["Author"] = Relation.one("books")
        ```
    """
    
    def __init__(
        self,
        back_populates: str,
        link_model: Optional[Any] = None,
        sa_relationship: Optional[Any] = None,
        **kwargs: Any
    ):
        self.back_populates = back_populates
        self.link_model = link_model
        self.sa_relationship = sa_relationship
        self.kwargs = kwargs
    
    def __get__(self, instance, owner):
        if instance is None:
            return self
        # Return the actual relationship value when accessed on an instance
        return getattr(instance, self.back_populates)
    
    @classmethod
    def one(cls, back_populates: str, **kwargs) -> SQLModelRelationship:
        """
        Create a one-to-many relationship (from the 'one' side).
        
        Args:
            back_populates: Name of the attribute in the related model that refers back to this relationship
            **kwargs: Additional keyword arguments to pass to SQLAlchemy's relationship function
        
        Returns:
            A relationship object that can be used in a SQLModel class
        """
        return SQLModelRelationship(back_populates=back_populates, **kwargs)
    
    @classmethod
    def many(cls, back_populates: str, **kwargs) -> SQLModelRelationship:
        """
        Create a one-to-many relationship (from the 'many' side).
        
        Args:
            back_populates: Name of the attribute in the related model that refers back to this relationship
            **kwargs: Additional keyword arguments to pass to SQLAlchemy's relationship function
        
        Returns:
            A relationship object that can be used in a SQLModel class
        """
        return SQLModelRelationship(back_populates=back_populates, **kwargs)
    
    @classmethod
    def many_to_many(
        cls, 
        back_populates: str, 
        link_model: Any,
        **kwargs
    ) -> SQLModelRelationship:
        """
        Create a many-to-many relationship.
        
        Args:
            back_populates: Name of the attribute in the related model that refers back to this relationship
            link_model: The model that serves as the link between the two related models
            **kwargs: Additional keyword arguments to pass to SQLAlchemy's relationship function
        
        Returns:
            A relationship object that can be used in a SQLModel class
        """
        return SQLModelRelationship(
            back_populates=back_populates,
            link_model=link_model,
            **kwargs
        )
