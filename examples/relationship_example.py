"""
Example demonstrating the enhanced relationship handling in async-easy-model.

This example shows how to:
1. Create models with relationships
2. Fetch related objects with a single query
3. Convert models to dictionaries with nested relationships
4. Create models with related objects in a single transaction
5. Use the simplified Relation syntax for defining relationships
"""

import asyncio
import sys
from pathlib import Path
import os
import uuid
from datetime import datetime

# Add the parent directory to sys.path to import the package
sys.path.append(str(Path(__file__).parent.parent))

from typing import List, Optional
from datetime import date
# Using the Field and Relation directly from async_easy_model instead of sqlmodel
from async_easy_model import EasyModel, init_db, db_config, Field, Relation

# Generate a unique database name to ensure we don't have conflicts
unique_db_name = f"rel_example_{int(datetime.now().timestamp())}.db"
# Configure SQLite for the example
db_config.configure_sqlite(unique_db_name)

# Define models with relationships using the simplified Relation syntax
class Author(EasyModel, table=True):
    """Author model with a one-to-many relationship to Book."""
    name: str = Field(index=True)
    email: str = Field(unique=True)
    # Using Relation.many for a more readable relationship definition
    books: List["Book"] = Relation.many("author")

class Category(EasyModel, table=True):
    """Category model with a one-to-many relationship to Book."""
    name: str = Field(unique=True)
    # Using Relation.many for a more readable relationship definition
    books: List["Book"] = Relation.many("category")

class Book(EasyModel, table=True):
    """
    Book model with many-to-one relationships to Author and Category.
    """
    title: str = Field(index=True)
    published_date: date = Field(default_factory=date.today)
    
    # Foreign keys
    author_id: Optional[int] = Field(default=None, foreign_key="author.id")
    category_id: Optional[int] = Field(default=None, foreign_key="category.id")
    
    # Relationships using Relation.one for a more readable relationship definition
    author: Optional["Author"] = Relation.one("books")
    category: Optional["Category"] = Relation.one("books")

async def run_example():
    """Run the example code demonstrating relationship features."""
    print("Initializing database...")
    await init_db()
    
    # Create an author with unique email
    print("\nCreating an author...")
    author_data = {
        "name": "Jane Doe",
        "email": f"jane_{uuid.uuid4().hex[:8]}@example.com"
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
    
    # Create a book with relationships
    print("\nCreating a book with relationships using separate calls...")
    book_data = {
        "title": "The Future of AI",
        "author_id": author.id,
        "category_id": category.id
    }
    book = await Book.insert(book_data)
    print(f"Created book: {book.title} (ID: {book.id})")
    
    # Create a new author and category first
    print("\nCreating a book with related objects...")
    new_author = await Author.insert({
        "name": "John Smith",
        "email": f"john_{uuid.uuid4().hex[:8]}@example.com"
    })
    new_category = await Category.insert({
        "name": "Fantasy"
    })
    
    # Now create a book with these IDs
    new_book = await Book.insert({
        "title": "The Magic Kingdom",
        "author_id": new_author.id,
        "category_id": new_category.id
    })
    
    # Fetch the book with its relationships using get_with_related
    new_book_with_relations = await Book.get_with_related(new_book.id, "author", "category")
    print(f"Created book: {new_book_with_relations.title} with author: {new_book_with_relations.author.name} and category: {new_book_with_relations.category.name}")
    
    # Fetch a book with its relationships
    print("\nFetching a book with its relationships...")
    book_with_relations = await Book.get_by_id(book.id, include_relationships=True)
    print(f"Book: {book_with_relations.title}")
    print(f"Author: {book_with_relations.author.name}")
    print(f"Category: {book_with_relations.category.name}")
    
    # Fetch a book and load specific relationships using get_with_related
    print("\nFetching a book with specific relationships...")
    another_book = await Book.get_with_related(new_book.id, "author", "category")
    print(f"Book: {another_book.title}")
    print(f"Author: {another_book.author.name}")
    print(f"Category: {another_book.category.name}")
    
    # Create author with books as a demonstration of create_with_related
    print("\nCreating an author with books in a single transaction...")
    author_with_books = await Author.create_with_related(
        data={
            "name": "Alice Wonder",
            "email": f"alice_{uuid.uuid4().hex[:8]}@example.com"
        },
        related_data={
            "books": [
                {"title": "Wonderland Adventures"},
                {"title": "Through the Looking Glass"}
            ]
        }
    )
    print(f"Created author: {author_with_books.name} with books:")
    for book in author_with_books.books:
        print(f"- {book.title}")
        
    # Demonstrating dictionary conversion with relationships properly
    print("\nConverting models to dictionaries with relationships...")
    # Make sure we have fresh instances with loaded relationships
    author_for_dict = await Author.get_with_related(author_with_books.id, "books")
    book_for_dict = await Book.get_with_related(book.id, "author", "category")
    
    # Now convert to dictionaries
    author_dict = author_for_dict.to_dict(include_relationships=True)
    book_dict = book_for_dict.to_dict(include_relationships=True)
    
    # Display the results
    print(f"Author: {author_dict['name']}")
    print(f"Books by {author_dict['name']}:")
    for book_item in author_dict.get('books', []):
        print(f"- {book_item.get('title')}")
        
    print(f"\nBook: {book_dict['title']}")
    if 'author' in book_dict and book_dict['author']:
        print(f"Written by: {book_dict['author'].get('name')}")
    if 'category' in book_dict and book_dict['category']:
        print(f"Category: {book_dict['category'].get('name')}")
    
    # Clean up - delete all created objects
    print("\nCleaning up...")
    # First delete all books
    all_books = await Book.all()
    for book_item in all_books:
        await Book.delete(book_item.id)
        
    # Then delete authors and categories
    all_authors = await Author.all()
    for author_item in all_authors:
        await Author.delete(author_item.id)
        
    all_categories = await Category.all()
    for category_item in all_categories:
        await Category.delete(category_item.id)
    
    # Verify deletion
    all_books = await Book.all()
    all_authors = await Author.all()
    all_categories = await Category.all()
    print(f"Remaining books: {len(all_books)}")
    print(f"Remaining authors: {len(all_authors)}")
    print(f"Remaining categories: {len(all_categories)}")
    
    # Delete the database file at the end
    print(f"\nDeleting database file: {unique_db_name}")
    try:
        os.remove(unique_db_name)
        print("Database file deleted successfully")
    except Exception as e:
        print(f"Error deleting database file: {e}")

if __name__ == "__main__":
    asyncio.run(run_example())
