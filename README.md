# async-easy-model

A simplified SQLModel-based ORM for async database operations in Python. async-easy-model provides a clean, intuitive interface for common database operations while leveraging the power of SQLModel and SQLAlchemy.

<p align="center">
  <img src="https://img.shields.io/pypi/v/async-easy-model" alt="PyPI Version">
  <img src="https://img.shields.io/pypi/pyversions/async-easy-model" alt="Python Versions">
  <img src="https://img.shields.io/github/license/puntorigen/easy_model" alt="License">
</p>

## Features

- 🚀 Easy-to-use async database operations with standardized methods
- 🔄 Intuitive APIs with sensible defaults for rapid development
- 📊 Dictionary-based CRUD operations (select, insert, update, delete)
- 🔗 Enhanced relationship handling with eager loading and nested operations
- 🔍 Powerful query methods with flexible ordering support
- ⚙️ Automatic relationship detection and bidirectional setup
- 📱 Support for both PostgreSQL and SQLite databases
- 🛠️ Built on top of SQLModel and SQLAlchemy for robust performance
- 📝 Type hints for better IDE support
- 🕒 Automatic `id`, `created_at` and `updated_at` fields provided by default
- ⏰ **PostgreSQL DateTime Compatibility**: Automatic timezone-aware to timezone-naive datetime conversion for PostgreSQL TIMESTAMP WITHOUT TIME ZONE columns
- 🔄 Automatic schema migrations for evolving database models
- 📊 Visualization of database schema using Mermaid ER diagrams
- 📋 **JSON Column Support**: Native support for JSON columns with proper serialization in migrations

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
    #no need to specify id, created_at or updated_at since EasyModel provides them by default
    username: str = Field(unique=True)
    email: str

# Initialize your database
async def setup():
    await init_db()

# Use it in your async code
async def main():
    await setup()
    # Create a new user
    user = await User.insert({
        "username": "john_doe",
        "email": "john@example.com"
    })
    
    # Get user ID
    print(f"New user id: {user.id}")
```

## CRUD Operations

First, let's define some models that we'll use throughout the examples:

```python
from async_easy_model import EasyModel, Field
from typing import Optional, List
from datetime import datetime

class User(EasyModel, table=True):
    username: str = Field(unique=True)
    email: str
    is_active: bool = Field(default=True)
    
class Post(EasyModel, table=True):
    title: str
    content: str
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    
class Comment(EasyModel, table=True):
    text: str
    post_id: Optional[int] = Field(default=None, foreign_key="post.id")
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    
class Department(EasyModel, table=True):
    name: str = Field(unique=True)
    
class Product(EasyModel, table=True):
    name: str
    price: float
    sales: int = Field(default=0)
    
class Book(EasyModel, table=True):
    title: str
    author_id: Optional[int] = Field(default=None, foreign_key="author.id")
    
class Author(EasyModel, table=True):
    name: str
```

### Create (Insert)

```python
# Insert a single record
user = await User.insert({
    "username": "john_doe",
    "email": "john@example.com"
})

# Insert multiple records
users = await User.insert([
    {"username": "user1", "email": "user1@example.com"},
    {"username": "user2", "email": "user2@example.com"}
])

# Insert with nested relationships
new_post = await Post.insert({
    "title": "My Post",
    "content": "Content here",
    "user": {"username": "jane_doe"},  # Will automatically link to existing user
    "comments": [  # Create multiple comments in a single transaction
        {"text": "Great post!", "user": {"username": "reader1"}},
        {"text": "Thanks for sharing", "user": {"username": "reader2"}}
    ]
})
# Access nested data without requerying
print(f"Post by {new_post.user.username} with {len(new_post.comments)} comments")

# Insert with nested one-to-many relationships 
publisher = await Publisher.insert({
    "name": "Example Publisher",
    "books": [  # List of nested objects
        {
            "title": "Python Mastery",
            "genres": [
                {"name": "Programming"},
                {"name": "Education"}
            ]
        },
        {"title": "Data Science Handbook"}
    ]
})
# Access nested relationships immediately
print(f"Publisher: {publisher.name} with {len(publisher.books)} books")
print(f"First book genres: {[g.name for g in publisher.books[0].genres]}")
```

### Read (Retrieve)

```python
# Select by ID
user = await User.select({"id": 1})

# Select with criteria
users = await User.select({"is_active": True}, all=True)

# Select first matching record
first_user = await User.select({"is_active": True}, first=True)

# Select all records
all_users = await User.select({}, all=True)

# Select with wildcard pattern matching
gmail_users = await User.select({"email": "*@gmail.com"}, all=True)

# Select with ordering
recent_users = await User.select({}, order_by="-created_at", all=True)

# Select with limit
latest_posts = await Post.select({}, order_by="-created_at", limit=5)
# Note: limit > 1 automatically sets all=True

# Select with multiple ordering fields
sorted_users = await User.select({}, order_by=["last_name", "first_name"], all=True)

# Select with relationship ordering
posts_by_author = await Post.select({}, order_by="user.username", all=True)
```

### Update

```python
# Update by ID
user = await User.update({"is_active": False}, 1)

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

