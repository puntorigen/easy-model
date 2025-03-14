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
9. [Automatic Schema Migrations](#automatic-schema-migrations)
10. [Advanced Features](#advanced-features)
11. [Examples](#examples)

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

# Method 2: Using EasyModel's Relation helper for more readable code
class Category(EasyModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    # Using Relation.many for a more readable relationship definition
    products: List["Product"] = Relation.many("category")

class Product(EasyModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    category_id: Optional[int] = Field(default=None, foreign_key="category.id")
    # Using Relation.one for a more readable relationship definition
    category: Optional[Category] = Relation.one("products")
```

The `Relation` class provides a more intuitive way to define relationships:

- `Relation.one(back_populates)`: For the "one" side of a one-to-many relationship
- `Relation.many(back_populates)`: For the "many" side of a one-to-many relationship
- `Relation.many_to_many(back_populates, link_model)`: For many-to-many relationships

This approach makes the relationship definitions more readable and self-documenting.

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
from async_easy_model import enable_auto_relationships, EasyModel, init_db, Field
from typing import Optional

# Enable automatic relationship detection before defining your models
enable_auto_relationships()

# Define models with foreign keys but without explicit relationships
class Department(EasyModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    # No explicit 'employees' relationship needed!

class Employee(EasyModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    department_id: Optional[int] = Field(default=None, foreign_key="department.id")
    # No explicit 'department' relationship needed!
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

If you encounter issues with automatic relationship detection due to conflicts with SQLModel's metaclass, you can:

1. Use explicit relationship definitions with SQLModel's `Relationship` or `Relation` helpers
2. Enable auto-relationships without patching the metaclass and set up relationships manually after model definition

```python
from async_easy_model import enable_auto_relationships, setup_relationship_between_models
from async_easy_model import EasyModel, Field
from typing import Optional

# Enable without patching SQLModel's metaclass
enable_auto_relationships(patch_metaclass=False)

# Define models with foreign keys but without explicit relationships
class Department(EasyModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str

class Employee(EasyModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    department_id: Optional[int] = Field(default=None, foreign_key="department.id")

# Manually set up relationships after model definition
setup_relationship_between_models(
    source_model=Employee,
    target_model=Department,
    foreign_key_name="department_id",
    source_attr_name="department",  # Employee.department
    target_attr_name="employees"    # Department.employees
)
```

### How Automatic Relationship Detection Works

The automatic relationship detection feature works by:

1. Scanning model definitions for foreign key fields
2. Identifying the target model from the foreign key reference
3. Setting up bidirectional relationships between models
4. Registering relationships with SQLModel's metadata

This allows you to simply define the foreign key fields and let the library handle the relationship setup. The naming convention used for automatic relationships is:

- For to-one relationships: The name is derived from the foreign key field by removing the "_id" suffix (e.g., "author_id" → "author")
- For to-many relationships: The pluralized name of the source model (e.g., "book" → "books")

## Query Methods

### all() - Retrieving All Records

```python
# Basic usage
all_users = await User.all()

# With relationships
all_users_with_relations = await User.all(include_relationships=True)

# With ordering (ascending)
ordered_users = await User.all(order_by="username")

# With ordering (descending)
newest_users = await User.all(order_by="-created_at")

# With multiple ordering fields
complex_order = await User.all(order_by=["last_name", "first_name"])

# With relationship field ordering
books_by_author = await Book.all(order_by="author.name")
users_by_post_date = await User.all(order_by="-posts.created_at")
```

### first() - Getting the First Record

```python
# Basic usage
first_user = await User.first()

# With relationships
first_user_with_relations = await User.first(include_relationships=True)

# With ordering (get oldest user)
oldest_user = await User.first(order_by="created_at")

# With ordering (get newest user)
newest_user = await User.first(order_by="-created_at")

# With relationship field ordering
first_book_by_author = await Book.first(order_by="author.name")
```

### limit() - Limiting Results

```python
# Basic usage
recent_users = await User.limit(10)

# With relationships
recent_users_with_relations = await User.limit(5, include_relationships=True)

# With ordering
newest_users = await User.limit(5, order_by="-created_at")

# With multiple ordering fields
complex_limit = await User.limit(5, order_by=["last_name", "first_name"])

# With relationship field ordering
top_books_by_author = await Book.limit(5, order_by="author.name")
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

# Multiple filter criteria with ordering
filtered_users = await User.get_by_attribute(
    all=True,
    is_active=True,
    role="user",
    order_by="username"
)

# With relationship field ordering
books_by_author = await Book.get_by_attribute(
    all=True,
    published=True,
    order_by="author.name"
)
```

### Ordering Capabilities

The ordering capabilities in async-easy-model are powerful and flexible:

1. **Ascending Order**: By default, results are ordered in ascending order
   ```python
   users = await User.all(order_by="username")  # A to Z
   ```

2. **Descending Order**: Prefix the field name with a minus sign (`-`) for descending order
   ```python
   users = await User.all(order_by="-created_at")  # Newest first
   ```

3. **Multiple Field Ordering**: Pass a list of field names to order by multiple fields
   ```python
   users = await User.all(order_by=["last_name", "first_name"])  # Sort by last name, then first name
   ```

4. **Relationship Field Ordering**: Use dot notation to order by fields in related models
   ```python
   books = await Book.all(order_by="author.name")  # Books ordered by author name
   posts = await Post.all(order_by="-user.created_at")  # Posts ordered by user creation date (newest first)
   ```

These ordering capabilities can be used with all query methods (`all()`, `first()`, `limit()`, and `get_by_attribute()`), making it easy to retrieve data in the desired sequence without additional sorting in application code.

## Automatic Schema Migrations

EasyModel offers an automatic migration system that detects changes in your model definitions and applies appropriate migrations to your database schema without requiring manual migration scripts.

### Overview

The migration system tracks your model definitions with hash codes and detects when they change. When changes are detected, it automatically generates and applies the necessary database schema migrations. This ensures that your database tables always match your model definitions.

### How It Works

The migration process happens automatically when you call `init_db()`:

1. EasyModel generates a hash code for each model definition based on:
   - Table name
   - Column definitions (name, type, constraints)
   - Relationships

2. These hashes are compared with previously stored hashes to detect changes.

3. For changed or new models, EasyModel:
   - Inspects the current database schema
   - Compares it with the model definition
   - Generates migration operations (create table, add/alter/drop column)
   - Applies the migrations to update the database schema

4. All migrations are tracked in a migration history file for reference.

### Usage

The migration system works automatically without any additional code:

```python
from async_easy_model import EasyModel, init_db, db_config, Field
from typing import Optional

# Configure your database
db_config.configure_sqlite("database.db")

# Define your model
class User(EasyModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str
    email: str
    # Later, you might add a new field:
    # is_active: bool = Field(default=True)

# Initialize database with automatic migrations
async def setup():
    await init_db()  # This will detect and apply any needed migrations
```

### Migration Storage

Migrations are tracked in a `.easy_model_migrations` directory in your project root:

- `model_hashes.json`: Stores hashes of model definitions
- `migration_history.json`: Records the migration history with timestamps

### Advanced Migration Control

For more control over the migration process, you can use the `MigrationManager` directly:

```python
from async_easy_model import MigrationManager
from your_app.models import User, Post

async def manage_migrations():
    # Create a migration manager
    migration_manager = MigrationManager()
    
    # Check for pending model changes without applying them
    changes = await migration_manager.detect_model_changes([User, Post])
    if changes:
        print("Pending changes:")
        for model_name, info in changes.items():
            print(f"- {model_name}: {info['status']}")
    
    # Apply migrations for specific models
    results = await migration_manager.migrate_models([User, Post])
    if results:
        print("Applied migrations:")
        for model_name, operations in results.items():
            for op in operations:
                print(f"- {model_name}: {op['operation']} - {op.get('table_name')} {op.get('column_name', '')}")
```

### Migration Operations

The migration system supports the following operations:

- `create_table`: Creates a new table for a new model
- `add_column`: Adds a new column to an existing table
- `alter_column`: Changes the type or constraints of an existing column
- `drop_column`: Removes a column from a table

### Limitations

While the automatic migration system is powerful, there are some limitations to be aware of:

1. **Complex Migrations**: Very complex schema changes might require manual intervention
2. **Data Migration**: The system handles schema changes but not data transformations
3. **SQLite Constraints**: SQLite has limited support for altering columns (primarily adding new columns)

If you encounter these limitations, you may need to:
- Use the PostgreSQL backend for more advanced migration support
- Manually modify your database schema for complex changes
- Perform data migrations in your application code

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

### Relation Class

A helper class that provides a more intuitive way to define relationships.

**Class Methods:**

- `Relation.one(back_populates, **kwargs)`: Define a to-one relationship
- `Relation.many(back_populates, **kwargs)`: Define a to-many relationship
- `Relation.many_to_many(back_populates, link_model, **kwargs)`: Define a many-to-many relationship

**Example:**

```python
class Author(EasyModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    # Using Relation.many for a more readable relationship definition
    books: List["Book"] = Relation.many("author")

class Book(EasyModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    author_id: Optional[int] = Field(default=None, foreign_key="author.id")
    # Using Relation.one for a more readable relationship definition
    author: Optional[Author] = Relation.one("books")
```

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
