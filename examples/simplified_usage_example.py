"""
Simplified Usage Example for async-easy-model

This example demonstrates the simplified API usage without requiring explicit 
relationship management calls, as per planned_usage.md
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Optional, List

from sqlmodel import Field
from async_easy_model import EasyModel, db_config, init_db

# Configure logging
logging.basicConfig(level=logging.INFO)

# Define models according to the planned usage
class Users(EasyModel, table=True):
    username: str = Field(unique=True)
    email: str
    # Note: id, created_at and updated_at fields are automatically included
    # and managed by EasyModel

class Products(EasyModel, table=True):
    name: str = Field(unique=True)
    description: Optional[str] = Field(default=None)
    price: float

class ShoppingCart(EasyModel, table=True):
    user_id: int = Field(foreign_key="users.id")
    product_id: int = Field(foreign_key="products.id")
    quantity: int = Field(default=1)

# Configure SQLite database
os.environ["SQLITE_FILE"] = "./test_auto_rel2.db"
db_config.configure_sqlite("./test_auto_rel2.db")

async def main():
    print("=== Simplified Usage Example for async-easy-model ===\n")
    
    # Initialize database
    print("Initializing database...")
    # Just initialize the database since auto-relationships are enabled by default
    await init_db()
    print("Database initialized\n")

    # Example 1: Insert users
    print("=== Example 1: Insert users ===")
    try:
        # Try to select first to avoid duplication
        existing_user = await Users.select({"username": "john_doe"})
        if not existing_user:
            # Insert if not exists
            john = await Users.insert({
                "username": "john_doe",
                "email": "john@example.com"
            })
            print(f"User {john.username}: Created")
        else:
            print(f"User john_doe: Already existed")

        # Try another user
        existing_user = await Users.select({"username": "jane_doe"})
        if not existing_user:
            # Insert if not exists
            jane = await Users.insert({
                "username": "jane_doe",
                "email": "jane@example.com"
            })
            print(f"User {jane.username}: Created")
        else:
            print(f"User jane_doe: Already existed")
        print()
    except Exception as e:
        print(f"User insertion error: {e}\n")

    # Example 2: Select all users
    print("=== Example 2: Select all users ===")
    all_users = await Users.all()
    print(f"All users: {[user.username for user in all_users]}\n")

    # Example 3: Search a user by username
    print("=== Example 3: Search a user by username ===")
    user = await Users.select({"username": "john_doe"})
    if user:
        print(f"Found user: {user.username}, Email: {user.email}\n")
    else:
        print("User not found\n")

    # Example 4: Get users by email domain (LIKE query)
    print("=== Example 4: Get users by email domain (LIKE query) ===")
    users_with_example_email = await Users.select({"email": "*@example.com"}, all=True)
    print(f"Users with example.com email: {[user.username for user in users_with_example_email]}\n")

    # Example 5: Update a user
    print("=== Example 5: Update a user ===")
    try:
        # Use a timestamp to guarantee uniqueness
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        updated_user = await Users.update(
            {"username": f"john_updated_{timestamp}", "email": "john_updated@example.com"},
            {"username": "john_doe"}
        )
        print(f"Updated user: {updated_user.username}, Email: {updated_user.email}\n")
    except Exception as e:
        print(f"Update failed: {e}\n")

    # Example 6: Insert products
    print("=== Example 6: Insert products ===")
    try:
        # Check if products exist first
        product1 = await Products.select({"name": "Product 1"})
        if not product1:
            # Insert if not exists
            product1 = await Products.insert({
                "name": "Product 1",
                "description": "Description for product 1",
                "price": 10.99
            })
            print(f"Product {product1.name}: Created")
        else:
            print(f"Product 1: Already existed")
        
        product2 = await Products.select({"name": "Product 2"})
        if not product2:
            # Insert if not exists
            product2 = await Products.insert({
                "name": "Product 2",
                "description": "Description for product 2",
                "price": 24.99
            })
            print(f"Product {product2.name}: Created")
        else:
            print(f"Product 2: Already existed")
        print()
    except Exception as e:
        print(f"Product insertion error: {e}\n")

    # Example 7: Insert a product to cart with relationship
    print("=== Example 7: Insert cart item with relationships ===")
    try:
        # Select existing user and product
        jane = await Users.select({"username": "jane_doe"})
        
        # Create a new product for this example
        product3 = await Products.select({"name": "Product 3"})
        if not product3:
            product3 = await Products.insert({
                "name": "Product 3",
                "description": "Description for product 3",
                "price": 15.50
            })
        
        # Create a cart item with the existing IDs
        cart_item = await ShoppingCart.insert({
            "user_id": jane.id,
            "product_id": product3.id,
            "quantity": 2
        })
        print(f"Added to cart: {cart_item.quantity} x Product (ID: {cart_item.product_id}) for User (ID: {cart_item.user_id})")
        
        # Fetch the cart item with relationships included
        cart_with_relations = await ShoppingCart.select(
            criteria={"id": cart_item.id}, 
            include_relationships=True
        )
        if cart_with_relations:
            print(f"Cart item details: {cart_with_relations.quantity} x {cart_with_relations.product.name} for {cart_with_relations.user.username}\n")
    except Exception as e:
        print(f"Cart item creation error: {e}\n")

    # Example 8: Insert cart item with existing IDs
    print("=== Example 8: Insert cart item with existing IDs ===")
    try:
        # Get references to existing users and products - more reliably
        users = await Users.all()
        if not users:
            print("No users found in database")
            raise ValueError("No users found")
        
        # Use the first available user
        john = users[0]
        
        # Get a reference to Product 2
        product2 = await Products.select({"name": "Product 2"})
        if not product2:
            print("Product 2 not found")
            raise ValueError("Product not found")
        
        # Create the cart item with their IDs
        cart_item2 = await ShoppingCart.insert({
            "user_id": john.id,
            "product_id": product2.id,
            "quantity": 1
        })
        print(f"Added to cart: {cart_item2.quantity} x Product (ID: {cart_item2.product_id}) for User (ID: {cart_item2.user_id})")
        
        # Fetch the cart item with relationships included
        cart_with_relations2 = await ShoppingCart.select(
            criteria={"id": cart_item2.id}, 
            include_relationships=True
        )
        if cart_with_relations2:
            print(f"Cart item details: {cart_with_relations2.quantity} x {cart_with_relations2.product.name} for {cart_with_relations2.user.username}\n")
    except Exception as e:
        print(f"Cart item creation error: {e}\n")

    # Example 9: Get cart items with relationships included
    print("\n=== Example 9: Get cart items with relationships ===")
    try:
        # Get jane's reference
        jane = await Users.select({"username": "jane_doe"})
        
        # Get all cart items for jane with relationships included
        jane_cart = await ShoppingCart.select({"user_id": jane.id}, all=True, include_relationships=True)
        
        print(f"Jane's cart items:")
        for item in jane_cart:
            print(f"  - {item.quantity} x {item.product.name} (${item.product.price})")
    except Exception as e:
        print(f"Error retrieving cart items: {e}\n")

    # Example 10: Delete a product
    print("\n=== Example 10: Delete a product ===")
    try:
        # First, create a product specifically for deletion that isn't referenced by any cart items
        new_product = await Products.insert({
            "name": "Temporary Product", 
            "description": "This product will be deleted", 
            "price": 5.99
        })
        
        # Now we can safely delete it
        result = await Products.delete({"name": "Temporary Product"})
        print(f"Deleted {result} product(s) with name 'Temporary Product'")
        
        # Try to delete a product that has references (will fail due to integrity constraints)
        try:
            result = await Products.delete({"name": "Product 3"})
            print(f"Deleted {result} product(s) with name 'Product 3'")
        except Exception as e:
            print(f"Expected error when deleting referenced product: Foreign key constraint prevents deletion")
        
        # Verify the deletion results
        remaining_products = await Products.all()
        print(f"Remaining products: {[p.name for p in remaining_products]}")
    except Exception as e:
        print(f"Error during product operations: {e}\n")

    # Example 11: Demonstrate all() method with relationships
    print("\n=== Example 11: Using all() method with relationships ===")
    try:
        # Get all products with relationships included
        all_products = await Products.all(include_relationships=True)
        
        print(f"All products with their shopping cart references:")
        for product in all_products:
            print(f"  - {product.name} (${product.price}) - in {len(product.shoppingcarts)} shopping carts")
    except Exception as e:
        print(f"Error retrieving all products: {e}\n")

    # Example 12: Demonstrate first() method
    print("\n=== Example 12: Using first() method ===")
    try:
        # Get the first user record
        first_user = await Users.first()
        print(f"First user in database: {first_user.username}")
        
        # Get the first user with relationships
        first_user_with_relations = await Users.first(include_relationships=True)
        cart_count = len(first_user_with_relations.shoppingcarts) if hasattr(first_user_with_relations, 'shoppingcarts') else 0
        print(f"First user {first_user_with_relations.username} has {cart_count} items in their cart")
    except Exception as e:
        print(f"Error retrieving first user: {e}\n")

    # Example 13: Demonstrate limit() method with ordering
    print("\n=== Example 13: Using limit() with ordering ===")
    try:
        # Create some additional users with timestamps to demonstrate ordering
        for i in range(3):
            await Users.insert({
                "username": f"ordered_user_{i}",
                "email": f"ordered{i}@example.com"
            })
            
        # Get the 5 most recently created users (order by created_at in descending order)
        recent_users = await Users.limit(5, order_by="-created_at")
        print(f"5 most recent users (newest first):")
        for user in recent_users:
            print(f"  - {user.username} (created at {user.created_at})")
            
        # Get the 3 oldest users (order by created_at in ascending order)
        oldest_users = await Users.limit(3, order_by="created_at")
        print(f"\n3 oldest users:")
        for user in oldest_users:
            print(f"  - {user.username} (created at {user.created_at})")
    except Exception as e:
        print(f"Error demonstrating ordering: {e}\n")

if __name__ == "__main__":
    asyncio.run(main())
