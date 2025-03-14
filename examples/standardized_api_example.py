"""
Example demonstrating the standardized API for async-easy-model.
This shows the new, more convenient methods for common database operations.
"""

import asyncio
import os
import logging
from typing import Optional, List
from datetime import datetime
from sqlmodel import Relationship
from async_easy_model import EasyModel, init_db, db_config, Field
from async_easy_model import enable_auto_relationships
from async_easy_model.auto_relationships import process_all_models_for_relationships, disable_auto_relationships, register_model_class

# Set logging level to DEBUG to see relationship detection details
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("auto_relationships").setLevel(logging.DEBUG)

# Configure the database - using a file instead of in-memory
DB_FILE = "example.db"
# Remove existing database file if it exists
if os.path.exists(DB_FILE):
    os.remove(DB_FILE)
db_config.configure_sqlite(DB_FILE)

# Make sure auto-relationships are disabled at the start
disable_auto_relationships()

# Define models
class User(EasyModel, table=True):
    username: str = Field(unique=True)
    email: str
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.now)

class Product(EasyModel, table=True):
    name: str = Field(unique=True)
    description: Optional[str] = Field(default=None)
    price: float

class ShoppingCart(EasyModel, table=True):
    user_id: int = Field(foreign_key="user.id")
    product_id: int = Field(foreign_key="product.id")
    quantity: int

# Using automatic relationship detection for Author and Book
class Author(EasyModel, table=True):
    name: str
    # Adding more fields for sorting examples
    country: str = Field(default="Unknown")
    birth_year: Optional[int] = Field(default=None)

class Book(EasyModel, table=True):
    title: str
    author_id: Optional[int] = Field(default=None, foreign_key="author.id")
    published_year: Optional[int] = Field(default=None)
    pages: Optional[int] = Field(default=None)

# Now that models are defined, enable automatic relationship detection
print("Enabling auto-relationships after model definitions...")
enable_auto_relationships(patch_metaclass=False)

# Manually register our models to ensure they're in the registry
print("Manually registering models...")
for model_cls in [User, Product, ShoppingCart, Author, Book]:
    print(f"Registering {model_cls.__name__}")
    register_model_class(model_cls)

# Process relationships for all models
print("Processing model relationships...")
process_all_models_for_relationships()

# Debug: Print relationship info for models
print("\nRelationship information for models:")
for model_cls in [User, Product, ShoppingCart, Author, Book]:
    print(f"\n{model_cls.__name__} relationships:")
    rels = getattr(model_cls, "__sqlmodel_relationships__", None)
    if rels:
        for rel_name, rel_info in rels.items():
            print(f"  - {rel_name}: {rel_info}")
    else:
        print("  No relationships found")
    
    # Also check if relationship attributes exist directly
    rel_attrs = []
    for attr in dir(model_cls):
        if not attr.startswith('_'):
            try:
                attr_value = getattr(model_cls, attr)
                attr_type = type(attr_value).__name__
                if "Relationship" in attr_type:
                    rel_attrs.append((attr, attr_type))
            except Exception as e:
                pass
    
    if rel_attrs:
        print(f"  Direct relationship attributes: {rel_attrs}")

