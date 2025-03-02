"""
Comprehensive example of automatic relationship detection in async-easy-model.

This example demonstrates:
1. Basic auto relationship detection
2. Working with SQLite database
3. Creating and querying records with relationships
4. Using the various query methods (get_by_id, all, first, limit) with relationships
5. Ordering query results

Run this example to see automatic relationships in action.
"""

import os
import sys
import asyncio
from sqlmodel import Field, SQLModel, Relationship
from typing import List, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

# Ensure we're using the local package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from async_easy_model.model import EasyModel, init_db, db_config
from async_easy_model.auto_relationships import enable_auto_relationships

# Configure SQLite database
db_config.configure_sqlite("./comprehensive_example.db")

# Enable auto relationships
enable_auto_relationships()

# Define models with foreign key relationships
class Category(EasyModel, table=True):
    """Category model with auto-relationship to products."""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True)
    description: Optional[str] = None
    
    # Explicitly define the relationship
    products: List["Product"] = Relationship(back_populates="category")

class Supplier(EasyModel, table=True):
    """Supplier model with auto-relationship to products."""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    contact_email: str = Field(unique=True)
    phone: Optional[str] = None
    
    # Explicitly define the relationship
    products: List["Product"] = Relationship(back_populates="supplier")

class Product(EasyModel, table=True):
    """Product model with foreign keys to Category and Supplier."""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    price: float
    stock: int = 0
    category_id: Optional[int] = Field(default=None, foreign_key="category.id")
    supplier_id: Optional[int] = Field(default=None, foreign_key="supplier.id")
    
    # Explicitly define the relationships
    category: Optional[Category] = Relationship(back_populates="products")
    supplier: Optional[Supplier] = Relationship(back_populates="products")

class OrderItem(EasyModel, table=True):
    """Order item with foreign key to Product."""
    id: Optional[int] = Field(default=None, primary_key=True)
    quantity: int
    product_id: int = Field(foreign_key="product.id")
    order_id: int = Field(foreign_key="order.id")
    
    # Explicitly define the relationships
    product: Product = Relationship(back_populates="orderitems")
    order: "Order" = Relationship(back_populates="orderitems")

class Order(EasyModel, table=True):
    """Order model with auto-relationship to order items."""
    id: Optional[int] = Field(default=None, primary_key=True)
    order_date: str
    customer_name: str
    total_amount: float
    
    # Explicitly define the relationship
    orderitems: List[OrderItem] = Relationship(back_populates="order")

async def setup_database():
    """Initialize the database and create tables."""
    await init_db()
    
    # Create tables
    engine = db_config.get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)
    
    print("Database setup complete.")
    return engine

async def create_test_data():
    """Create test data in the database."""
    # Create categories
    electronics = await Category.insert({
        "name": "Electronics", 
        "description": "Electronic devices and gadgets"
    })
    
    clothing = await Category.insert({
        "name": "Clothing", 
        "description": "Apparel and fashion items"
    })
    
    # Create suppliers
    acme = await Supplier.insert({
        "name": "Acme Corporation", 
        "contact_email": "contact@acme.com", 
        "phone": "555-1234"
    })
    
    globex = await Supplier.insert({
        "name": "Globex Industries", 
        "contact_email": "info@globex.com", 
        "phone": "555-5678"
    })
    
    # Create products
    laptop = await Product.insert({
        "name": "Laptop Pro", 
        "price": 1299.99, 
        "stock": 50, 
        "category_id": electronics.id, 
        "supplier_id": acme.id
    })
    
    smartphone = await Product.insert({
        "name": "SmartPhone X", 
        "price": 799.99, 
        "stock": 100, 
        "category_id": electronics.id, 
        "supplier_id": acme.id
    })
    
    tshirt = await Product.insert({
        "name": "Cotton T-Shirt", 
        "price": 19.99, 
        "stock": 200, 
        "category_id": clothing.id, 
        "supplier_id": globex.id
    })
    
    jeans = await Product.insert({
        "name": "Denim Jeans", 
        "price": 49.99, 
        "stock": 75, 
        "category_id": clothing.id, 
        "supplier_id": globex.id
    })
    
    # Create orders
    order1 = await Order.insert({
        "order_date": "2023-05-01", 
        "customer_name": "John Doe", 
        "total_amount": 1319.98
    })
    
    order2 = await Order.insert({
        "order_date": "2023-05-02", 
        "customer_name": "Jane Smith", 
        "total_amount": 869.97
    })
    
    # Create order items
    await OrderItem.insert({
        "quantity": 1, 
        "product_id": laptop.id, 
        "order_id": order1.id
    })
    
    await OrderItem.insert({
        "quantity": 1, 
        "product_id": tshirt.id, 
        "order_id": order1.id
    })
    
    await OrderItem.insert({
        "quantity": 1, 
        "product_id": smartphone.id, 
        "order_id": order2.id
    })
    
    await OrderItem.insert({
        "quantity": 1, 
        "product_id": jeans.id, 
        "order_id": order2.id
    })
    
    print("Test data created successfully.")

