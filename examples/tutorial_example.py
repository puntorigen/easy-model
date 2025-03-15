import asyncio
import logging
import os
from datetime import datetime
from typing import Optional, List

from sqlmodel import Field
from async_easy_model import EasyModel, Field, db_config, init_db

# Configure logging
logging.basicConfig(level=logging.INFO)

# Configure database 
db_file = "tutorial_example.db"
# Remove existing database file if it exists to start fresh
if os.path.exists(db_file):
    os.remove(db_file)
    logging.info(f"Removed existing database file: {db_file}")

db_config.configure_sqlite(db_file)

class User(EasyModel, table=True):
    username: str = Field(unique=True)
    email: str = Field(unique=True)

class Author(EasyModel, table=True):
    name: str
    bio: Optional[str] = Field(default=None)

class Tag(EasyModel, table=True):
    name: str = Field(unique=True)

class Book(EasyModel, table=True):
    title: str
    publication_year: int
    isbn: str = Field(unique=True)
    author_id: Optional[int] = Field(default=None, foreign_key="author.id")
    price: float = Field(default=0.0)

class BookTag(EasyModel, table=True):
    book_id: Optional[int] = Field(default=None, foreign_key="book.id")
    tag_id: Optional[int] = Field(default=None, foreign_key="tag.id")

class Review(EasyModel, table=True):
    rating: int = Field(ge=1, le=5)
    comment: Optional[str] = Field(default=None)
    book_id: Optional[int] = Field(default=None, foreign_key="book.id")
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")

async def create_book():
    # Create book with all relationships in a single operation
    book = await Book.insert({
        "title": "The Art of Async Python",
        "publication_year": 2023,
        "isbn": "978-1234567890",
        "price": 39.99,
        "author": {  # Nested author creation
            "name": "Jane Smith",
            "bio": "Python expert and educator"
        },
        "booktags": [  # Create BookTag join records with nested tags
            {
                "tag": {"name": "Programming"}
            },
            {
                "tag": {"name": "Python"}
            },
            {
                "tag": {"name": "Async"}
            }
        ],
        "reviews": [  # Create reviews with nested users
            {
                "rating": 5,
                "comment": "Game-changing book!",
                "user": {  # Create the reviewer
                    "username": "pythonlover",
                    "email": "fan@example.com"
                }
            },
            {
                "rating": 4,
                "comment": "Very practical approach",
                "user": {
                    "username": "devguru",
                    "email": "guru@example.com"
                }
            }
        ]
    }, max_depth=3)  # Use max_depth=3 to ensure nested relationships like review->user are loaded
    
    print("Debugging newly created book", book.to_dict())
    
    # Access all relationship data - all relationships are now fully loaded automatically
    print(f"Created book: {book.title} by {book.author.name}")
    print(f"Book has {len(book.reviews)} reviews")
    for i, review in enumerate(book.reviews):
        print(f"Review {i+1}: {review.rating}/5 stars by {review.user.username}")
    
    # Print tag names - now we can access the nested tag objects directly
    tags = [booktag.tag.name for booktag in book.booktags]
    print(f"Tags: {', '.join(tags)}")
    
    return book

async def find_python_books_with_good_reviews():
    # Find the Python tag directly with a condition
    python_tag = await Tag.select({"name": "Python"}, max_depth=3)
    
    if not python_tag:
        print("No Python tag found!")
        return []
    
    # Find all books that have this tag through the BookTag join table
    # This will automatically load the nested relationship chain (book -> reviews -> user)
    python_books = []
    for booktag in python_tag.booktags:
        book = booktag.book
        
        # Check if this book has any good reviews (rating >= 4)
        has_good_reviews = any(review.rating >= 4 for review in book.reviews)
        
        if has_good_reviews:
            python_books.append(book)
    
    print(f"Found {len(python_books)} Python books with good reviews:")
    for book in python_books:
        print(f"- {book.title} by {book.author.name}")
    
    return python_books

async def update_book(book_id):
    try:
        # Create an update data dictionary
        update_data = {
            "price": 42.99,
            "publication_year": 2024
        }
        
        # Create criteria to identify which book to update
        criteria = {"id": book_id}
        
        # Use the class-level update method with criteria
        updated_book = await Book.update(update_data, criteria)
        
        # Fetch the updated book to display its details
        book = await Book.select({"id": book_id}, include_relationships=True)
        
        print(f"Updated book: {book.title}")
        print(f"New price: ${book.price:.2f}")
        print(f"New year: {book.publication_year}")
        
        return book
    except Exception as e:
        print(f"Error updating record: {e}")
        return None

async def main():
    # Magic happens here - tables created, relationships detected
    await init_db()
    await create_book()
    await find_python_books_with_good_reviews()
    await update_book(1)

asyncio.run(main())