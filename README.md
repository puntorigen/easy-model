# EasyModel

A simplified SQLModel-based ORM for async database operations in Python. EasyModel provides a clean and intuitive interface for common database operations while leveraging the power of SQLModel and SQLAlchemy.

## Features

- Easy-to-use async database operations
- Built on top of SQLModel and SQLAlchemy
- Support for both PostgreSQL and SQLite databases
- Common CRUD operations out of the box
- Session management with context managers
- Type hints for better IDE support
- Automatic `created_at` and `updated_at` field management
- **Enhanced relationship handling with eager loading and nested operations**
- **Convenient query methods for retrieving records (all, first, limit)**

## Installation

```bash
pip install async-easy-model
```

## Quick Start

```python
from async_easy_model import EasyModel, init_db, db_config
from sqlmodel import Field
from typing import Optional
from datetime import datetime

# Configure your database (choose one)
# For SQLite:
db_config.configure_sqlite("database.db")
# For PostgreSQL:
db_config.configure_postgres(
    user="your_user",
    password="your_password",
    host="localhost",
    port="5432",
    database="your_database"
)

# Define your model
class User(EasyModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True)
    email: str
    # Note: created_at and updated_at fields are automatically included
    # and managed by EasyModel, so you don't need to define them.

# Initialize your database (creates all tables)
async def setup():
    await init_db()

# Use it in your async code
async def main():
    # Create a new user
    user = await User.insert({
        "username": "john_doe",
        "email": "john@example.com"
    })
    
    # Update user - updated_at will be automatically set
    updated_user = await User.update(1, {
        "email": "new_email@example.com"
    })
    print(f"Last update: {updated_user.updated_at}")

    # Delete user
    success = await User.delete(1)
```

## Working with Relationships

EasyModel provides enhanced support for handling relationships between models:

### Defining Models with Relationships

```python
from sqlmodel import Field, Relationship
from typing import List, Optional
from async_easy_model import EasyModel

class Author(EasyModel, table=True):
    name: str
    books: List["Book"] = Relationship(back_populates="author")

class Book(EasyModel, table=True):
    title: str
    author_id: Optional[int] = Field(default=None, foreign_key="author.id")
    author: Optional[Author] = Relationship(back_populates="books")
```

### Loading Related Objects

```python
# Fetch with all relationships eagerly loaded
author = await Author.get_by_id(1, include_relationships=True)
print(f"Author: {author.name}")
print(f"Books: {[book.title for book in author.books]}")

# Fetch specific relationships
book = await Book.get_with_related(1, "author")
print(f"Book: {book.title}")
print(f"Author: {book.author.name}")

# Load relationships after fetching
another_book = await Book.get_by_id(2)
await another_book.load_related("author")
print(f"Author: {another_book.author.name}")
```

### Creating Objects with Relationships

```python
# Create related objects in a single transaction
new_author = await Author.create_with_related(
    data={"name": "Jane Doe"},
    related_data={
        "books": [
            {"title": "Book One"},
            {"title": "Book Two"}
        ]
    }
)

# Access the created relationships
for book in new_author.books:
    print(f"Created book: {book.title}")
```

### Converting to Dictionary with Relationships

```python
# Convert to dictionary including relationships
author_dict = author.to_dict(include_relationships=True)
print(f"Author: {author_dict['name']}")
print(f"Books: {[book['title'] for book in author_dict['books']]}")

# Control the depth of nested relationships
deep_dict = author.to_dict(include_relationships=True, max_depth=2)
```

## Querying Records

EasyModel provides convenient methods for retrieving records:

### Retrieving All Records

```python
# Get all users
all_users = await User.all()
print(f"Total users: {len(all_users)}")

# Get all users with their relationships
all_users_with_relations = await User.all(include_relationships=True)
```

### Getting the First Record

```python
# Get the first user
first_user = await User.first()
if first_user:
    print(f"First user: {first_user.username}")

# Get the first user with relationships
first_user_with_relations = await User.first(include_relationships=True)
```

### Limiting Results

```python
# Get the first 10 users
recent_users = await User.limit(10)
print(f"Recent users: {[user.username for user in recent_users]}")

# Get the first 5 users with relationships
recent_users_with_relations = await User.limit(5, include_relationships=True)
```

## Configuration

You can configure the database connection in two ways:

### 1. Using Environment Variables

For PostgreSQL:
```bash
POSTGRES_USER=your_user
POSTGRES_PASSWORD=your_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=your_database
```

For SQLite:
```bash
SQLITE_FILE=database.db
```

### 2. Using Configuration Methods

For PostgreSQL:
```python
from async_easy_model import db_config

db_config.configure_postgres(
    user="your_user",
    password="your_password",
    host="localhost",
    port="5432",
    database="your_database"
)
```

For SQLite:
```python
from async_easy_model import db_config

db_config.configure_sqlite("database.db")
```

## Examples

Check out the `examples` directory for more detailed examples:

- `examples/relationship_example.py`: Demonstrates the enhanced relationship handling features
- `examples/diario_example.py`: Shows how to use relationship features with diary entries

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
