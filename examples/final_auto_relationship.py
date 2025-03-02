"""
Final test of automatic relationship detection with manual setup.
This approach avoids conflicts with SQLModel's metaclass.
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
    register_model_class,
    setup_relationship_between_models
)

# Configure SQLite
db_config.configure_sqlite("./final_auto_rel.db")

# Enable auto relationships but don't patch the metaclass
enable_auto_relationships(patch_metaclass=False)

# Define models with explicit relationships to avoid SQLModel metaclass issues
class Author(EasyModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    
    # We'll define relationships using SQLModel's Relationship
    books: List["Book"] = Relationship(back_populates="author")

class Book(EasyModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    author_id: Optional[int] = Field(default=None, foreign_key="author.id")
    
    # We'll define relationships using SQLModel's Relationship
    author: Optional[Author] = Relationship(back_populates="books")

async def run_test():
    """Run the example with SQLite."""
    print(f"Using database: {db_config.get_connection_url()}")
    
    # Initialize database
    await init_db()
    
    # Create tables
    engine = db_config.get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)
    
    # Check for relationships
    print("\n=== Checking relationships ===")
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
        author = await Author.insert({"name": "John Doe"})
        print(f"Created author: {author.id}, {author.name}")
        
        book = await Book.insert({
            "title": "Test Book", 
            "author_id": author.id
        })
        print(f"Created book: {book.id}, {book.title}, author_id={book.author_id}")
        
        # Test retrieving data with relationships
        print("\n=== Retrieving data with relationships ===")
        retrieved_book = await Book.get_by_id(book.id, include_relationships=True)
        if hasattr(retrieved_book, "author") and retrieved_book.author:
            print(f"✅ Book: {retrieved_book.title} - Author: {retrieved_book.author.name}")
        else:
            print(f"❌ Book: {retrieved_book.title} - No author relationship loaded")
        
        retrieved_author = await Author.get_by_id(author.id, include_relationships=True)
        if hasattr(retrieved_author, "books") and retrieved_author.books:
            print(f"✅ Author: {retrieved_author.name} - Books:")
            for b in retrieved_author.books:
                print(f"  - {b.title}")
        else:
            print(f"❌ Author: {retrieved_author.name} - No books relationship loaded")
            
        # Testing with the all() method
        print("\n=== Testing with all() method ===")
        all_books = await Book.all(include_relationships=True)
        print(f"Retrieved {len(all_books)} books:")
        for b in all_books:
            author_name = b.author.name if hasattr(b, "author") and b.author else "None"
            print(f"  - {b.title} (Author: {author_name})")
            
        # Testing with ordering
        print("\n=== Testing with ordering ===")
        # Create more books for testing ordering
        await Book.insert({
            "title": "Advanced Programming", 
            "author_id": author.id
        })
        await Book.insert({
            "title": "Zen of Coding", 
            "author_id": author.id
        })
        
        # Get books ordered by title
        books_ordered = await Book.all(order_by="title", include_relationships=True)
        print("Books ordered by title (ascending):")
        for b in books_ordered:
            print(f"  - {b.title}")
            
        # Get books ordered by title descending
        books_ordered_desc = await Book.all(order_by="-title", include_relationships=True)
        print("Books ordered by title (descending):")
        for b in books_ordered_desc:
            print(f"  - {b.title}")
            
    except Exception as e:
        print(f"Error during example: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(run_test())