async def demonstrate_relationships():
    """Demonstrate auto-relationship features."""
    print("\n=== Testing Relationships ===")
    
    # 1. Get a category with its products
    electronics = await Category.get_by_attribute(name="Electronics", include_relationships=True, all=True)
    if electronics:
        electronics = electronics[0]
        print(f"\nCategory: {electronics.name}")
        print(f"Products in {electronics.name}:")
        for product in electronics.products:
            print(f"  - {product.name} (${product.price})")
    
    # 2. Get a supplier with its products
    acme = await Supplier.get_by_attribute(name="Acme Corporation", include_relationships=True, all=True)
    if acme:
        acme = acme[0]
        print(f"\nSupplier: {acme.name}")
        print(f"Products supplied by {acme.name}:")
        for product in acme.products:
            print(f"  - {product.name} (${product.price})")
    
    # 3. Get a product with its category and supplier
    laptop = await Product.get_by_attribute(name="Laptop Pro", include_relationships=True, all=True)
    if laptop:
        laptop = laptop[0]
        print(f"\nProduct: {laptop.name}")
        print(f"Category: {laptop.category.name}")
        print(f"Supplier: {laptop.supplier.name}")
    
    # 4. Get an order with its items and related products
    order = await Order.get_by_id(1, include_relationships=True)
    print(f"\nOrder: #{order.id} for {order.customer_name}")
    print(f"Order Items:")
    total = 0
    for item in order.orderitems:
        product = await item.load_related("product")
        print(f"  - {item.quantity}x {product.name} (${product.price})")
        total += item.quantity * product.price
    print(f"Total: ${total:.2f}")

async def demonstrate_query_methods():
    """Demonstrate various query methods with relationships."""
    print("\n=== Testing Query Methods ===")
    
    # 1. all() method with relationships
    print("\nAll products (ordered by name):")
    all_products = await Product.all(order_by="name", include_relationships=True)
    for product in all_products:
        print(f"  - {product.name} from {product.category.name} by {product.supplier.name}")
    
    # 2. first() method with relationships
    print("\nFirst product:")
    first_product = await Product.first(include_relationships=True)
    print(f"  - {first_product.name} from {first_product.category.name}")
    
    # 3. limit() method with relationships
    print("\nLimited products (top 2 most expensive):")
    top_products = await Product.limit(2, order_by="-price", include_relationships=True)
    for product in top_products:
        print(f"  - {product.name}: ${product.price} from {product.supplier.name}")
    
    # 4. get_by_attribute with relationships
    print("\nElectronic products:")
    electronics = await Category.get_by_attribute(name="Electronics", all=True)
    if electronics:
        electronics_id = electronics[0].id
        electronic_products = await Product.get_by_attribute(
            category_id=electronics_id, include_relationships=True, all=True
        )
        for product in electronic_products:
            print(f"  - {product.name}: ${product.price}")

async def main():
    """Run the example."""
    try:
        engine = await setup_database()
        await create_test_data()
        await demonstrate_relationships()
        await demonstrate_query_methods()
    except Exception as e:
        print(f"Error during example: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up
        await engine.dispose()
        print("\nExample completed.")

if __name__ == "__main__":
    asyncio.run(main())
