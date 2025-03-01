"""
Example demonstrating the query methods in async-easy-model.

This example shows how to:
1. Use the all() method to retrieve all records
2. Use the first() method to retrieve the first record
3. Use the limit(x) method to retrieve a limited number of records
4. Use the order_by parameter to sort results in various ways
"""

import asyncio
import sys
from pathlib import Path
import os

# Add the parent directory to sys.path to import the package
sys.path.append(str(Path(__file__).parent.parent))

from sqlmodel import Field, Relationship
from typing import List, Optional
from datetime import date
from async_easy_model import EasyModel, init_db, db_config

# Configure SQLite for the example
db_config.configure_sqlite("query_example.db")

# Define a simple model for demonstration
class Product(EasyModel, table=True):
    """Product model for demonstration."""
    name: str = Field(index=True)
    price: float
    description: Optional[str] = None
    category: str = Field(index=True)

# Define models with relationships for ordering demonstration
class Category(EasyModel, table=True):
    """Category model for relationship ordering demonstration."""
    name: str = Field(index=True)
    display_order: int = Field(default=0)
    products: List["CategoryProduct"] = Relationship(back_populates="category")

class CategoryProduct(EasyModel, table=True):
    """Product with category relationship for ordering demonstration."""
    name: str = Field(index=True)
    price: float
    description: Optional[str] = None
    category_id: Optional[int] = Field(default=None, foreign_key="category.id")
    category: Optional[Category] = Relationship(back_populates="products")