async def run_examples():
    # Initialize the database
    print("\nInitializing database...")
    await init_db()

    # Example 1: Create users with insert method
    print("\n=== Example 1: Insert users ===")
    users = await User.insert([
        {"username": "john_doe", "email": "john@example.com"},
        {"username": "jane_doe", "email": "jane@example.com"}
    ])
    print(f"Inserted users: {[user.username for user in users]}")

    # Example 2: Create products
    print("\n=== Example 2: Create products ===")
    products = await Product.insert([
        {"name": "Laptop", "description": "Powerful laptop", "price": 1200.0},
        {"name": "Phone", "description": "Smartphone", "price": 800.0}
    ])
    print(f"Inserted products: {[product.name for product in products]}")

    # Example 3: Create shopping carts with relationships
    print("\n=== Example 3: Create shopping carts with relationships ===")
    # Get the first user and product
    user = await User.first()
    product = await Product.first()
    
    # Create shopping cart with valid user_id and product_id
    cart = await ShoppingCart.insert({
        "user_id": user.id, 
        "product_id": product.id, 
        "quantity": 2
    })
    print(f"Created shopping cart: {cart.id} for user {user.username} and product {product.name}")
    
    # Example 4: Get with relationships
    print("\n=== Example 4: Get with relationships ===")
    # Get the cart with related user and product - using variable arguments syntax
    cart_with_rels = await ShoppingCart.get_with_related(cart.id, "user", "product")
    print(f"Cart {cart_with_rels.id}, User: {cart_with_rels.user.username}, Product: {cart_with_rels.product.name}")

    # Example 5: Create authors and books with relationships
    print("\n=== Example 5: Create authors and books with relationships ===")
    authors = await Author.insert([
        {"name": "George Orwell", "country": "UK", "birth_year": 1903},
        {"name": "J.K. Rowling", "country": "UK", "birth_year": 1965}
    ])
    print(f"Inserted authors: {[author.name for author in authors]}")
    
    # Create books with author relationship
    orwell = authors[0]
    rowling = authors[1]
    
    books = await Book.insert([
        {"title": "1984", "author_id": orwell.id, "published_year": 1949, "pages": 328},
        {"title": "Animal Farm", "author_id": orwell.id, "published_year": 1945, "pages": 112},
        {"title": "Harry Potter", "author_id": rowling.id, "published_year": 1997, "pages": 223}
    ])
    print(f"Inserted books: {[book.title for book in books]}")
    
    # Example 6: Retrieve with ordering
    print("\n=== Example 6: Retrieve with ordering ===")
    # Get books ordered by title (ascending order - default)
    books_by_title = await Book.all(order_by="title")
    print(f"Books ordered by title: {[book.title for book in books_by_title]}")
    
    # Get books ordered by published year descending
    books_by_year = await Book.all(order_by="-published_year")
    print(f"Books ordered by year (newest first): {[f'{book.title} ({book.published_year})' for book in books_by_year]}")
    
    # Multiple field ordering
    books_by_author_year = await Book.all(order_by=["author_id", "published_year"])
    print(f"Books by author and year: {[f'{book.title} (Author ID: {book.author_id}, Year: {book.published_year})' for book in books_by_author_year]}")

    # Example 7: Get authors with their books (relationship loading)
    print("\n=== Example 7: Get authors with their books ===")
    author_with_books = await Author.get_with_related(orwell.id, "books")
    print(f"Author: {author_with_books.name}, Books: {[book.title for book in author_with_books.books]}")

    # Example 8: Get by attribute with relationship loading
    print("\n=== Example 8: Get by attribute with relationship loading ===")
    # Use the enhanced get_by_attribute method with include_relationships parameter
    harry_potter = await Book.get_by_attribute(title="Harry Potter", all=False, include_relationships=True)
    if harry_potter and hasattr(harry_potter, 'author') and harry_potter.author:
        print(f"Book: {harry_potter.title}, Author: {harry_potter.author.name}")
    else:
        print(f"Book: {harry_potter.title}, Author not loaded")

    # Example 9: Using the new all() method with relationship loading
    print("\n=== Example 9: Using all() with relationship loading ===")
    all_books_with_authors = await Book.all(include_relationships=True)
    for book in all_books_with_authors:
        author_name = book.author.name if hasattr(book, 'author') and book.author else "Unknown"
        print(f"Book: {book.title}, Author: {author_name}")

    # Example 10: Update and delete
    print("\n=== Example 10: Update and delete ===")
    jane = await User.get_by_attribute(username="jane_doe", all=False)
    if jane:
        # Use the class method delete with criteria
        await User.delete({"username": "jane_doe"})
        print(f"Deleted user: {jane.username}")
    
    # Verify deletion
    all_users = await User.all()
    print(f"Remaining users: {[user.username for user in all_users]}")
    
    # Example 11: Create if not exists (custom get_or_create implementation)
    print("\n=== Example 11: Custom get_or_create implementation ===")
    
    # Define a custom get_or_create function for this example
    async def get_or_create(model_cls, search_criteria, defaults=None):
        """
        Get a record by criteria or create it if it doesn't exist.
        
        Args:
            model_cls: The model class
            search_criteria: Dictionary of search criteria
            defaults: Default values to use when creating a new record
            
        Returns:
            Tuple of (model instance, created flag)
        """
        # Try to find the record
        record = await model_cls.get_by_attribute(all=False, **search_criteria)
        
        if record:
            return record, False
        
        # Record not found, create it
        data = {**search_criteria}
        if defaults:
            data.update(defaults)
        
        new_record = await model_cls.insert(data)
        return new_record, True
    
    # Use our custom get_or_create function
    alice, created = await get_or_create(
        User, 
        {"username": "alice"}, 
        defaults={"email": "alice@example.com"}
    )
    status = "Created" if created else "Found existing"
    print(f"{status} user: {alice.username}")
    
    # Create again to show it finds the existing record
    alice2, created = await get_or_create(
        User,
        {"username": "alice"},
        defaults={"email": "different_email@example.com"}
    )
    status = "Created" if created else "Found existing"
    print(f"{status} user: {alice2.username}, Email: {alice2.email}")

    # Example 12: Using the limit() method with relationship loading
    print("\n=== Example 12: Using limit() with relationship loading ===")
    limited_books = await Book.limit(2, include_relationships=True, order_by="title")
    print(f"Limited books (2): {[book.title for book in limited_books]}")
    
    # Example 13: Using the first() method with ordering
    print("\n=== Example 13: Using first() method with ordering ===")
    # Get the oldest book (ordered by published year ascending)
    oldest_book = await Book.first(include_relationships=True, order_by="published_year")
    if oldest_book:
        author_name = oldest_book.author.name if hasattr(oldest_book, 'author') and oldest_book.author else "Unknown"
        print(f"Oldest book: {oldest_book.title} ({oldest_book.published_year}) by {author_name}")
    
    # Get the newest book (ordered by published year descending)
    newest_book = await Book.first(include_relationships=True, order_by="-published_year")
    if newest_book:
        author_name = newest_book.author.name if hasattr(newest_book, 'author') and newest_book.author else "Unknown"
        print(f"Newest book: {newest_book.title} ({newest_book.published_year}) by {author_name}")

if __name__ == "__main__":
    # Debug: Print relationship info for models immediately after setup

    # Run the examples
    asyncio.run(run_examples())
