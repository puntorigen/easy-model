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
- **Flexible ordering of query results with support for relationship fields**
- **Simplified Field and Relationship definition syntax**
- **Automatic relationship detection**

## Installation

```bash
pip install async-easy-model
```

## Quick Start

This section demonstrates the basic usage of EasyModel including database configuration, model definition, and fundamental CRUD operations.

```python
from async_easy_model import EasyModel, init_db, db_config, Field
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

EasyModel provides enhanced support for handling relationships between models. With the new `Relation` helper class, defining and working with relationships becomes more intuitive and type-safe.

### Defining Models with Relationships

You can define relationships between models using either the new `Relation` helper class or the traditional SQLModel `Relationship` approach.

```python
from typing import List, Optional
from async_easy_model import EasyModel, Field, Relation

class Author(EasyModel, table=True):
    name: str
    # Using Relation.many for a clear one-to-many relationship
    books: List["Book"] = Relation.many("author")

class Book(EasyModel, table=True):
    title: str
    author_id: Optional[int] = Field(default=None, foreign_key="author.id")
    # Using Relation.one for a clear many-to-one relationship
    author: Optional["Author"] = Relation.one("books")
```

The above example uses the new `Relation` class, which provides a more readable and intuitive way to define relationships. The `Relation` class offers:

- `Relation.one()` - For defining a many-to-one relationship
- `Relation.many()` - For defining a one-to-many relationship

You can also use the traditional SQLModel `Relationship` approach, which is now exposed directly in the async_easy_model package:

```python
from async_easy_model import EasyModel, Field, Relationship
from typing import List, Optional

class Author(EasyModel, table=True):
    name: str
    books: List["Book"] = Relationship(back_populates="author")

class Book(EasyModel, table=True):
    title: str
    author_id: Optional[int] = Field(default=None, foreign_key="author.id")
    author: Optional["Author"] = Relationship(back_populates="books")
```

### Loading Related Objects

EasyModel offers multiple ways to load related objects, allowing you to choose the most suitable approach for your specific use case.

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

When creating objects with relationships, EasyModel allows you to create related objects in a single transaction using the `create_with_related` method.

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

The `to_dict()` method allows you to convert a model instance to a dictionary, including its relationships. This is particularly useful when you need to serialize your models for an API response.

```python
# First ensure you have loaded the relationships
author = await Author.get_with_related(1, "books")

# Convert to dictionary including relationships
author_dict = author.to_dict(include_relationships=True)
print(f"Author: {author_dict['name']}")
if 'books' in author_dict and author_dict['books']:
    print(f"Books: {[book['title'] for book in author_dict['books']]}")

# Control the depth of nested relationships (default is 1)
deep_dict = author.to_dict(include_relationships=True, max_depth=2)
```

> **Note:** Always ensure that relationships are properly loaded before calling `to_dict()` with `include_relationships=True`. Use either `get_with_related()` or `get_by_id()` with `include_relationships=True` to ensure all relationship data is available.

## Automatic Relationship Detection

Async EasyModel now supports automatic relationship detection based on foreign key fields. This makes it easier to work with related models without having to explicitly define relationships.

### How to enable automatic relationship detection

```python
from async_easy_model import enable_auto_relationships, EasyModel, init_db, Field
from typing import Optional

# Enable automatic relationship detection before defining your models
enable_auto_relationships()

