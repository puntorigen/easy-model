"""
Example demonstrating the nested relationship data handling in the 'insert' method.

This example shows how to:
1. Create models with automatic relationship detection
2. Insert a model with nested relationship data in a single operation
3. Compare with the explicit insert_with_related method
4. Test more complex nested relationship scenarios
"""

import asyncio
import sys
from pathlib import Path
import os
import uuid
from datetime import datetime, date

# Add the parent directory to sys.path to import the package
sys.path.append(str(Path(__file__).parent.parent))

from typing import List, Optional, Dict, Any
# Using Field from async_easy_model instead of sqlmodel
from async_easy_model import EasyModel, init_db, db_config, Field

# Generate a unique database name to ensure we don't have conflicts
unique_db_name = f"nested_insert_example_{int(datetime.now().timestamp())}.db"
# Configure SQLite for the example
db_config.configure_sqlite(unique_db_name)

# Define models with automatic relationship detection
class Publisher(EasyModel, table=True):
    """Publisher model with automatic one-to-many relationships to Author and Book."""
    name: str = Field(unique=True)
    founded_year: int = Field(default=2000)
    description: str = Field(default="")
    
    # Relationships will be automatically detected:
    # - publisher.authors: automatically available after init_db()
    # - publisher.books: automatically available after init_db()

class Author(EasyModel, table=True):
    """Author model with automatic relationships."""
    name: str = Field(index=True)
    email: str = Field(unique=True)
    bio: str = Field(default="")
    
    # Foreign keys for automatic relationship detection
    publisher_id: Optional[int] = Field(default=None, foreign_key="publisher.id")
    
    # Relationships will be automatically detected:
    # - author.publisher: automatically available after init_db()
    # - author.books: automatically available after init_db()
    # - author.genres: automatically available after init_db() (through AuthorGenre)

class Genre(EasyModel, table=True):
    """Genre model with automatic relationships."""
    name: str = Field(unique=True)
    description: str = Field(default="")
    
    # Relationships will be automatically detected:
    # - genre.books: automatically available after init_db()
    # - genre.authors: automatically available after init_db() (through AuthorGenre)

class AuthorGenre(EasyModel, table=True):
    """Link table for many-to-many relationship between Author and Genre."""
    author_id: Optional[int] = Field(
        default=None, foreign_key="author.id", primary_key=True
    )
    genre_id: Optional[int] = Field(
        default=None, foreign_key="genre.id", primary_key=True
    )
    
    # Relationships will be automatically detected:
    # - authorgenre.author: automatically available after init_db()
    # - authorgenre.genre: automatically available after init_db()

class Book(EasyModel, table=True):
    """Book model with automatic relationships."""
    title: str = Field(index=True)
    published_date: date = Field(default_factory=date.today)
    description: str = Field(default="")
    price: float = Field(default=0.0)
    
    # Foreign keys for automatic relationship detection
    author_id: Optional[int] = Field(default=None, foreign_key="author.id")
    genre_id: Optional[int] = Field(default=None, foreign_key="genre.id")
    publisher_id: Optional[int] = Field(default=None, foreign_key="publisher.id")
    
    # Relationships will be automatically detected:
    # - book.author: automatically available after init_db()
    # - book.genre: automatically available after init_db()
    # - book.publisher: automatically available after init_db()
    # - book.reviews: automatically available after init_db()

class Review(EasyModel, table=True):
    """Review model with automatic relationship to Book."""
    content: str
    rating: int = Field(ge=1, le=5)  # Rating from 1 to 5
    reviewer_name: str
    
    # Foreign key for automatic relationship detection
    book_id: Optional[int] = Field(default=None, foreign_key="book.id")
    
    # Relationships will be automatically detected:
    # - review.book: automatically available after init_db()

async def display_entity_details(entity, name="Entity", include_nested=True, max_depth=2):
    """Helper function to display entity details including nested relationships."""
    print(f"\n--- {name} Details ---")
    entity_dict = entity.to_dict(include_relationships=include_nested, max_depth=max_depth)
    
    def print_nested(data, indent=0):
        for key, value in data.items():
            if isinstance(value, dict):
                print("  " * indent + f"{key}:")
                print_nested(value, indent + 1)
            elif isinstance(value, list) and value and isinstance(value[0], dict):
                print("  " * indent + f"{key}: [{len(value)} items]")
                for i, item in enumerate(value):
                    print("  " * (indent + 1) + f"Item {i + 1}:")
                    print_nested(item, indent + 2)
            else:
                print("  " * indent + f"{key}: {value}")
    
    print_nested(entity_dict)