async def run_example():
    """Run the example code demonstrating query methods."""
    print("Initializing database...")
    await init_db()
    
    # Create sample products
    print("\nCreating sample products...")
    products_data = [
        {"name": "Laptop", "price": 1200.00, "category": "Electronics", 
         "description": "High-performance laptop with 16GB RAM"},
        {"name": "Smartphone", "price": 800.00, "category": "Electronics", 
         "description": "Latest smartphone with 128GB storage"},
        {"name": "Headphones", "price": 150.00, "category": "Electronics", 
         "description": "Noise-cancelling wireless headphones"},
        {"name": "Coffee Maker", "price": 89.99, "category": "Kitchen", 
         "description": "Programmable coffee maker with timer"},
        {"name": "Blender", "price": 49.99, "category": "Kitchen", 
         "description": "High-speed blender for smoothies"},
        {"name": "Desk", "price": 199.99, "category": "Furniture", 
         "description": "Adjustable standing desk"},
        {"name": "Chair", "price": 129.99, "category": "Furniture", 
         "description": "Ergonomic office chair"},
        {"name": "Bookshelf", "price": 79.99, "category": "Furniture", 
         "description": "5-shelf bookcase for home or office"}
    ]
    
    # Insert products
    for data in products_data:
        await Product.insert(data)
    
    print(f"Created {len(products_data)} products")
    
    # Demonstrate all() method
    print("\nDemonstrating all() method...")
    all_products = await Product.all()
    print(f"Total products: {len(all_products)}")
    print("Products:")
    for product in all_products:
        print(f"- {product.name}: ${product.price:.2f} ({product.category})")
    
    # Demonstrate first() method
    print("\nDemonstrating first() method...")
    first_product = await Product.first()
    print(f"First product: {first_product.name} - ${first_product.price:.2f}")
    
    # Demonstrate limit() method
    print("\nDemonstrating limit() method...")
    limited_products = await Product.limit(3)
    print(f"First 3 products:")
    for product in limited_products:
        print(f"- {product.name}: ${product.price:.2f}")
    
    # Demonstrate get_by_attribute with all=True
    print("\nDemonstrating get_by_attribute with all=True...")
    electronics = await Product.get_by_attribute(all=True, category="Electronics")
    print(f"Electronics products ({len(electronics)}):")
    for product in electronics:
        print(f"- {product.name}: ${product.price:.2f}")
    
    # Demonstrate ordering by name (ascending)
    print("\nDemonstrating ordering by name (ascending)...")
    ordered_products = await Product.all(order_by="name")
    print("Products ordered by name:")
    for product in ordered_products:
        print(f"- {product.name}: ${product.price:.2f}")
    
    # Demonstrate ordering by price (descending)
    print("\nDemonstrating ordering by price (descending)...")
    expensive_first = await Product.all(order_by="-price")
    print("Products ordered by price (most expensive first):")
    for product in expensive_first:
        print(f"- {product.name}: ${product.price:.2f}")
    
    # Demonstrate ordering with get_by_attribute
    print("\nDemonstrating ordering with get_by_attribute...")
    furniture_by_price = await Product.get_by_attribute(
        all=True, 
        category="Furniture", 
        order_by="price"
    )
    print("Furniture products ordered by price (cheapest first):")
    for product in furniture_by_price:
        print(f"- {product.name}: ${product.price:.2f}")
    
    # Demonstrate first() with ordering
    print("\nDemonstrating first() with ordering...")
    cheapest = await Product.first(order_by="price")
    print(f"Cheapest product: {cheapest.name} - ${cheapest.price:.2f}")
    most_expensive = await Product.first(order_by="-price")
    print(f"Most expensive product: {most_expensive.name} - ${most_expensive.price:.2f}")
    
    # Demonstrate limit() with ordering
    print("\nDemonstrating limit() with ordering...")
    top_3_expensive = await Product.limit(3, order_by="-price")
    print("Top 3 most expensive products:")
    for product in top_3_expensive:
        print(f"- {product.name}: ${product.price:.2f}")
    
    # Create categories and products with relationships for relationship ordering demo
    print("\nSetting up relationship ordering demonstration...")
    
    # Create categories
    categories = [
        {"name": "Electronics", "display_order": 1},
        {"name": "Kitchen", "display_order": 2},
        {"name": "Furniture", "display_order": 3}
    ]
    
    category_objects = []
    for cat_data in categories:
        category = await Category.insert(cat_data)
        category_objects.append(category)
    
    # Create products with category relationships
    rel_products = [
        {"name": "Laptop", "price": 1200.00, "category_id": category_objects[0].id},
        {"name": "Smartphone", "price": 800.00, "category_id": category_objects[0].id},
        {"name": "Coffee Maker", "price": 89.99, "category_id": category_objects[1].id},
        {"name": "Desk", "price": 199.99, "category_id": category_objects[2].id},
        {"name": "Chair", "price": 129.99, "category_id": category_objects[2].id}
    ]
    
    for prod_data in rel_products:
        await CategoryProduct.insert(prod_data)
    
    # Demonstrate ordering by relationship field
    print("\nDemonstrating ordering by relationship field...")
    
    # Order products by category name
    products_by_category = await CategoryProduct.all(
        include_relationships=True,
        order_by="category.name"
    )
    
    print("Products ordered by category name:")
    for product in products_by_category:
        print(f"- {product.name}: ${product.price:.2f} (Category: {product.category.name})")
    
    # Order products by category display order
    products_by_display_order = await CategoryProduct.all(
        include_relationships=True,
        order_by="category.display_order"
    )
    
    print("\nProducts ordered by category display order:")
    for product in products_by_display_order:
        print(f"- {product.name}: ${product.price:.2f} (Category: {product.category.name}, Order: {product.category.display_order})")
    
    # Clean up - delete all products and categories
    print("\nCleaning up...")
    all_products = await Product.all()
    for product in all_products:
        await Product.delete(product.id)
    
    all_cat_products = await CategoryProduct.all()
    for product in all_cat_products:
        await CategoryProduct.delete(product.id)
    
    all_categories = await Category.all()
    for category in all_categories:
        await Category.delete(category.id)
    
    # Verify deletion
    remaining_products = await Product.all()
    remaining_cat_products = await CategoryProduct.all()
    remaining_categories = await Category.all()
    print(f"Remaining products after cleanup: {len(remaining_products)}")
    print(f"Remaining category products after cleanup: {len(remaining_cat_products)}")
    print(f"Remaining categories after cleanup: {len(remaining_categories)}")

if __name__ == "__main__":
    asyncio.run(run_example())
