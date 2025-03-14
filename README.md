# EasyModel

A simplified SQLModel-based ORM for async database operations in Python. EasyModel provides a clean and intuitive interface for common database operations while leveraging the power of SQLModel and SQLAlchemy.

## Features

- Easy-to-use async database operations with standardized methods
- Intuitive APIs with sensible defaults (relationships loaded by default)
- Dictionary-based CRUD operations (select, insert, update, delete)
- Built on top of SQLModel and SQLAlchemy
- Support for both PostgreSQL and SQLite databases
- Type hints for better IDE support
- Automatic `id`, `created_at` and `updated_at` fields provided by default
- Enhanced relationship handling with eager loading and nested operations
- Flexible ordering of query results with support for relationship fields
- Automatic relationship detection
- Automatic schema migrations for evolving database models

## Installation

```bash
pip install async-easy-model
```

## Quick Start with Standardized API

This section demonstrates the preferred usage of EasyModel with its standardized API methods.

```python
from async_easy_model import EasyModel, init_db, db_config, Field
from typing import Optional
from datetime import datetime

# Configure your database
db_config.configure_sqlite("database.db")

# Define your model
class User(EasyModel, table=True):
    # id field is automatically created (primary key)
    username: str = Field(unique=True)
    email: str
    is_active: bool = Field(default=True)
    # created_at and updated_at fields are automatically included
    
class Post(EasyModel, table=True):
    # id field is automatically created (primary key)
    title: str
    content: str
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    # created_at and updated_at fields are automatically included

# Initialize your database
async def setup():
    await init_db()

# Use the standardized methods in your code
async def main():
    # Insert a new user
    user = await User.insert({
        "username": "john_doe",
        "email": "john@example.com"
    })
    
    # Insert with relationships
    post = await Post.insert({
        "title": "My First Post",
        "content": "Hello world!",
        "user": {"username": "john_doe"}  # Will find the user by username
    })
    
    # Select with criteria
    active_users = await User.select({"is_active": True}, all=True)
    
    # Select with wildcard search
    gmail_users = await User.select({"email": "*@gmail.com"}, all=True)
    
    # Select with ordering and limit
    recent_posts = await Post.select({}, order_by="-id", limit=5)
    # Note: limit > 1 automatically sets all=True
    
    # Update by criteria
    await User.update(
        {"is_active": False},
        {"last_login": None}  # Update users with no login
    )
    
    # Delete with criteria
    await Post.delete({"user": {"username": "john_doe"}})
```

## Standardized API Methods

EasyModel provides a set of standardized methods that make it easy and intuitive to perform common database operations.

### Select Method

The `select()` method is a powerful and flexible way to query data:

```python
# Get active users
active_users = await User.select({"is_active": True}, all=True)

# Get single user by username (returns first match)
user = await User.select({"username": "john_doe"})

# Explicitly get first result
first_admin = await User.select({"role": "admin"}, first=True)

# With wildcard pattern matching
gmail_users = await User.select({"email": "*@gmail.com"}, all=True)

# With ordering and limit (automatically sets all=True)
newest_users = await User.select({}, order_by="-created_at", limit=5)

# With ordering by multiple fields
sorted_users = await User.select({}, order_by=["last_name", "first_name"], all=True)

# With ordering by nested relationship fields using dot notation
books_by_author = await Book.select({}, order_by="author.name", all=True)
posts_by_popularity = await Post.select({}, order_by=["-comments.count", "title"], all=True)
```

### Insert Method

The `insert()` method supports both single and multiple records with relationship handling and returns the newly created records with assigned IDs and auto-generated fields (`created_at`, `updated_at`):

```python
# Insert single record
user = await User.insert({
    "username": "john_doe",
    "email": "john@example.com"
})
print(user.id)  # Newly assigned ID is available
print(user.created_at)  # Auto-generated timestamp is available

# Insert with relationship
comment = await Comment.insert({
    "text": "Great post!",
    "post": {"id": 1},  # Link by ID
    "author": {"username": "jane_doe"}  # Link by attribute lookup
})

# Insert multiple records
products = await Product.insert([
    {"name": "Product 1", "price": 10.99},
    {"name": "Product 2", "price": 24.99}
])
```