async def run_nested_insert_example():
    """Run the example demonstrating nested insert functionality."""
    print("Initializing database...")
    await init_db()
    
    print("\n=== EXAMPLE 1: Basic Nested Insert ===")
    print("\nCreating a publisher with a nested author using insert...")
    
    # Generate unique email to avoid conflicts
    email = f"author_{uuid.uuid4().hex[:8]}@example.com"
    
    # Create a publisher with a nested author using insert
    publisher_data = {
        "name": "Penguin Books",
        "founded_year": 1935,
        "authors": [
            {
                "name": "Jane Smith",
                "email": email,
                "bio": "Award-winning fiction author"
            }
        ]
    }
    
    # Use the insert method with nested data
    publisher = await Publisher.insert(publisher_data)
    
    # Display the result
    await display_entity_details(publisher, "Publisher with Nested Author")
    
    # Let's verify the author was created and properly linked
    author = await Author.get_by_attribute(email=email)
    print(f"\nVerifying author creation: {author.name} (ID: {author.id})")
    print(f"Author's publisher_id: {author.publisher_id} (should match Publisher ID: {publisher.id})")
    
    print("\n=== EXAMPLE 2: Complex Nested Insert ===")
    # Now let's try a more complex example with multiple levels of nesting
    
    # Create a publisher with authors, books, and genres all at once
    complex_data = {
        "name": "TechPress Publishing",
        "founded_year": 2010,
        "authors": [
            {
                "name": "John Tech",
                "email": f"john_{uuid.uuid4().hex[:8]}@example.com",
                "bio": "Technology expert",
                "books": [
                    {
                        "title": "Python Programming",
                        "published_date": date(2022, 5, 15),
                        "price": 29.99,
                        "description": "A comprehensive guide to Python",
                        "genre": {
                            "name": "Programming",
                            "description": "Books about programming languages and techniques"
                        },
                        "reviews": [
                            {
                                "content": "Excellent book for beginners!",
                                "rating": 5,
                                "reviewer_name": "Alice"
                            },
                            {
                                "content": "Very comprehensive coverage.",
                                "rating": 4,
                                "reviewer_name": "Bob"
                            }
                        ]
                    }
                ]
            },
            {
                "name": "Sarah Coder",
                "email": f"sarah_{uuid.uuid4().hex[:8]}@example.com",
                "bio": "Software developer and author",
                "books": [
                    {
                        "title": "Web Development Essentials",
                        "published_date": date(2023, 2, 10),
                        "price": 34.99,
                        "genre": {
                            "name": "Web Development",
                            "description": "Books about web technologies"
                        }
                    }
                ]
            }
        ]
    }
    
    # Attempt to insert this complex nested structure
    print("\nCreating a publisher with nested authors, books, genres, and reviews...")
    try:
        tech_publisher = await Publisher.insert(complex_data)
        await display_entity_details(tech_publisher, "Complex Nested Publisher", max_depth=3)
    except Exception as e:
        print(f"Error during complex insert: {e}")
    
    print("\n=== EXAMPLE 3: Comparison with insert_with_related ===")
    # Compare with the insert_with_related method
    
    # First approach: using insert with nested data
    publisher_nested_data = {
        "name": "Harper Collins",
        "founded_year": 1989,
        "authors": [
            {
                "name": "Emily Writer",
                "email": f"emily_{uuid.uuid4().hex[:8]}@example.com",
                "bio": "Mystery novelist"
            }
        ]
    }
    
    print("\nApproach 1: Using insert with nested data...")
    publisher_approach1 = await Publisher.insert(publisher_nested_data)
    
    # Second approach: using insert_with_related
    publisher_data = {
        "name": "Simon & Schuster",
        "founded_year": 1924
    }
    
    related_data = {
        "authors": [
            {
                "name": "Michael Author",
                "email": f"michael_{uuid.uuid4().hex[:8]}@example.com",
                "bio": "Sci-fi writer"
            }
        ]
    }
    
    print("\nApproach 2: Using insert_with_related...")
    publisher_approach2 = await Publisher.insert_with_related(
        data=publisher_data,
        related_data=related_data
    )
    
    # Display results of both approaches
    print("\nBoth approaches should yield similar results:")
    await display_entity_details(publisher_approach1, "Publisher from insert with nested data")
    await display_entity_details(publisher_approach2, "Publisher from insert_with_related")
    
    print("\n=== Clean up ===")
    # Delete the database file
    print(f"Deleting database file: {unique_db_name}")
    try:
        os.remove(unique_db_name)
        print("Database file deleted successfully")
    except Exception as e:
        print(f"Error deleting database file: {e}")

if __name__ == "__main__":
    asyncio.run(run_nested_insert_example())
