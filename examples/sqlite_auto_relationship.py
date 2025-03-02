"""
Test of automatic relationship detection using SQLite.
"""

import os
import asyncio
import sys
from sqlmodel import Field, SQLModel, Relationship
from typing import List, Optional
import logging

# Configure logging to see debug messages
logging.basicConfig(level=logging.INFO)

# Ensure we're using the local package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from async_easy_model.model import EasyModel, init_db, db_config
from async_easy_model.auto_relationships import (
    enable_auto_relationships, 
    process_all_models_for_relationships,
    get_foreign_keys_from_model,
    setup_relationship_between_models,
    register_model_class
)

# Explicitly configure SQLite
db_config.configure_sqlite("./test_auto_rel.db")

# Enable auto-relationships
enable_auto_relationships()

# Define models and explicitly define the foreign key
class Author(EasyModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    
    # Define relationship with Relationship (explicit approach)
    books: List["Book"] = Relationship(back_populates="author")

class Book(EasyModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    author_id: Optional[int] = Field(
        default=None, foreign_key="author.id", description="Foreign key to the author"
    )
    
    # Define relationship with Relationship (explicit approach)
    author: Optional[Author] = Relationship(back_populates="books")

# Manual registration
register_model_class(Book)
register_model_class(Author)

# Manually check and print foreign keys
def debug_foreign_keys():
    book_fks = get_foreign_keys_from_model(Book)
    print(f"Book foreign keys: {book_fks}")
    
    author_fks = get_foreign_keys_from_model(Author)
    print(f"Author foreign keys: {author_fks}")

async def run_test():
    """Run the auto-relationship test with SQLite."""
    print(f"Using database: {db_config.get_connection_url()}")
    
    # Debug foreign keys
    print("\n=== Debug Foreign Keys ===")
    debug_foreign_keys()
    
    # Initialize database
    await init_db()
    
    # Create tables
    engine = db_config.get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)
    
    # Check for relationships
    print("\n=== Checking relationships after model setup ===")
    if hasattr(Book, "__sqlmodel_relationships__"):
        for rel_name, rel_info in Book.__sqlmodel_relationships__.items():
            target = getattr(rel_info, 'link_model', None)
            target_name = target.__name__ if target else "None"
            back_populates = getattr(rel_info, 'back_populates', None)
            print(f"Book.{rel_name}: target={target_name}, back_populates='{back_populates}'")
    else:
        print("No relationships found on Book")
        
    if hasattr(Author, "__sqlmodel_relationships__"):
        for rel_name, rel_info in Author.__sqlmodel_relationships__.items():
            target = getattr(rel_info, 'link_model', None)
            target_name = target.__name__ if target else "None"
            back_populates = getattr(rel_info, 'back_populates', None)
            print(f"Author.{rel_name}: target={target_name}, back_populates='{back_populates}'")
    else:
        print("No relationships found on Author")
        
    # Check SQLAlchemy relationship properties
    print("\n=== Checking SQLAlchemy relationships ===")
    if hasattr(Book, "_sa_relationship_props"):
        print(f"Book SA relationships: {list(Book._sa_relationship_props.keys())}")
    else:
        print("No SQLAlchemy relationships on Book")
        
    if hasattr(Author, "_sa_relationship_props"):
        print(f"Author SA relationships: {list(Author._sa_relationship_props.keys())}")
    else:
        print("No SQLAlchemy relationships on Author")
    
    try:
        # Create test data
        print("\n=== Creating test data ===")
        author_data = {"name": "John Doe"}
        author = await Author.insert(author_data)
        print(f"Created author: {author.id}, {author.name}")
        
        book_data = {"title": "Test Book", "author_id": author.id}
        book = await Book.insert(book_data)
        print(f"Created book: {book.id}, {book.title}, author_id={book.author_id}")
        
        # Test retrieving data with relationships
        print("\n=== Retrieving data with relationships ===")
        retrieved_book = await Book.get_by_id(book.id, include_relationships=True)
        if hasattr(retrieved_book, "author") and retrieved_book.author:
            print(f"Book: {retrieved_book.title} - Author: {retrieved_book.author.name}")
        else:
            print(f"Book: {retrieved_book.title} - No author relationship loaded")
        
        retrieved_author = await Author.get_by_id(author.id, include_relationships=True)
        if hasattr(retrieved_author, "books") and retrieved_author.books:
            print(f"Author: {retrieved_author.name} - Books:")
            for book in retrieved_author.books:
                print(f"  - {book.title}")
        else:
            print(f"Author: {retrieved_author.name} - No books relationship loaded")
            
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Close the engine
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(run_test())
