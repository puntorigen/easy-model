# async-easy-model Documentation

This document provides comprehensive documentation for the async-easy-model package, a simplified SQLModel-based ORM for async database operations in Python.

## Table of Contents

1. [Installation](#installation)
2. [Basic Usage](#basic-usage)
3. [Database Configuration](#database-configuration)
4. [Model Definition](#model-definition)
5. [CRUD Operations](#crud-operations)
6. [Relationship Handling](#relationship-handling)
7. [Automatic Relationship Detection](#automatic-relationship-detection)
8. [Query Methods](#query-methods)
9. [Advanced Features](#advanced-features)
10. [Examples](#examples)

## Installation

```bash
pip install async-easy-model
```

## Basic Usage

```python
from async_easy_model import EasyModel, init_db, db_config, Field
from typing import Optional
from datetime import datetime

# Configure your database
db_config.configure_sqlite("database.db")

# Define your model
class User(EasyModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True)
    email: str

# Initialize your database
async def setup():
    await init_db()

# Use it in your async code
async def main():
    # Create a new user
    user = await User.insert({
        "username": "john_doe",
        "email": "john@example.com"
    })
    
    # Get user by ID
    retrieved_user = await User.get_by_id(user.id)
    print(f"Retrieved user: {retrieved_user.username}")
```

## Database Configuration

### SQLite Configuration

```python
from async_easy_model import db_config

# Method 1: Direct configuration
db_config.configure_sqlite("database.db")

# Method 2: With full path
db_config.configure_sqlite("/path/to/database.db")

# Method 3: In-memory database
db_config.configure_sqlite(":memory:")

# Method 4: Using environment variables
# Set SQLITE_FILE=database.db in your environment
# Then simply call init_db() without explicit configuration
```

### PostgreSQL Configuration

```python
from async_easy_model import db_config

# Method 1: Direct configuration
db_config.configure_postgres(
    user="your_user",
    password="your_password",
    host="localhost",
    port="5432",
    database="your_database"
)

# Method 2: Using environment variables
# Set these in your environment:
# POSTGRES_USER=your_user
# POSTGRES_PASSWORD=your_password
# POSTGRES_HOST=localhost
# POSTGRES_PORT=5432
# POSTGRES_DB=your_database
# Then simply call init_db() without explicit configuration
```

### Custom Connection URL

```python
from async_easy_model import db_config

# For advanced use cases, you can set the connection URL directly
db_config.set_connection_url("postgresql+asyncpg://user:password@localhost:5432/database")
```

## Model Definition

### Basic Model

```python
from async_easy_model import EasyModel, Field
from typing import Optional
from datetime import datetime

class User(EasyModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True)
    email: str
    is_active: bool = Field(default=True)
    created_at: Optional[datetime] = Field(default_factory=lambda: datetime.now())
    updated_at: Optional[datetime] = Field(default_factory=lambda: datetime.now())
```

### Field Types and Options

```python
from async_easy_model import EasyModel, Field
from typing import Optional
from datetime import datetime

class Product(EasyModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: Optional[str] = Field(default=None)
    price: float = Field(gt=0)
    stock: int = Field(default=0, ge=0)
    sku: str = Field(unique=True, max_length=20)
    is_available: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now())
```

## CRUD Operations

### Create (Insert)

```python
# Insert a single record
user = await User.insert({
    "username": "john_doe",
    "email": "john@example.com"
})

# Insert multiple records
users = await User.insert_many([
    {"username": "user1", "email": "user1@example.com"},
    {"username": "user2", "email": "user2@example.com"}
])
```

### Read (Retrieve)

```python
# Get by ID
user = await User.get_by_id(1)

# Get by attribute
users = await User.get_by_attribute(username="john_doe", all=True)

# Get first matching record
first_user = await User.get_by_attribute(is_active=True)

# Get all records
all_users = await User.all()

# Get limited records
recent_users = await User.limit(10, order_by="-created_at")
```

### Update

```python
# Update by ID
updated_user = await User.update(1, {
    "email": "new_email@example.com"
})

# Update multiple records
await User.update_by_attribute(
    {"is_active": False},  # Update data
    is_active=True, role="guest"  # Filter criteria
)
```

### Delete

```python
# Delete by ID
success = await User.delete(1)

# Delete by attribute
deleted_count = await User.delete_by_attribute(is_active=False)
```

## Relationship Handling

### Defining Relationships

```python
from async_easy_model import EasyModel, Field, Relationship, Relation
from typing import List, Optional

# Method 1: Using SQLModel's Relationship
class Author(EasyModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    books: List["Book"] = Relationship(back_populates="author")

class Book(EasyModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    author_id: Optional[int] = Field(default=None, foreign_key="author.id")
    author: Optional[Author] = Relationship(back_populates="books")

# Method 2: Using EasyModel's Relation helper
class Category(EasyModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    products: List["Product"] = Relation.many("category")

class Product(EasyModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    category_id: Optional[int] = Field(default=None, foreign_key="category.id")
    category: Optional[Category] = Relation.one("products")
```

### Loading Related Objects

```python
# Method 1: Eager loading with include_relationships
author = await Author.get_by_id(1, include_relationships=True)
for book in author.books:
    print(f"Book: {book.title}")

# Method 2: Using get_with_related
book = await Book.get_with_related(1, "author")
print(f"Author: {book.author.name}")

# Method 3: Loading relationships after fetching
product = await Product.get_by_id(1)
await product.load_related("category")
print(f"Category: {product.category.name}")
```

### Creating with Related Objects

```python
# Create an author with books in a single transaction
new_author = await Author.create_with_related(
    data={"name": "Jane Doe"},
    related_data={
        "books": [
            {"title": "Book One"},
            {"title": "Book Two"}
        ]
    }
)
```

### Converting to Dictionary with Relationships

```python
# Convert to dictionary including relationships
author = await Author.get_with_related(1, "books")
author_dict = author.to_dict(include_relationships=True)

# Control the depth of nested relationships
deep_dict = author.to_dict(include_relationships=True, max_depth=2)
```

## Automatic Relationship Detection

### Enabling Auto-Relationships

```python
from async_easy_model import enable_auto_relationships, EasyModel, Field
from typing import Optional

# Enable automatic relationship detection
enable_auto_relationships()

# Define models with foreign keys but without explicit relationships
class Department(EasyModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str

class Employee(EasyModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    department_id: Optional[int] = Field(default=None, foreign_key="department.id")
```

### Using Auto-Detected Relationships

```python
# Relationships are automatically detected and can be used like explicit ones
department = await Department.get_by_id(1, include_relationships=True)
for employee in department.employees:
    print(f"Employee: {employee.name}")

employee = await Employee.get_by_id(1, include_relationships=True)
print(f"Department: {employee.department.name}")
```

### Compatibility with SQLModel

```python
from async_easy_model import enable_auto_relationships, setup_relationship_between_models

# Enable without patching SQLModel's metaclass
enable_auto_relationships(patch_metaclass=False)

# Manually set up relationships after model definition
setup_relationship_between_models(
    source_model=Employee,
    target_model=Department,
    foreign_key_name="department_id",
    source_attr_name="department",
    target_attr_name="employees"
)
```

## Query Methods

### all() - Retrieving All Records

```python
# Basic usage
all_users = await User.all()

# With relationships
all_users_with_relations = await User.all(include_relationships=True)

# With ordering
ordered_users = await User.all(order_by="username")
newest_users = await User.all(order_by="-created_at")

# With multiple ordering fields
complex_order = await User.all(order_by=["last_name", "first_name"])

# With relationship field ordering
books_by_author = await Book.all(order_by="author.name")
```

### first() - Getting the First Record

```python
# Basic usage
first_user = await User.first()

# With relationships
first_user_with_relations = await User.first(include_relationships=True)

# With ordering
oldest_user = await User.first(order_by="created_at")
newest_user = await User.first(order_by="-created_at")
```

### limit() - Limiting Results

```python
# Basic usage
recent_users = await User.limit(10)

# With relationships
recent_users_with_relations = await User.limit(5, include_relationships=True)

# With ordering
newest_users = await User.limit(5, order_by="-created_at")
```

### get_by_attribute() - Filtering Records

```python
# Get a single record
user = await User.get_by_attribute(username="john_doe")

# Get all matching records
active_users = await User.get_by_attribute(all=True, is_active=True)

# With relationships
user_with_relations = await User.get_by_attribute(
    username="john_doe",
    include_relationships=True
)

# With ordering
latest_admin = await User.get_by_attribute(
    role="admin",
    order_by="-created_at"
)

# Multiple filter criteria
filtered_users = await User.get_by_attribute(
    all=True,
    is_active=True,
    role="user",
    order_by="username"
)
```

## Advanced Features

### Custom Session Management

```python
from async_easy_model import EasyModel

class User(EasyModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str

async def custom_session_example():
    # Use the session context manager
    async with User.get_session() as session:
        # Perform multiple operations in a single transaction
        statement = select(User).where(User.username == "john_doe")
        result = await session.execute(statement)
        user = result.scalar_one_or_none()
        
        if user:
            # Update user
            user.username = "john_smith"
            session.add(user)
            await session.commit()
```

### Raw SQL Queries

```python
from async_easy_model import db_config
from sqlalchemy import text

async def raw_sql_example():
    engine = db_config.get_engine()
    async with engine.connect() as conn:
        # Execute raw SQL
        result = await conn.execute(
            text("SELECT * FROM user WHERE username = :username"),
            {"username": "john_doe"}
        )
        for row in result:
            print(row)
```

### Transactions

```python
from async_easy_model import db_config

async def transaction_example():
    engine = db_config.get_engine()
    async with engine.begin() as conn:
        # Everything in this block is part of a transaction
        await conn.execute(
            text("INSERT INTO user (username, email) VALUES (:username, :email)"),
            {"username": "new_user", "email": "new@example.com"}
        )
        # Transaction is automatically committed if no exceptions occur
        # or rolled back if an exception is raised
```

## Examples

The package includes several example scripts in the `examples` directory:

- `minimal_working_example.py`: Basic example of model definition and CRUD operations
- `relationship_example.py`: Demonstrates relationship handling with SQLModel
- `auto_relationship_test.py`: Tests automatic relationship detection
- `simple_auto_relationship.py`: Simple example of auto-relationships with SQLite
- `final_auto_relationship.py`: Complete example with explicit relationships
- `simple_auto_detection.py`: Demonstrates manual relationship setup
- `comprehensive_auto_rel_example.py`: Comprehensive example with multiple models

To run an example:

```bash
cd /path/to/async-easy-model
python examples/minimal_working_example.py
```

## API Reference

### EasyModel Class

The base model class that provides common async database operations.

**Class Methods:**

- `get_session()`: Get a database session for transactions
- `insert(data)`: Insert a single record
- `insert_many(data_list)`: Insert multiple records
- `get_by_id(id, include_relationships=False)`: Get a record by ID
- `get_by_attribute(**kwargs)`: Get records by attribute values
- `all(include_relationships=False, order_by=None)`: Get all records
- `first(include_relationships=False, order_by=None)`: Get the first record
- `limit(count, include_relationships=False, order_by=None)`: Get a limited number of records
- `update(id, data)`: Update a record by ID
- `update_by_attribute(data, **kwargs)`: Update records by attribute values
- `delete(id)`: Delete a record by ID
- `delete_by_attribute(**kwargs)`: Delete records by attribute values
- `get_with_related(id, *relationships)`: Get a record with specific relationships
- `create_with_related(data, related_data)`: Create a record with related records

**Instance Methods:**

- `load_related(*relationships)`: Load relationships for an instance
- `to_dict(include_relationships=False, max_depth=1)`: Convert instance to dictionary

### Database Configuration

The `db_config` module provides methods for configuring the database connection.

**Methods:**

- `configure_sqlite(database_path)`: Configure SQLite database
- `configure_postgres(user, password, host, port, database)`: Configure PostgreSQL database
- `set_connection_url(url)`: Set the connection URL directly
- `get_connection_url()`: Get the current connection URL
- `get_engine()`: Get the SQLAlchemy engine
- `get_session_maker()`: Get the session maker

### Auto-Relationships

The `auto_relationships` module provides functions for automatic relationship detection.

**Functions:**

- `enable_auto_relationships(patch_metaclass=False)`: Enable automatic relationship detection
- `setup_relationship_between_models(source_model, target_model, foreign_key_name, source_attr_name=None, target_attr_name=None)`: Set up relationships between models
- `setup_auto_relationships_for_model(model_cls)`: Set up automatic relationships for a model