### Update Method

The `update()` method allows updates based on ID or criteria:

```python
# Update by ID
user = await User.update({"email": "new@example.com"}, 1)

# Update by criteria
count = await User.update(
    {"is_active": False},
    {"last_login": None}  # Set all users without login to inactive
)

# Update with relationships
await User.update(
    {"department": {"name": "Sales"}},  # Update department relationship
    {"username": "john_doe"}
)
```

### Delete Method

The `delete()` method provides a consistent way to delete records:

```python
# Delete by ID
success = await User.delete(1)

# Delete by criteria
deleted_count = await User.delete({"is_active": False})

# Delete with compound criteria
await Post.delete({"author": {"username": "john_doe"}, "is_published": False})
```

## Convenience Query Methods

EasyModel also provides convenient shorthand methods for common queries:

```python
# Get all records with relationships loaded (default)
users = await User.all()

# Get all records ordered by a field
users = await User.all(order_by="username")

# Get the first record
user = await User.first()

# Get the most recently created user
newest_user = await User.first(order_by="-created_at")

# Get limited records
recent_users = await User.limit(10, order_by="-created_at")
```

## Automatic Relationship Detection

EasyModel supports automatic relationship detection based on foreign key fields:

```python
from async_easy_model import enable_auto_relationships, EasyModel, init_db, Field
from typing import Optional

# Enable automatic relationship detection
enable_auto_relationships()

# Define models with foreign keys but without explicit relationships
class Author(EasyModel, table=True):
    # id field is automatically created (primary key)
    name: str

class Book(EasyModel, table=True):
    title: str
    author_id: Optional[int] = Field(default=None, foreign_key="author.id")
    # No need to define Relationship attributes - they're detected automatically!

# Use the automatically detected relationships
async def main():
    await init_db()
    author = await Author.insert({"name": "Jane Author"})
    
    book = await Book.insert({
        "title": "Auto-detected Relationships",
        "author_id": author.id
    })
    
    # Show the book with its author
    print(f"Book: {book.title}, Author: {book.author.name}")
```

### Another Example
```python
# Using the standard insert with nested dictionaries (recommended)
new_book = await Book.insert({
    "title": "New Book",
    "author": {"name": "Jane Author"}  # Will create or find the author
})
```

## Automatic Schema Migrations

EasyModel includes automatic database migration capabilities, similar to alembic:

```python
from async_easy_model import MigrationManager

async def apply_migrations():
    migration_manager = MigrationManager()
    results = await migration_manager.migrate_models([User, Post])
    
    if results:
        print("Migrations applied:")
        for model_name, changes in results.items():
            print(f"  {model_name}:")
            for change in changes:
                print(f"    - {change}")
```

## Legacy API Methods

The following methods are still supported but the standardized methods above are recommended for new code:

### Traditional CRUD Operations

```python
# Create a record (consider using insert() instead)
user = User(username="john_doe", email="john@example.com")
await user.save()

# Get by ID (consider using select() instead)
user = await User.get_by_id(1)

# Get by attribute (consider using select() instead)
users = await User.get_by_attribute(is_active=True, all=True)

# Update by ID (consider using update() instead)
updated_user = await User.update_by_id(1, {"email": "new_email@example.com"})

# Update by attribute (consider using update() instead)
await User.update_by_attribute(
    {"is_active": False},  # Update data
    is_active=True, role="guest"  # Filter criteria
)

# Delete by ID (consider using delete() instead)
success = await User.delete_by_id(1)

# Delete by attribute (consider using delete() instead)
deleted_count = await User.delete_by_attribute(is_active=False)
```

## Complete Documentation

For complete documentation, including advanced features, please see the [full documentation](DOCS.md).
