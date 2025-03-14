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
os.environ["SQLITE_FILE"] = "./test_auto_rel3.db"
db_config.configure_sqlite("./test_auto_rel3.db")

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
    all_users = await Users.select(criteria={}, all=True)
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
        users = await Users.select(criteria={}, all=True)
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

    # Example 9: Insert cart item with nested relationships
    print("=== Example 9: Insert cart item with nested relationships ===")
    try:
        # First, try to check if the nested user already exists
        existing_nested_user = await Users.select(criteria={"username": "nested_user"}, first=True)
        if existing_nested_user:
            print(f"Found existing nested user with username: {existing_nested_user.username}")
            # First delete any shopping cart records that use this user
            await ShoppingCart.delete({"user_id": existing_nested_user.id})
            print("Deleted existing cart items for nested_user")
            # Now delete the user
            await Users.delete({"username": "nested_user"})
            print("Deleted existing nested_user to start fresh")
        
        # Generate a unique product name with timestamp
        from datetime import datetime as dt
        timestamp = dt.now().strftime("%Y%m%d%H%M%S")
        unique_product_name = f"Nested Product {timestamp}"
        
        # Try creating a cart item with nested user and product objects
        cart_item3 = await ShoppingCart.insert({
            "user": {
                "username": "nested_user",
                "email": "nested@example.com"
            }, 
            "product": {
                "name": unique_product_name,
                "description": "This is a nested product",
                "price": 15.99
            },
            "quantity": 3
        })
        
        # Fetch and verify
        cart_with_nested = await ShoppingCart.select(
            criteria={"id": cart_item3.id}, 
            include_relationships=True
        )
        if cart_with_nested:
            print(f"Added to cart using nested relationships!")
            print(f"Nested cart item details: {cart_with_nested.quantity} x {cart_with_nested.product.name} for {cart_with_nested.user.username}")
            print(f"Product price: ${cart_with_nested.product.price}")
            print(f"User email: {cart_with_nested.user.email}\n")
    except Exception as e:
        print(f"Nested relationship cart creation error: {e}\n")
        
    # Example 10: Reusing existing records with nested relationships
    print("=== Example 10: Reusing existing records with nested relationships ===")
    try:
        # First, let's verify the existing user is present
        existing_user = await Users.select(criteria={"username": "nested_user"}, first=True)
        if existing_user:
            print(f"Found existing user: {existing_user.username} with email: {existing_user.email}")
            
            # Instead of trying to update a unique field, let's first update the user
            # Then use the updated user in the cart
            await Users.update(
                criteria={"username": "nested_user"},
                data={"email": "modified@example.com"}
            )
            print(f"Updated user email separately")
            
            # Generate a unique product name with timestamp for testing reuse
            from datetime import datetime as dt
            timestamp = dt.now().strftime("%Y%m%d%H%M%S")
            unique_product_name2 = f"Another Product {timestamp}"
            
            # Now try to create a cart with the same username but different email
            # This should reuse the existing user without trying to modify it
            cart_item4 = await ShoppingCart.insert({
                "user_id": existing_user.id,  # Use ID directly instead of nested object
                "product": {
                    "name": unique_product_name2,
                    "description": "This is a different product",
                    "price": 25.50
                },
                "quantity": 1
            })
            
            # Fetch and verify
            cart_with_reused = await ShoppingCart.select(
                criteria={"id": cart_item4.id}, 
                include_relationships=True
            )
            
            # Check if the user was reused
            if cart_with_reused:
                print(f"Reused relationship cart: {cart_with_reused.quantity} x {cart_with_reused.product.name}")
                print(f"User email was updated: {cart_with_reused.user.email}")
                print(f"User ID remained the same: {cart_with_reused.user.id == existing_user.id}")
            
            # Verify the user record directly
            updated_user = await Users.select(criteria={"username": "nested_user"}, first=True)
            if updated_user:
                print(f"Updated user email: {updated_user.email}")
        else:
            print("Could not find the existing 'nested_user' record to test reuse functionality")
    except Exception as e:
        print(f"Reused relationship cart creation error: {e}\n")

    # Example 11: Get cart items with relationships included
    print("\n=== Example 11: Get cart items with relationships ===")
    try:
        # Get jane's reference
        jane = await Users.select({"username": "jane_doe"})
        print(f"Jane's direct object with select:",jane.to_dict())
        
        # Get all cart items for jane with relationships included
        jane_cart = await ShoppingCart.select({"user_id": jane.id}, all=True, include_relationships=True)
        
        print(f"Jane's cart items:")
        for item in jane_cart:
            print(f"  - {item.quantity} x {item.product.name} (${item.product.price})")
    except Exception as e:
        print(f"Error retrieving cart items: {e}\n")

    # Example 12: Delete a product (with cascade delete)
    print("\n=== Example 12: Delete a product ===")
    try:
        # Generate a unique product name for this example
        from datetime import datetime as dt
        timestamp = dt.now().strftime("%Y%m%d%H%M%S")
        temp_product_name = f"Temporary Product {timestamp}"
        
        # Create product to delete
        temp_product = await Products.insert({
            "name": temp_product_name,
            "description": "This product will be deleted",
            "price": 5.99
        })
        print(f"Created temporary product: {temp_product_name}")
        
        # Create cart item for the temporary product
        await ShoppingCart.insert({
            "user_id": 1,  # Using john_updated
            "product_id": temp_product.id,
            "quantity": 1
        })
        print(f"Added temporary product to a cart")
        
        # Now try to delete the product
        # This should cascade delete the associated cart items
        await Products.delete({"id": temp_product.id})
        print(f"Deleted temporary product and associated cart items")
        
        # Verify the product is gone
        deleted_product = await Products.select(criteria={"id": temp_product.id}, first=True)
        if deleted_product is None:
            print(f"Successfully deleted the product")
        else:
            print(f"Failed to delete the product")
            
    except Exception as e:
        print(f"Error during product operations: {e}")
        
    # Example 13: Demonstrate all() method with relationships
    print("\n=== Example 13: Using all() method with relationships ===")
    try:
        # Get all products with relationships included
        all_products = await Products.select(criteria={}, include_relationships=True, all=True)
        
        print(f"All products with their shopping cart references:")
        for product in all_products:
            print(f"  - {product.name} (${product.price}) - in {len(product.shoppingcarts)} shopping carts")
    except Exception as e:
        print(f"Error retrieving all products: {e}\n")

    # Example 14: Demonstrate first() method
    print("\n=== Example 14: Using first() method ===")
    try:
        # Get the first user in the database
        first_user = await Users.select(criteria={}, first=True)
        print(f"First user in database: {first_user.username}")
        
        # Get with relationships
        first_user_with_relations = await Users.select(criteria={}, first=True, include_relationships=True)
        print(f"First user {first_user.username} has {len(first_user_with_relations.shoppingcarts)} items in their cart")
    except Exception as e:
        print(f"Error demonstrating first: {e}")
        
    # Example 15: Demonstrate limit() method with ordering
    print("\n=== Example 15: Using limit() with ordering ===")
    try:
        # Create some users with different timestamps
        for i in range(3):
            await Users.insert({
                "username": f"ordered_user_{dt.now().strftime('%Y%m%d%H%M%S')}_{i}",
                "email": f"ordered{i}@example.com"
            })
        
        print("5 most recent users:")
        recent_users = await Users.select(
            criteria={},
            all=True,
            order_by="-created_at",
            limit=5
        )
        
        for user in recent_users:
            print(f"  - {user.username} (created: {user.created_at})")
            
        print("\n3 oldest users:")
        oldest_users = await Users.select(
            criteria={},
            all=True,
            order_by="created_at",
            limit=3
        )
        
        for user in oldest_users:
            print(f"  - {user.username} (created: {user.created_at})")
    except Exception as e:
        print(f"Error demonstrating ordering: {e}")
        
    # Example 16: Test to_dict with different max_depth values
    print("\n=== Example 16: Test to_dict with different max_depth values ===")
    try:
        # Get a shopping cart item with relationships included
        # When include_relationships=True, relationships are eagerly loaded
        cart_item = await ShoppingCart.first(include_relationships=True)
        
        if cart_item:
            # Test with different max_depth values
            print("Default max_depth (4):")
            default_dict = cart_item.to_dict()
            print(f"  - Cart item ID: {default_dict.get('id')}")
            print(f"  - User username: {default_dict.get('user', {}).get('username')}")
            print(f"  - Product name: {default_dict.get('product', {}).get('name')}")
            
            print("\nmax_depth=1:")
            depth1_dict = cart_item.to_dict(max_depth=1)
            print(f"  - Cart item ID: {depth1_dict.get('id')}")
            print(f"  - User present: {'Yes' if 'user' in depth1_dict else 'No'}")
            print(f"  - User has data: {'Yes' if depth1_dict.get('user') != {} else 'No'}")
            
            print("\nmax_depth=0:")
            depth0_dict = cart_item.to_dict(max_depth=0)
            print(f"  - Cart item ID: {depth0_dict.get('id')}")
            print(f"  - User present: {'Yes' if 'user' in depth0_dict else 'No'}")
            
            print("\nInclude relationships=False:")
            no_rel_dict = cart_item.to_dict(include_relationships=False)
            print(f"  - Cart item ID: {no_rel_dict.get('id')}")
            print(f"  - User present: {'Yes' if 'user' in no_rel_dict else 'No'}")
        else:
            print("No cart items found to test.")
        
    except Exception as e:
        print(f"Error testing to_dict: {e}\n")

if __name__ == "__main__":
    asyncio.run(main())
