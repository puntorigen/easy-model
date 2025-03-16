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
10. [Database Visualization](#database-visualization)
11. [Advanced Features](#advanced-features)
12. [Standardized API Methods](#standardized-api-methods)
13. [Examples](#examples)
14. [API Reference](#api-reference)

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
    username: str = Field(unique=True)
    email: str
    is_active: bool = Field(default=True)
```

### Field Types and Options

```python
from async_easy_model import EasyModel, Field
from typing import Optional

class Product(EasyModel, table=True):
    name: str = Field(index=True)
    description: Optional[str] = Field(default=None)
    price: float = Field(gt=0)
    stock: int = Field(default=0, ge=0)
    sku: str = Field(unique=True, max_length=20)
    is_available: bool = Field(default=True)
```

## CRUD Operations

### Create (Insert)

```python
# Create a model with nested relationships
user = await User.insert({
    "username": "new_user",
    "email": "new@example.com",
    "posts": [  # Create related posts in the same transaction
        {
            "title": "My First Post", 
            "content": "Post content",
            "comments": [  # Nested relationships can be multiple levels deep
                {"text": "Great post!", "user": {"username": "commenter1"}}
            ]
        },
        {"title": "My Second Post", "content": "More content"}
    ],
    "profile": {  # One-to-one relationship
        "bio": "Python developer",
        "avatar_url": "https://example.com/avatar.jpg"
    }
})

# Access all the nested relationship data immediately
print(f"User: {user.username}")
print(f"Profile bio: {user.profile.bio}")
print(f"First post: {user.posts[0].title}")
print(f"First comment on first post: {user.posts[0].comments[0].text}")
print(f"Comment author: {user.posts[0].comments[0].user.username}")
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
all_users = await User.select(all=True)

# Select with wildcard pattern matching
gmail_users = await User.select({"email": "*@gmail.com"}, all=True)

# Select with ordering
recent_users = await User.select(order_by="-created_at", all=True)

# Select with limit
latest_posts = await Post.select(order_by="-created_at", limit=5)
# Note: limit > 1 automatically sets all=True

# Select with multiple ordering fields
sorted_users = await User.select(order_by=["last_name", "first_name"], all=True)

# Select with relationship ordering
posts_by_author = await Post.select(order_by="author.username", all=True)

# Select with relationship criteria
admin_posts = await Post.select({"author": {"role": "admin"}}, all=True)
```

### Update

```python
# Update by ID
updated_user = await User.update({"email": "new@example.com"}, 1)

# Update by criteria
count = await User.update(
    {"is_active": False},
    {"last_login": None}
)
print(f"Updated {count} users")

# Update with relationship criteria
await Post.update(
    {"status": "archived"},
    {"author": {"username": "john_doe"}}
)

# Update nested relationship fields
await User.update(
    {
        "profile": {"bio": "New bio"},
        "settings": {"notification": True}
    },
    {"username": "john_doe"}
)
```

### Delete

```python
# Delete by ID
success = await User.delete(1)

# Delete by criteria
deleted_count = await User.delete({"is_active": False})
print(f"Deleted {deleted_count} inactive users")

# Delete with relationship criteria
await Comment.delete({"post": {"title": "Old Post"}})

# Delete with complex criteria
await Post.delete({
    "published": False,
    "author": {"username": "john_doe"}
})
```

## Relationship Handling

EasyModel provides robust support for relationship handling. Relationships between models are automatically detected based on foreign key fields, allowing for easy querying of related data.

### Accessing Relationship Fields

Once you've fetched a model instance, you can directly access its relationship fields as properties, even after the database session is closed:

```python
# Get a user with relationships (default behavior - include_relationships=True)
user = await User.select({"username": "jane_doe"})

# Access to-many relationship directly
for cart_item in user.shoppingcarts:
    print(f"Item: {cart_item.quantity} x {cart_item.product.name}")

# Access to-one relationship directly
post = await Post.select({"id": 1})
print(f"Author: {post.author.username}")
```

### Loading Relationships

Relationships are automatically loaded when you fetch models using the `select()`, `get_by_id()`, or other retrieval methods with `include_relationships=True` (which is the default).

```python
# Relationships are loaded by default
user = await User.select({"username": "john_doe"})
print(f"User has {len(user.posts)} posts")

# If you don't need relationships, you can disable them for better performance
user = await User.select({"username": "john_doe"}, include_relationships=False)
# Note: trying to access relationships here would require an active session
```

### Loading Specific Relationships

For performance reasons, you might want to load only specific relationships:

```python
# Load specific relationships for an existing model instance
user = await User.select({"username": "john_doe"}, include_relationships=False)
await user.load_related("posts", "profile")

# Get a model with specific relationships loaded
user = await User.get_with_related(1, ["posts", "comments"])
```

### Creating with Relationships

You can create models with relationships in a single operation:

```python
# Create a model with nested relationships
user = await User.insert({
    "username": "new_user",
    "email": "new@example.com",
    "posts": [  # Create related posts in the same transaction
        {
            "title": "My First Post", 
            "content": "Post content",
            "comments": [  # Nested relationships can be multiple levels deep
                {"text": "Great post!", "user": {"username": "commenter1"}}
            ]
        },
        {"title": "My Second Post", "content": "More content"}
    ],
    "profile": {  # One-to-one relationship
        "bio": "Python developer",
        "avatar_url": "https://example.com/avatar.jpg"
    }
})

# Access all the nested relationship data immediately
print(f"User: {user.username}")
print(f"Profile bio: {user.profile.bio}")
print(f"First post: {user.posts[0].title}")
print(f"First comment on first post: {user.posts[0].comments[0].text}")
print(f"Comment author: {user.posts[0].comments[0].user.username}")
```

### Converting to Dictionary with Relationships

The `to_dict()` method allows you to convert a model instance to a dictionary, including its relationships:

```python
# Get a model with relationships
user = await User.select({"username": "john_doe"})

# Convert to dictionary with default depth (4)
user_dict = user.to_dict()

# Control the depth of relationships
user_dict_shallow = user.to_dict(max_depth=1)  # Only immediate relationships
user_dict_no_rel = user.to_dict(include_relationships=False)  # No relationships
```

### Relationship Features Summary

- **Direct Access**: Access relationship fields directly as properties (`user.posts`)
- **Eager Loading**: Relationships are loaded by default with `include_relationships=True`
- **Selective Loading**: Load specific relationships with `load_related()` or `get_with_related()`
- **Dictionary Conversion**: Convert models to dictionaries with relationship support via `to_dict()`
- **Nested Updates**: Update relationships when creating or updating models

## Automatic Relationship Detection

EasyModel provides a powerful feature that automatically detects and sets up relationships between models based on foreign key fields. This eliminates the need to manually define relationships using SQLModel's `Relationship` class.

### How It Works

The automatic relationship detection system works as follows:

1. When you call `init_db()`, the system scans all models that inherit from `EasyModel`
2. It identifies foreign key fields (either explicitly defined with `foreign_key` or using naming conventions like `user_id`)
3. It automatically sets up bidirectional relationships between models
4. For each foreign key, it creates:
   - A to-one relationship on the model with the foreign key (e.g., `cart.user`)
   - A to-many relationship on the referenced model (e.g., `user.shoppingcarts`)

### Example

```python
from async_easy_model import EasyModel, Field
from typing import Optional

# Define your models without explicit relationship definitions
class Department(EasyModel, table=True):
    name: str
    # here we get a 'employees' field automatically available due to the foreign key on Employee

class Employee(EasyModel, table=True):
    name: str
    department_id: Optional[int] = Field(default=None, foreign_key="department.id")
    # No explicit 'department' relationship needed!
    # here we get a 'department' field (Department class) automatically available due to the foreign key on department_id

# Initialize the database (this will set up relationships)
await init_db()

# Now you can use relationships directly
department = await Department.insert({"name": "Engineering"})
employee = await Employee.insert({"name": "John Doe", "department_id": department.id})

# Access the to-one relationship
print(f"{employee.name} works in the {employee.department.name} department")

# Access the to-many relationship
print(f"The {department.name} department has {len(department.employees)} employees")

```

### Foreign Key Naming Conventions

The system detects foreign keys based on:

1. Explicit foreign key definitions: `field: int = Field(foreign_key="table.column")`
2. Naming convention: Fields named `<table_singular>_id` (e.g., `user_id` referring to the `users` table)

The relationship fields are named intelligently:
- The to-one field uses the name without the `_id` suffix (e.g., `user_id` → `user`)
- The to-many field uses the pluralized form of the referencing model's table name (e.g., `users` → `employees`)

### Accessing Auto-Detected Relationships

Once relationships are set up, you can access them directly on model instances:

```python
# Access to-one relationships
user = await User.select({"username": "john_doe"})
print(f"First shopping cart product: {user.shoppingcarts[0].product.name}")

# Access to-many relationships  
product = await Product.select({"id": 1})
print(f"This product appears in {len(product.shoppingcarts)} shopping carts")
```

### Customizing Automatic Relationships

For most cases, automatic detection works without configuration, but you can customize it:

```python
from async_easy_model.auto_relationships import setup_relationship_between_models

# Manual setup for custom relationship names
setup_relationship_between_models(
    Order, 
    Customer, 
    "customer_id", 
    source_attr_name="buyer",  # Custom name on Order side
    target_attr_name="purchases"  # Custom name on Customer side
)
```

## Query Methods

### Ordering Capabilities

The ordering capabilities in async-easy-model are powerful and flexible:

1. **Ascending Order**: By default, results are ordered in ascending order
   ```python
   users = await User.select({}, order_by="username", all=True)  # A to Z
   ```

2. **Descending Order**: Prefix the field name with a minus sign (`-`) for descending order
   ```python
   users = await User.select({}, order_by="-created_at", all=True)  # Newest first
   ```

3. **Multiple Field Ordering**: Pass a list of field names to order by multiple fields
   ```python
   users = await User.select({}, order_by=["last_name", "first_name"], all=True)  # Sort by last name, then first name
   ```

4. **Relationship Field Ordering**: Use dot notation to order by fields in related models
   ```python
   books = await Book.select({}, order_by="author.name", all=True)  # Books ordered by author name
   posts = await Post.select({}, order_by="-user.created_at", all=True)  # Posts ordered by user creation date (newest first)
   ```

These ordering capabilities can be used with the `select()` method, making it easy to retrieve data in the desired sequence without additional sorting in application code.

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
    username: str = Field(unique=True)
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

## Database Visualization

The async-easy-model package includes a powerful visualization component that allows you to generate Entity-Relationship (ER) diagrams for your database schema using the Mermaid diagram syntax. This feature is particularly useful for documentation, understanding complex model relationships, and communicating database structure to team members.

### ModelVisualizer Class

The `ModelVisualizer` class automatically discovers all registered EasyModel models and generates ER diagrams showing tables, fields, and relationships.

```python
from async_easy_model import EasyModel, init_db, db_config, ModelVisualizer

# Define your models...

# Initialize database
await init_db(model_classes=[Author, Book, Tag, BookTag, Review])

# Create visualizer instance with default title
visualizer = ModelVisualizer()

# Generate Mermaid ER diagram in markdown format
er_diagram = visualizer.mermaid()
print(er_diagram)

# Generate a link to view the diagram in Mermaid Live Editor
link = visualizer.mermaid_link()
print(link)

# Optionally save to a file
with open("database_schema.md", "w") as f:
    f.write("# Database Schema\n\n")
    f.write(er_diagram)
```

### Customizing the Diagram Title

You can customize the title of your ER diagram:

```python
# Set title during initialization
visualizer = ModelVisualizer(title="My Project Database Schema")

# Or change it after initialization
visualizer.set_title("Library Management System")
custom_diagram = visualizer.mermaid()
```

### Example Output

The generated Mermaid ER diagram will look like this:

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

### Understanding the Diagram

The ER diagram includes:

1. **Tables**: Each model is represented as a table with its table name
2. **Fields**: Each field is shown with its data type
3. **Primary Keys**: Fields marked with `PK`
4. **Foreign Keys**: Fields marked with `FK`
5. **Virtual Fields**: Relationship fields created automatically by EasyModel
6. **Relationships**: Lines showing connections between tables with cardinality indicators:
   - `||--o{`: One-to-many relationship
   - `}o--o{`: Many-to-many relationship
   - `||--||`: One-to-one relationship
7. **Required Fields**: Fields that are required are shown with the `"required"` attribute

### Benefits of Visualization

- **Documentation**: Automatically generate up-to-date documentation of your database schema
- **Understanding Relationships**: Clearly see how tables are related, including many-to-many relationships
- **Sharing**: Generate links to share with team members
- **Development Planning**: Plan database changes by visualizing the current structure

### API Reference

#### ModelVisualizer Class

**Constructor:**
- `ModelVisualizer(title: str = "EasyModel Table Schemas")`: Initialize the visualizer with an optional title

**Methods:**
- `mermaid() -> str`: Generate a Mermaid ER diagram as a markdown string
- `mermaid_link() -> str`: Generate a shareable link to view the diagram in Mermaid Live Editor
- `set_title(title: str) -> None`: Set or update the diagram title

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

### Insert Method

```python
# Insert single record
user = await User.insert({
    "username": "john_doe",
    "email": "john@example.com"
})

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
    {"department": {"name": "Sales"}},  # Update the department
    {"username": "john_doe"}
)
```

### Delete Method

```python
# Delete by ID
success = await User.delete(1)

# Delete by criteria
deleted_count = await User.delete({"is_active": False})

# Delete with compound criteria
await Post.delete({"author": {"username": "john_doe"}, "is_published": False})
```

### Complete Example with Relationships

This example demonstrates a complete workflow using EasyModel, including model definition, database initialization, and relationship field access:

```python
import asyncio
from async_easy_model import EasyModel, init_db, db_config, Field
from typing import Optional
from datetime import datetime

# Configure database
db_config.configure_sqlite(":memory:")

# Define models with automatic relationships
class User(EasyModel, table=True):
    username: str = Field(unique=True)
    email: str

class Post(EasyModel, table=True):
    title: str
    content: str
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")

class Comment(EasyModel, table=True):
    text: str
    post_id: Optional[int] = Field(default=None, foreign_key="post.id")
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")

async def main():
    # Initialize database
    await init_db()
    
    # Create user
    user = await User.insert({
        "username": "john_doe",
        "email": "john@example.com"
    })
    
    # Create post with relationship to user
    post = await Post.insert({
        "title": "First Post",
        "content": "Hello world!",
        "user_id": user.id  # Link to user by ID
    })
    
    # Create comment with relationship to post and user
    comment = await Comment.insert({
        "text": "Great post!",
        "post_id": post.id,
        "user": {"username": "john_doe"}  # Link to user by attribute lookup
    })
    
    # Get user with relationships
    john = await User.select({"username": "john_doe"})
    
    # Access relationship fields directly
    print(f"User: {john.username}")
    print(f"Posts: {len(john.posts)}")
    for post in john.posts:
        print(f"  - Post: {post.title}")
        print(f"    Comments: {len(post.comments)}")
        for comment in post.comments:
            print(f"      * {comment.text} (by {comment.user.username})")
    
    # Query with relationship criteria
    johns_comments = await Comment.select({
        "user": {"username": "john_doe"}
    }, all=True)
    
    print(f"\nJohn's comments: {len(johns_comments)}")
    
    # Update with relationships
    await Post.update(
        {"title": "Updated Title"},
        {"user": {"username": "john_doe"}}
    )
    
    # Verify update
    updated_post = await Post.select({"id": post.id})
    print(f"\nUpdated post title: {updated_post.title}")
    
    # Convert to dictionary with relationships
    post_dict = updated_post.to_dict()
    print(f"\nPost as dictionary: {post_dict}")
    print(f"Author username: {post_dict['user']['username']}")

# Run the example
asyncio.run(main())
```

### Shopping Cart Example

This example demonstrates a more complex relationship structure with direct relationship field access:

```python
import asyncio
from async_easy_model import EasyModel, init_db, db_config, Field
from typing import Optional
from datetime import datetime

# Configure database
db_config.configure_sqlite(":memory:")

# Define models
class User(EasyModel, table=True):
    username: str = Field(unique=True)
    email: str

class Product(EasyModel, table=True):
    name: str
    price: float = Field(gt=0)

class ShoppingCart(EasyModel, table=True):
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    product_id: Optional[int] = Field(default=None, foreign_key="product.id")
    quantity: int = Field(default=1, gt=0)

async def main():
    # Initialize database
    await init_db()
    
    # Create user
    jane = await User.insert({
        "username": "jane_doe",
        "email": "jane@example.com"
    })
    
    # Create products
    products = await Product.insert([
        {"name": "Product 1", "price": 10.99},
        {"name": "Product 2", "price": 24.99},
        {"name": "Product 3", "price": 15.50}
    ])
    
    # Add items to Jane's cart
    for product in products:
        await ShoppingCart.insert({
            "user_id": jane.id,
            "product_id": product.id,
            "quantity": 2
        })
    
    # Retrieve user with relationships
    jane = await User.select({"username": "jane_doe"})
    
    # Direct access to shopping carts
    print(f"Jane's cart has {len(jane.shoppingcarts)} items:")
    total = 0
    for item in jane.shoppingcarts:
        subtotal = item.quantity * item.product.price
        total += subtotal
        print(f"  - {item.quantity} x {item.product.name} (${item.product.price}) = ${subtotal:.2f}")
    
    print(f"Total: ${total:.2f}")
    
    # Access from product perspective
    product = await Product.select({"name": "Product 2"})
    print(f"\nProduct '{product.name}' is in {len(product.shoppingcarts)} carts")
    
    # Query with multiple relationship criteria
    expensive_items = await ShoppingCart.select({
        "user": {"username": "jane_doe"},
        "product": {"price": 15.50}
    }, all=True)
    
    print(f"\nJane has {len(expensive_items)} expensive items in her cart")

# Run the example
asyncio.run(main())