### Delete

```python
# Delete by ID
success = await User.delete(1)

# Delete by criteria
deleted_count = await User.delete({"is_active": False})

# Delete with compound criteria
await Post.delete({"user": {"username": "john_doe"}, "is_published": False})
```

## Database Schema Visualization

The package includes a `ModelVisualizer` class that makes it easy to generate Entity-Relationship (ER) diagrams for your database models using Mermaid syntax.

```python
from async_easy_model import EasyModel, init_db, db_config, ModelVisualizer

# Initialize your models and database
await init_db()

# Create a visualizer
visualizer = ModelVisualizer()

# Generate a Mermaid ER diagram
er_diagram = visualizer.mermaid()
print(er_diagram)

# Generate a shareable link to view the diagram online
er_link = visualizer.mermaid_link()
print(er_link)

# Customize the diagram title
visualizer.set_title("My Project Database Schema")
custom_diagram = visualizer.mermaid()
```

### Example Mermaid ER Diagram Output

```mermaid
---
title: EasyModel Table Schemas
config:
    layout: elk
---
erDiagram
    author {
        number id PK
        string name "required"
        string email
    }
    book {
        number id PK
        string title "required"
        number author_id FK
        string isbn
        number published_year
        author author "virtual"
        tag[] tags "virtual"
    }
    tag {
        number id PK
        string name "required"
        book[] books "virtual"
    }
    book_tag {
        number id PK
        number book_id FK "required"
        number tag_id FK "required"
        book book "virtual"
        tag tag "virtual"
    }
    review {
        number id PK
        number book_id FK "required"
        number rating "required"
        string comment
        string reviewer_name "required"
        book book "virtual"
    }
    book ||--o{ author : "author_id"
    book_tag ||--o{ book : "book_id"
    book_tag ||--o{ tag : "tag_id"
    book }o--o{ tag : "many-to-many"
    review ||--o{ book : "book_id"
```

The diagram automatically:
- Shows all tables with their fields and data types
- Identifies primary keys (PK) and foreign keys (FK)
- Shows required fields and virtual relationships
- Visualizes relationships between tables with proper cardinality
- Properly handles many-to-many relationships

## Convenient Query Methods

async-easy-model provides simplified methods for common query patterns:

```python
# Get all records with relationships loaded (default)
users = await User.all()

# Get all records ordered by a field (ascending)
users = await User.all(order_by="username")

# Get all records ordered by a field (descending)
newest_users = await User.all(order_by="-created_at")

# Get all records ordered by multiple fields
sorted_users = await User.all(order_by=["last_name", "first_name"])

# Get all records ordered by relationship fields
books = await Book.all(order_by="author.name")

# Get the first record 
user = await User.first()

# Get the most recently created user
newest_user = await User.first(order_by="-created_at")

# Get a limited number of records
recent_users = await User.limit(10)

# Get a limited number of records with ordering
top_products = await Product.limit(5, order_by="-sales")
```

## Enhanced Relationship Handling

Using the models defined earlier, here's how to work with relationships:

```python
# Load all relationships automatically
post = await Post.select({"id": 1})
print(post.user.username)  # Access related objects directly

# Load specific relationships
post = await Post.get_with_related(1, ["user", "comments"])

# Load relationships after fetching
post = await Post.select({"id": 1}, include_relationships=False)
await post.load_related(["user", "comments"])

# Insert with nested relationships
new_post = await Post.insert({
    "title": "My Post",
    "content": "Content here",
    "user": {"username": "jane_doe"},  # Will automatically link to existing user
    "comments": [  # Create multiple comments in a single transaction
        {"text": "Great post!", "user": {"username": "reader1"}},
        {"text": "Thanks for sharing", "user": {"username": "reader2"}}
    ]
})
# Access nested data without requerying
print(f"Post by {new_post.user.username} with {len(new_post.comments)} comments")

# Convert to dictionary with nested relationships
post_dict = post.to_dict(include_relationships=True, max_depth=2)
```

## Automatic Relationship Detection

The package can automatically detect and set up bidirectional relationships between models:

```python
class User(EasyModel, table=True):
    username: str

class Post(EasyModel, table=True):
    title: str
    user_id: int = Field(foreign_key="user.id")

# After init_db():
# - post.user relationship is automatically available
# - user.posts relationship is automatically available
```

## Database Configuration

```python
# SQLite Configuration
db_config.configure_sqlite("database.db")
db_config.configure_sqlite(":memory:")  # In-memory database

# PostgreSQL Configuration
db_config.configure_postgres(
    user="your_user",
    password="your_password",
    host="localhost",
    port="5432",
    database="your_database"
)

# Custom Connection URL
db_config.set_connection_url("postgresql+asyncpg://user:password@localhost:5432/database")
```

## Documentation

For more detailed documentation, please visit the [GitHub repository](https://github.com/puntorigen/easy-model) or refer to the [DOCS.md](https://github.com/puntorigen/easy-model/blob/master/DOCS.md) file.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
