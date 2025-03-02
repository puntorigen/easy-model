"""
Simple test for automatic relationship detection.
This test just focuses on verifying the relationship detection mechanism works,
without actually creating a database or inserting data.
"""

import os
import sys
from sqlmodel import Field, SQLModel, Relationship
from typing import List, Optional

# Add parent directory to path to import from async_easy_model
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from async_easy_model.model import EasyModel
from async_easy_model.auto_relationships import (
    process_all_models_for_relationships,
    get_foreign_keys_from_model,
    setup_relationship_between_models,
    register_model_class,
    enable_auto_relationships,
    get_model_by_table_name
)

# Enable auto relationships
enable_auto_relationships()

# 1. Define models with a Foreign Key relationship
class Author(EasyModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str

class Book(EasyModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    author_id: Optional[int] = Field(
        default=None, foreign_key="author.id", description="Foreign key to the author"
    )

# Debug function to inspect models
def inspect_model(model_cls):
    """Inspect a model and its relationships."""
    print(f"\n=== Inspecting {model_cls.__name__} ===")
    
    # Check for SQLAlchemy relationships
    if hasattr(model_cls, "_sa_relationship_props"):
        relationships = list(model_cls._sa_relationship_props.keys())
        print(f"Relationships: {relationships}")
        
        for rel_name in relationships:
            rel = model_cls._sa_relationship_props[rel_name]
            target = rel.mapper.class_.__name__ if rel.mapper else "None"
            back_populates = rel.back_populates
            print(f"  - {rel_name}: target={target}, back_populates='{back_populates}'")
    else:
        print("No SQLAlchemy relationships found")
    
    # Check SQLModel relationships
    if hasattr(model_cls, "__sqlmodel_relationships__"):
        sm_relationships = list(model_cls.__sqlmodel_relationships__.keys())
        print(f"SQLModel relationships: {sm_relationships}")
        
        for rel_name, rel_info in model_cls.__sqlmodel_relationships__.items():
            target = getattr(rel_info, 'link_model', None)
            target_name = target.__name__ if target else "None"
            back_populates = getattr(rel_info, 'back_populates', None)
            print(f"  - {rel_name}: target={target_name}, back_populates='{back_populates}'")
    else:
        print("No SQLModel relationships found")
    
    # Check for foreign keys
    foreign_keys = get_foreign_keys_from_model(model_cls)
    if foreign_keys:
        print(f"Foreign keys: {foreign_keys}")
    else:
        print("No foreign keys found")

def main():
    """Test automatic relationship detection."""
    print("Testing automatic relationship detection...")
    
    # Register models manually to ensure they're in the registry
    register_model_class(Author)
    register_model_class(Book)
    
    # Verify the models are registered
    print("\n=== Model Registry ===")
    author_model = get_model_by_table_name("author")
    book_model = get_model_by_table_name("book")
    print(f"Author from registry: {author_model.__name__ if author_model else 'Not found'}")
    print(f"Book from registry: {book_model.__name__ if book_model else 'Not found'}")
    
    # First, inspect models before processing
    print("\n=== Before Processing ===")
    inspect_model(Author)
    inspect_model(Book)
    
    # Process all models for relationships
    print("\n=== Using process_all_models_for_relationships ===")
    process_all_models_for_relationships()
    
    # Inspect models after processing
    print("\n=== After Automatic Processing ===")
    inspect_model(Author)
    inspect_model(Book)
    
    # Try direct relationship setup if automatic didn't work
    if not hasattr(Book, "author") or not hasattr(Author, "books"):
        print("\n=== Manual Relationship Setup ===")
        # Try direct approach
        setup_relationship_between_models(Book, Author, "author_id")
        
        # Inspect again
        print("\n=== After Manual Setup ===")
        inspect_model(Author)
        inspect_model(Book)
    
    # Try to access the relationships directly
    print("\n=== Relationship Access Test ===")
    if hasattr(Book, "author"):
        print("Book.author relationship exists")
    else:
        print("Book.author relationship DOES NOT exist")
        
    if hasattr(Author, "books"):
        print("Author.books relationship exists")
    else:
        print("Author.books relationship DOES NOT exist")

if __name__ == "__main__":
    main()
