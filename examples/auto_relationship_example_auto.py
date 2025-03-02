"""
Auto Relationship Example (Auto Detection)

This example demonstrates how the automatic relationship detection works
in async-easy-model without explicitly defining relationships.
"""

import asyncio
import sys
import os
import uuid
import inspect

# Add the parent directory to the Python path so we can import the local package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from typing import List, Optional
from sqlmodel import Field
from async_easy_model import EasyModel, init_db, db_config, enable_auto_relationships
from async_easy_model.auto_relationships import process_auto_relationships
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Enable automatic relationship detection
enable_auto_relationships()

# Configure a SQLite database for this example
db_config.configure_sqlite("auto_relationship_example_auto.db")


# Define our models WITHOUT explicit relationships - they should be detected automatically
class Author(EasyModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    email: str = Field(unique=True)
    
    # No relationship definition for books - should be created automatically


class Book(EasyModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    author_id: Optional[int] = Field(default=None, foreign_key="author.id")
    
    # No relationship definition for author - should be created automatically


def print_model_info(model_cls):
    """Print debug information about a model class."""
    print(f"\n----- DEBUG INFO FOR {model_cls.__name__} -----")
    
    print(f"Tablename: {getattr(model_cls, '__tablename__', None)}")
    
    print("\nDirect attributes:")
    for attr_name in dir(model_cls):
        if attr_name.startswith('__'):
            continue
        attr = getattr(model_cls, attr_name)
        if hasattr(attr, 'back_populates'):
            print(f"  - {attr_name}: Relationship(back_populates='{attr.back_populates}')")
    
    print("\nSQLModel relationships:")
    if hasattr(model_cls, '__sqlmodel_relationships__'):
        for rel_name, rel_info in model_cls.__sqlmodel_relationships__.items():
            target = getattr(rel_info, 'link_model', None)
            target_name = target.__name__ if target else "None"
            back_populates = getattr(rel_info, 'back_populates', None)
            print(f"  - {rel_name}: target={target_name}, back_populates='{back_populates}'")
    else:
        print("  No __sqlmodel_relationships__ found")
    
    print("\nDetected relationship fields:")
    rel_fields = model_cls._get_auto_relationship_fields()
    print(f"  {rel_fields}")
    
    print(f"----- END DEBUG INFO FOR {model_cls.__name__} -----\n")


async def main():
    # Process auto-relationships explicitly before initializing the database
    process_auto_relationships()
    
    # Initialize the database and create all tables
    await init_db()
    
    # Print debug information for the models
    print_model_info(Author)
    print_model_info(Book)
    
    # Generate a unique suffix for emails to avoid conflicts if the example is run multiple times
    unique_suffix = str(uuid.uuid4())[:8]
    
    # Create an author
    author = await Author.insert({
        "name": "Jane Doe",
        "email": f"jane.doe.{unique_suffix}@example.com"
    })
    
    # Create another author
    another_author = await Author.insert({
        "name": "John Smith",
        "email": f"john.smith.{unique_suffix}@example.com"
    })
    
    # Create books linked to the first author
    book1 = await Book.insert({
        "title": "The Art of Automatic Relationships",
        "author_id": author.id
    })
    
    book2 = await Book.insert({
        "title": "Foreign Keys Made Simple",
        "author_id": author.id
    })
    
    # Create a book linked to the second author
    book3 = await Book.insert({
        "title": "SQLModel for Beginners",
        "author_id": another_author.id
    })
    
    # Now let's demonstrate that the auto-detected relationships work
    
    # Get an author with their books
    retrieved_author = await Author.get_by_id(author.id, include_relationships=True)
    print(f"\nAuthor: {retrieved_author.name}")
    
    # Print debug information about the retrieved author instance
    print("\n----- DEBUG INFO FOR RETRIEVED AUTHOR INSTANCE -----")
    print(f"Author ID: {retrieved_author.id}")
    print(f"Author Name: {retrieved_author.name}")
    print(f"Author Email: {retrieved_author.email}")
    print("\nAttributes:")
    for attr_name in dir(retrieved_author):
        if attr_name.startswith('__') or attr_name in ('id', 'name', 'email'):
            continue
        print(f"  - {attr_name}")
    print("----- END DEBUG INFO FOR RETRIEVED AUTHOR INSTANCE -----\n")
    
    # Try to access books (might fail if not set up correctly)
    try:
        print("Books:")
        for book in retrieved_author.books:
            print(f"  - {book.title}")
    except AttributeError as e:
        print(f"Error accessing books: {e}")
    
    # Get a book with its author
    retrieved_book = await Book.get_by_id(book1.id, include_relationships=True)
    print(f"\nBook: {retrieved_book.title}")
    
    # Print debug information about the retrieved book instance
    print("\n----- DEBUG INFO FOR RETRIEVED BOOK INSTANCE -----")
    print(f"Book ID: {retrieved_book.id}")
    print(f"Book Title: {retrieved_book.title}")
    print(f"Book Author ID: {retrieved_book.author_id}")
    print("\nAttributes:")
    for attr_name in dir(retrieved_book):
        if attr_name.startswith('__') or attr_name in ('id', 'title', 'author_id'):
            continue
        print(f"  - {attr_name}")
    print("----- END DEBUG INFO FOR RETRIEVED BOOK INSTANCE -----\n")
    
    # Try to access author (might fail if not set up correctly)
    try:
        print(f"Written by: {retrieved_book.author.name}")
    except AttributeError as e:
        print(f"Error accessing author: {e}")


if __name__ == "__main__":
    asyncio.run(main())
