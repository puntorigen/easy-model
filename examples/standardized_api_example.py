"""
Example demonstrating the standardized API for async-easy-model.
This shows the new, more convenient methods for common database operations.
"""

import asyncio
from async_easy_model import EasyModel, init_db, db_config, Field
from typing import Optional, List
from datetime import datetime

# Configure the database
db_config.configure_sqlite(":memory:")

# Define models
class User(EasyModel, table=True):
    username: str = Field(unique=True)
    email: str
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default=datetime.now)

class Product(EasyModel, table=True):
    name: str = Field(unique=True)
    description: Optional[str] = Field(default=None)
    price: float

class ShoppingCart(EasyModel, table=True):
    user_id: int = Field(foreign_key="User.id")
    product_id: int = Field(foreign_key="Product.id")
    quantity: int

async def run_examples():
    # Initialize the database
    print("Initializing database...")
    await init_db()
    
    # Example 1: Create users with insert method
    print("\n=== Example 1: Insert users ===")
    users = await User.insert([
        {
            "username": "john_doe",
            "email": "john@example.com"
        },
        {
            "username": "jane_doe",
            "email": "jane@example.com"
        }
    ])
    print(f"Created {len(users)} users")
    
    # Example 2: Select users
    print("\n=== Example 2: Select users ===")
    # Select all users
    all_users = await User.all()
    print(f"All users: {[user.username for user in all_users]}")
    
    # Select a single user by criteria
    user = await User.select({"username": "john_doe"})
    print(f"Selected user: {user.username}")
    
    # Example 3: Select with wildcard pattern
    print("\n=== Example 3: Select with wildcard pattern ===")
    users_with_domain = await User.select({"email": "*@example.com"}, all=True)
    print(f"Users with example.com email: {[user.username for user in users_with_domain]}")
    
    # Example 3b: Select with first parameter
    print("\n=== Example 3b: Select with first parameter ===")
    first_active_user = await User.select({"is_active": True}, first=True)
    print(f"First active user: {first_active_user.username}")
    
    # Example 3c: Select with order_by and limit
    print("\n=== Example 3c: Select with order_by and limit ===")
    newest_users = await User.select({}, order_by="-created_at", limit=2)  # No need to specify all=True
    print(f"Newest users: {[user.username for user in newest_users]}")
    
    # Example 3d: Using limit without explicitly setting all=True
    print("\n=== Example 3d: Using limit automatically sets all=True ===")
    limited_users = await User.select({}, limit=2)  # This will return a list because limit > 1
    print(f"Got {len(limited_users)} users automatically because limit > 1")
    
    # Example 4: Update user
    print("\n=== Example 4: Update user ===")
    updated_user = await User.update(
        {"email": "john.updated@example.com"},
        {"username": "john_doe"}
    )
    print(f"Updated user email: {updated_user.email}")
    
    # Example 5: Create products
    print("\n=== Example 5: Create products ===")
    products = await Product.insert([
        {
            "name": "Product 1",
            "description": "Description 1",
            "price": 10.0
        },
        {
            "name": "Product 2",
            "description": "Description 2",
            "price": 20.0
        }
    ])
    print(f"Created {len(products)} products")
    
    # Example 6: Add items to shopping cart
    print("\n=== Example 6: Add items to shopping cart with relationships ===")
    # Using direct foreign key references
    cart_item1 = await ShoppingCart.insert({
        "user_id": users[0].id,
        "product_id": products[0].id,
        "quantity": 2
    })
    
    # Using nested dictionaries to lookup relationships
    cart_item2 = await ShoppingCart.insert({
        "user": {
            "username": "jane_doe"
        },
        "product": {
            "name": "Product 2"
        },
        "quantity": 1
    })  # include_relationships=True is now the default!
    
    print(f"Created cart item with quantity: {cart_item1.quantity}")
    print(f"Created cart item with related user: {cart_item2.user.username}")
    print(f"Created cart item with related product: {cart_item2.product.name}")
    
    # Example 7: Select with ordering
    print("\n=== Example 7: Select with ordering ===")
    # Order by price descending
    expensive_products = await Product.select(all=True, order_by="-price")
    print("Products ordered by price (desc):")
    for product in expensive_products:
        print(f"  {product.name}: ${product.price}")
    
    # Example 8: Delete records
    print("\n=== Example 8: Delete records ===")
    deleted_count = await User.delete({"username": "jane_doe"})
    print(f"Deleted {deleted_count} user(s)")
    
    # Verify deletion
    remaining_users = await User.all()
    print(f"Remaining users: {[user.username for user in remaining_users]}")

if __name__ == "__main__":
    asyncio.run(run_examples())
