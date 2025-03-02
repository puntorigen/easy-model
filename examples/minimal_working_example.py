"""
Minimal working example of relationship detection with SQLite

This example creates a simple Author-Book relationship and demonstrates
both the retrieval of related objects with include_relationships and 
the various query methods (all, first, limit) with relationships.
"""

import os
import sys
import asyncio
from typing import List, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

# Ensure we're using the local package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Field, SQLModel, Relationship
from async_easy_model.model import EasyModel, init_db, db_config

# Configure SQLite database
db_config.configure_sqlite("./minimal_example.db")

# Define Author model with relationship to books
class Author(EasyModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    
    # SQLModel Relationship
    books: List["Book"] = Relationship(back_populates="author")

# Define Book model with relationship to author
class Book(EasyModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    author_id: Optional[int] = Field(default=None, foreign_key="author.id")
    
    # SQLModel Relationship
    author: Optional[Author] = Relationship(back_populates="books")

async def run_example():
    """Run the minimal working example."""
    print(f"Using database: {db_config.get_connection_url()}")
    
    # Initialize database
    await init_db()
    
    # Create tables
    engine = db_config.get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)
    
    try:
        # Create test data
        print("\n=== Creating test data ===")
        author1 = await Author.insert({"name": "Jane Austen"})
        author2 = await Author.insert({"name": "Ernest Hemingway"})
        
        book1 = await Book.insert({
            "title": "Pride and Prejudice", 
            "author_id": author1.id
        })
        
        book2 = await Book.insert({
            "title": "Sense and Sensibility", 
            "author_id": author1.id
        })
        
        book3 = await Book.insert({
            "title": "The Old Man and the Sea", 
            "author_id": author2.id
        })
        
        print(f"Created 2 authors and 3 books")
        
        # Test retrieving with relationships
        print("\n=== Retrieving data with relationships ===")
        
        # 1. Get by ID with relationships
        retrieved_author = await Author.get_by_id(author1.id, include_relationships=True)
        print(f"Author: {retrieved_author.name}")
        print(f"Books by {retrieved_author.name}:")
        for book in retrieved_author.books:
            print(f"  - {book.title}")
        
        # 2. Get by attribute with relationships
        retrieved_book = await Book.get_by_attribute(title="The Old Man and the Sea", all=True, include_relationships=True)
        if retrieved_book and len(retrieved_book) > 0:
            book = retrieved_book[0]
            print(f"\nBook: {book.title}")
            print(f"Author: {book.author.name}")
        
        # 3. Test all() method with relationships
        print("\n=== Testing all() method ===")
        all_books = await Book.all(include_relationships=True)
        print(f"All books (count: {len(all_books)}):")
        for book in all_books:
            print(f"  - '{book.title}' by {book.author.name}")
        
        # 4. Test first() method with relationships
        print("\n=== Testing first() method ===")
        first_book = await Book.first(include_relationships=True)
        print(f"First book: '{first_book.title}' by {first_book.author.name}")
        
        # 5. Test limit() method with ordering
        print("\n=== Testing limit() with ordering ===")
        limited_books = await Book.limit(2, order_by="title", include_relationships=True)
        print(f"First 2 books ordered by title:")
        for book in limited_books:
            print(f"  - '{book.title}' by {book.author.name}")
        
    except Exception as e:
        print(f"Error during example: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up
        await engine.dispose()
        print("\nExample completed.")

if __name__ == "__main__":
    asyncio.run(run_example())
