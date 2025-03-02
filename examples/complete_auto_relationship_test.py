"""
Complete test of automatic relationship detection in async-easy-model.
This example demonstrates both explicit and automatic relationship approaches.
"""

import os
import asyncio
import sys
from sqlmodel import Field, SQLModel
from typing import List, Optional

# Ensure we're using the local package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from async_easy_model.model import EasyModel, init_db, db_config
from async_easy_model.auto_relationships import enable_auto_relationships

# Configure SQLite for the test
db_config.configure_sqlite("./complete_auto_rel_test.db")

# Enable auto relationships
enable_auto_relationships()

# 1. Models with explicit relationships (using SQLModel's Relationship)
class Category(EasyModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str

class Product(EasyModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    price: float
    category_id: Optional[int] = Field(default=None, foreign_key="category.id")

# 2. Models with automatic relationships (only define foreign key)
class Author(EasyModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str

class Book(EasyModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    author_id: Optional[int] = Field(default=None, foreign_key="author.id")
    
async def run_test():
    """Run the complete relationship test."""
    print("=== Complete Auto-Relationship Test ===")
    print(f"Using database: {db_config.get_connection_url()}")
    
    # Initialize database and create tables
    await init_db()
    
    engine = db_config.get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)
    
    print("\n=== Testing Explicit Relationships ===")
    try:
        # Create category and product
        category = await Category.insert({"name": "Electronics"})
        product = await Product.insert({
            "name": "Smartphone", 
            "price": 599.99, 
            "category_id": category.id
        })
        
        # Retrieve with relationships
        retrieved_product = await Product.get_by_id(product.id, include_relationships=True)
        if hasattr(retrieved_product, "category") and retrieved_product.category:
            print(f"✅ Product: {retrieved_product.name} - Category: {retrieved_product.category.name}")
        else:
            print(f"❌ Product: {retrieved_product.name} - No category relationship loaded")
        
        retrieved_category = await Category.get_by_id(category.id, include_relationships=True)
        if hasattr(retrieved_category, "products") and retrieved_category.products:
            print(f"✅ Category: {retrieved_category.name} - Products:")
            for prod in retrieved_category.products:
                print(f"  - {prod.name} (${prod.price})")
        else:
            print(f"❌ Category: {retrieved_category.name} - No products relationship loaded")
            
    except Exception as e:
        print(f"Error testing explicit relationships: {e}")
    
    print("\n=== Testing Automatic Relationships ===")
    try:
        # Create author and book
        author = await Author.insert({"name": "Jane Doe"})
        book = await Book.insert({
            "title": "The Art of Programming", 
            "author_id": author.id
        })
        
        # Retrieve with relationships
        retrieved_book = await Book.get_by_id(book.id, include_relationships=True)
        has_author_attr = hasattr(retrieved_book, "author")
        author_loaded = has_author_attr and retrieved_book.author is not None
        
        if author_loaded:
            print(f"✅ Book: {retrieved_book.title} - Author: {retrieved_book.author.name}")
        else:
            print(f"❌ Book: {retrieved_book.title} - " + 
                  (f"Has author attribute but not loaded" if has_author_attr else "No author attribute"))
        
        retrieved_author = await Author.get_by_id(author.id, include_relationships=True)
        has_books_attr = hasattr(retrieved_author, "books")
        books_loaded = has_books_attr and retrieved_author.books is not None and len(retrieved_author.books) > 0
        
        if books_loaded:
            print(f"✅ Author: {retrieved_author.name} - Books:")
            for b in retrieved_author.books:
                print(f"  - {b.title}")
        else:
            print(f"❌ Author: {retrieved_author.name} - " + 
                  (f"Has books attribute but empty/not loaded" if has_books_attr else "No books attribute"))
            
        # Additional diagnostics
        print("\n=== Relationship Diagnostics ===")
        if hasattr(Book, "__sqlmodel_relationships__"):
            rel_names = list(Book.__sqlmodel_relationships__.keys())
            print(f"Book SQLModel relationships: {rel_names}")
        else:
            print("Book has no __sqlmodel_relationships__ attribute")
            
        if hasattr(Author, "__sqlmodel_relationships__"):
            rel_names = list(Author.__sqlmodel_relationships__.keys())
            print(f"Author SQLModel relationships: {rel_names}")
        else:
            print("Author has no __sqlmodel_relationships__ attribute")
            
        # Try to force process the relationships
        from async_easy_model.auto_relationships import process_all_models_for_relationships
        print("\n=== Forcing relationship processing ===")
        process_all_models_for_relationships()
        
        # Check again after forcing
        print("\n=== Relationships after forced processing ===")
        if hasattr(Book, "__sqlmodel_relationships__"):
            rel_names = list(Book.__sqlmodel_relationships__.keys())
            print(f"Book SQLModel relationships: {rel_names}")
        else:
            print("Book has no __sqlmodel_relationships__ attribute")
            
        if hasattr(Author, "__sqlmodel_relationships__"):
            rel_names = list(Author.__sqlmodel_relationships__.keys())
            print(f"Author SQLModel relationships: {rel_names}")
        else:
            print("Author has no __sqlmodel_relationships__ attribute")
            
    except Exception as e:
        print(f"Error testing automatic relationships: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Close the engine
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(run_test())