# Define your models with foreign key fields but without explicit relationships
class Author(EasyModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    # No relationship definition needed for books!

class Book(EasyModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    author_id: Optional[int] = Field(default=None, foreign_key="author.id")
    # No relationship definition needed for author!

# Initialize database
await init_db()

# Now you can use relationships just like they were explicitly defined
author = await Author.get_by_id(1, include_relationships=True)
print(f"Author: {author.name}")
print(f"Books: {[book.title for book in author.books]}")

book = await Book.get_by_id(1, include_relationships=True)
print(f"Book: {book.title}")
print(f"Author: {book.author.name}")
```

### Compatibility with SQLModel

If you encounter issues with automatic relationship detection due to conflicts with SQLModel's metaclass, you can:

1. Use the explicit relationship definitions with SQLModel's `Relationship`
2. Call `enable_auto_relationships(patch_metaclass=False)` and then set up relationships after model definition

```python
from async_easy_model import enable_auto_relationships, EasyModel, Field, Relationship
from typing import List, Optional

# Enable without patching SQLModel's metaclass
enable_auto_relationships(patch_metaclass=False)

# Define models with explicit relationships
class Author(EasyModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    
    # Explicitly define relationship
    books: List["Book"] = Relationship(back_populates="author")

class Book(EasyModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    author_id: Optional[int] = Field(default=None, foreign_key="author.id")
    
    # Explicitly define relationship
    author: Optional[Author] = Relationship(back_populates="books")
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

This follows the common convention in ORMs and makes the code more intuitive and self-documenting.

## Querying Records

EasyModel provides powerful and flexible query methods that make it easy to retrieve and filter records from your database. The following sections demonstrate the various query methods available.

### Retrieving All Records

The `all()` method allows you to retrieve all records of a model, with options for including relationships and ordering.

```python
# Get all users
all_users = await User.all()
print(f"Total users: {len(all_users)}")

# Get all users with their relationships
all_users_with_relations = await User.all(include_relationships=True)

# Get all users ordered by username
ordered_users = await User.all(order_by="username")

# Get all users ordered by creation date (newest first)
newest_users = await User.all(order_by="-created_at")

# Order by multiple fields
complex_order = await User.all(order_by=["last_name", "first_name"])
```

### Getting the First Record

The `first()` method allows you to retrieve the first record that matches your criteria, with options for ordering and including relationships.

```python
# Get the first user
first_user = await User.first()
if first_user:
    print(f"First user: {first_user.username}")

# Get the first user with relationships
first_user_with_relations = await User.first(include_relationships=True)

# Get the oldest user (ordered by created_at)
oldest_user = await User.first(order_by="created_at")
```

### Limiting Results

The `limit()` method allows you to retrieve a limited number of records, with options for ordering and including relationships.

```python
# Get the first 10 users
recent_users = await User.limit(10)
print(f"Recent users: {[user.username for user in recent_users]}")

# Get the first 5 users with relationships
recent_users_with_relations = await User.limit(5, include_relationships=True)

# Get the 5 most recently created users
newest_users = await User.limit(5, order_by="-created_at")
```

### Filtering with Ordering

The `get_by_attribute()` method allows you to filter records by attribute values, with options for ordering and including relationships.

```python
# Get all active users ordered by username
active_users = await User.get_by_attribute(
    all=True, 
    is_active=True, 
    order_by="username"
)

# Get the most recent user in a specific category
latest_admin = await User.get_by_attribute(
    role="admin", 
    order_by="-created_at"
)
```

### Ordering by Relationship Fields

EasyModel supports ordering by relationship fields, allowing you to sort records based on attributes of related models.

```python
# Get all books ordered by author name
books_by_author = await Book.all(order_by="author.name")

# Get users ordered by their latest post date
users_by_post = await User.all(order_by="-posts.created_at")
```

## Configuration

EasyModel supports multiple ways to configure your database connection, making it easy to adapt to different environments and requirements.

### 1. Using Environment Variables

Environment variables provide a secure and flexible way to configure your database connection, especially for production deployments.

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

Configuration methods provide a programmatic way to set up your database connection, which is often more convenient during development.

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

For more detailed examples and practical applications, check out the `examples` directory in the repository:

- `examples/relationship_example.py`: Demonstrates the enhanced relationship handling features
- `examples/diario_example.py`: Shows how to use relationship features with diary entries
- `examples/query_methods_example.py`: Shows how to use the query methods with ordering
- `examples/minimal_working_example.py`: Basic example of model definition and CRUD operations
- `examples/simple_auto_detection.py`: Demonstrates automatic relationship detection with SQLite
- `examples/simple_auto_relationship.py`: Shows how to use auto-relationships with explicit definitions
- `examples/comprehensive_auto_rel_example.py`: Comprehensive example with multiple models and relationships

For complete documentation of all features, see the [DOCS.md](DOCS.md) file.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
