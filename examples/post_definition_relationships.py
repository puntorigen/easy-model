"""
Demonstrate auto relationships by setting them up after model definition.
This approach avoids conflicts with SQLModel's metaclass.
"""

import os
import asyncio
import sys
from sqlmodel import Field, SQLModel
from typing import List, Optional
import logging

# Configure logging to see debug messages
logging.basicConfig(level=logging.INFO)

# Ensure we're using the local package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from async_easy_model.model import EasyModel, init_db, db_config
from async_easy_model.auto_relationships import enable_auto_relationships
from sqlalchemy.orm import relationship

# Configure SQLite
db_config.configure_sqlite("./post_def_rel.db")

# Enable auto relationships
enable_auto_relationships()

# First, define the models without any relationships
class Author(EasyModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str

class Book(EasyModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    author_id: Optional[int] = Field(
        default=None, foreign_key="author.id", description="Foreign key to author"
    )

# Now manually set up the relationships after the models are fully defined
# For the Book -> Author relationship (to-one)
Book.author = relationship(
    "Author",
    back_populates="books",
    uselist=False,
    foreign_keys=[Book.author_id]
)

# For the Author -> Book relationship (to-many)
Author.books = relationship(
    "Book",
    back_populates="author",
    uselist=True
)

# Register relationships with SQLModel's metadata
if not hasattr(Book, "__sqlmodel_relationships__"):
    Book.__sqlmodel_relationships__ = {}

Book.__sqlmodel_relationships__["author"] = type('RelationshipInfo', (), {
    'back_populates': 'books',
    'link_model': Author
})

if not hasattr(Author, "__sqlmodel_relationships__"):
    Author.__sqlmodel_relationships__ = {}

Author.__sqlmodel_relationships__["books"] = type('RelationshipInfo', (), {
    'back_populates': 'author',
    'link_model': Book
})

print("Relationships manually set up after model definition")

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
            
    except Exception as e:
        print(f"Error during example: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(run_test())
