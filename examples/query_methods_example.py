"""
Example demonstrating the query methods in async-easy-model.

This example shows how to:
1. Use the all() method to retrieve all records
2. Use the first() method to retrieve the first record
3. Use the limit(x) method to retrieve a limited number of records
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
    
    # Demonstrate combination of methods
    print("\nDemonstrating combination with get_by_attribute...")
    # Get first 2 furniture items
    furniture = await Product.get_by_attribute(all=True, category="Furniture")
    print(f"All furniture products ({len(furniture)}):")
    for product in furniture:
        print(f"- {product.name}: ${product.price:.2f}")
    
    # Clean up - delete all products
    print("\nCleaning up...")
    for product in all_products:
        await Product.delete(product.id)
    
    # Verify deletion
    remaining = await Product.all()
    print(f"Remaining products after cleanup: {len(remaining)}")

if __name__ == "__main__":
    asyncio.run(run_example())
