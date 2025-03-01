"""
Example demonstrating the enhanced relationship handling in async-easy-model.

This example shows how to:
1. Create models with relationships
2. Fetch related objects with a single query
3. Convert models to dictionaries with nested relationships
4. Create models with related objects in a single transaction
"""

import asyncio
import sys
from pathlib import Path
import os

# Add the parent directory to sys.path to import the package
sys.path.append(str(Path(__file__).parent.parent))

from sqlmodel import Field, Relationship
from typing import List, Optional
from datetime import date, datetime
from async_easy_model import EasyModel, init_db, db_config

# Configure SQLite for the example
db_config.configure_sqlite("example.db")

# Define models with relationships
class Author(EasyModel, table=True):
    """Author model with a one-to-many relationship to Book."""
    name: str = Field(index=True)
    email: str = Field(unique=True)
    books: List["Book"] = Relationship(back_populates="author")

class Category(EasyModel, table=True):
    """Category model with a one-to-many relationship to Book."""
    name: str = Field(unique=True)
    books: List["Book"] = Relationship(back_populates="category")

class Book(EasyModel, table=True):
    """
    Book model with many-to-one relationships to Author and Category.
    """
    title: str = Field(index=True)
    published_date: date = Field(default_factory=date.today)
    
    # Foreign keys
    author_id: Optional[int] = Field(default=None, foreign_key="author.id")
    category_id: Optional[int] = Field(default=None, foreign_key="category.id")
    
    # Relationships
    author: Optional[Author] = Relationship(back_populates="books")
    category: Optional[Category] = Relationship(back_populates="books")

async def run_example():
    """Run the example code demonstrating relationship features."""
    print("Initializing database...")
    await init_db()
    
    # Create an author
    print("\nCreating an author...")
    author_data = {
        "name": "Jane Doe",
        "email": "jane@example.com"
    }
    author = await Author.insert(author_data)
    print(f"Created author: {author.name} (ID: {author.id})")
    
    # Create a category
    print("\nCreating a category...")
    category_data = {
        "name": "Science Fiction"
    }
    category = await Category.insert(category_data)
    print(f"Created category: {category.name} (ID: {category.id})")
    
    # Create a book with relationships using separate calls
    print("\nCreating a book with relationships using separate calls...")
    book_data = {
        "title": "The Future of AI",
        "author_id": author.id,
        "category_id": category.id
    }
    book = await Book.insert(book_data)
    print(f"Created book: {book.title} (ID: {book.id})")
    
    # Create another book with related objects in a single transaction
    print("\nCreating a book with related objects in a single transaction...")
    new_author_data = {
        "name": "John Smith",
        "email": "john@example.com"
    }
    new_category_data = {
        "name": "Fantasy"
    }
    
    # First create the author and category
    new_author = await Author.insert(new_author_data)
    new_category = await Category.insert(new_category_data)
    
    # Now create a book with the new author and category
    new_book_data = {
        "title": "The Magic Kingdom",
        "author_id": new_author.id,
        "category_id": new_category.id
    }
    new_book = await Book.insert(new_book_data)
    print(f"Created book: {new_book.title} with author: {new_author.name} and category: {new_category.name}")
    
    # Fetch a book with its relationships
    print("\nFetching a book with its relationships...")
    book_with_relations = await Book.get_by_id(book.id, include_relationships=True)
    print(f"Book: {book_with_relations.title}")
    print(f"Author: {book_with_relations.author.name}")
    print(f"Category: {book_with_relations.category.name}")
    
    # Fetch a book and load specific relationships
    print("\nFetching a book and loading specific relationships...")
    another_book = await Book.get_by_id(new_book.id)
    await another_book.load_related("author", "category")
    print(f"Book: {another_book.title}")
    print(f"Author: {another_book.author.name}")
    print(f"Category: {another_book.category.name}")
    
    # Get an author with all their books
    print("\nGetting an author with all their books...")
    author_with_books = await Author.get_with_related(author.id, "books")
    print(f"Author: {author_with_books.name}")
    print(f"Books: {[book.title for book in author_with_books.books]}")
    
    # Convert to dictionary with relationships
    print("\nConverting to dictionary with relationships...")
    author_dict = author_with_books.to_dict(include_relationships=True)
    print(f"Author dict: {author_dict['name']}")
    print(f"Books in dict: {[book['title'] for book in author_dict['books']]}")
    
    # Create with related in one transaction
    print("\nCreating an author with books in one transaction...")
    new_author_with_books = await Author.create_with_related(
        data={
            "name": "Alice Wonder",
            "email": "alice@example.com"
        },
        related_data={
            "books": [
                {"title": "Wonderland Adventures"},
                {"title": "Through the Looking Glass"}
            ]
        }
    )
    print(f"Created author: {new_author_with_books.name} with books:")
    for book in new_author_with_books.books:
        print(f"- {book.title}")

if __name__ == "__main__":
    asyncio.run(run_example())
