"""
Auto Relationship Example

This example demonstrates how the automatic relationship detection works
in async-easy-model.
"""

import asyncio
import sys
import os
import uuid

# Add the parent directory to the Python path so we can import the local package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from typing import List, Optional
from sqlmodel import Field, Relationship
from async_easy_model import EasyModel, init_db, db_config, enable_auto_relationships
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Enable automatic relationship detection
enable_auto_relationships()

# Configure a SQLite database for this example
db_config.configure_sqlite("auto_relationship_example.db")


# Define our models with relationships explicitly
class Author(EasyModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    email: str = Field(unique=True)
    
    books: List["Book"] = Relationship(back_populates="author")


class Book(EasyModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    author_id: Optional[int] = Field(default=None, foreign_key="author.id")
    
    author: Optional[Author] = Relationship(back_populates="books")


async def main():
    # Initialize the database and create all tables
    await init_db()
    
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
    
    # Now let's demonstrate that the relationships work
    
    # Get an author with their books
    retrieved_author = await Author.get_by_id(author.id, include_relationships=True)
    print(f"\nAuthor: {retrieved_author.name}")
    print("Books:")
    for book in retrieved_author.books:
        print(f"  - {book.title}")
    
    # Get a book with its author
    retrieved_book = await Book.get_by_id(book1.id, include_relationships=True)
    print(f"\nBook: {retrieved_book.title}")
    print(f"Written by: {retrieved_book.author.name}")


if __name__ == "__main__":
    asyncio.run(main())
