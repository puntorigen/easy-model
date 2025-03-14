# Supercharge Your Async Python Projects with async-easy-model

Hey fellow developers! 👋

Are you tired of writing boilerplate code for database operations? Struggling with complex ORM setups? Dealing with manual migrations that seem to break at the worst possible time? I've been there too, and today I'm thrilled to share a game-changing package that has transformed my development workflow: **async-easy-model**.

## Why async-easy-model Is Your New Best Friend

As Python developers, we're constantly looking for tools that enhance productivity without sacrificing flexibility or performance. The **async-easy-model** package is exactly that – a sleek, intuitive ORM built on top of SQLModel and SQLAlchemy that makes async database operations a breeze.

What makes it special?

- **Simplicity meets power**: Write expressive, clean code that's easy to read and maintain
- **Async-first design**: Built for modern Python applications with full async/await support
- **Automatic migrations**: Say goodbye to Alembic scripts and hello to seamless schema evolution
- **Enhanced relationship handling**: Work with nested models intuitively
- **Standardized methods**: Consistent API for all your CRUD operations
- **Intuitive querying**: Flexible, readable query methods with ordering support
- **Built-in best practices**: Automatic timestamps, sensible defaults, and type hints

Let's dive in and see how async-easy-model can transform your development workflow!

## Getting Started

First things first, let's install the package:

```bash
pip install async-easy-model
```

### Configure Your Database Connection

Start by configuring your database connection:

```python
from async_easy_model import db_config

# SQLite setup (great for development)
db_config.configure_sqlite("database.db")

# Or PostgreSQL for production
db_config.configure_postgres(
    user="your_user",
    password="your_password",
    host="localhost",
    port="5432",
    database="your_database"
)
```

### Define Your Models

After setting up your connection, define your models:

```python
from async_easy_model import EasyModel, Field
from typing import Optional

# Define your models
class User(EasyModel, table=True):
    username: str = Field(unique=True)
    email: str
    is_active: bool = Field(default=True)

# Define other models...
```

### Initialize Your Database

Finally, initialize your database after all your models have been defined:

```python
from async_easy_model import init_db

async def setup():
    # Always call init_db() after all your models have been defined
    await init_db()  # This is where the magic happens!
```

## Defining Your Models

Model definition is clean and intuitive:

```python
# User model with automatic timestamps
class User(EasyModel, table=True):
    username: str = Field(unique=True)
    email: str
    is_active: bool = Field(default=True)
    
# Blog post with relationship to user
class Post(EasyModel, table=True):
    title: str
    content: str
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    
# Comment with relationships to post and user
class Comment(EasyModel, table=True):
    text: str
    post_id: Optional[int] = Field(default=None, foreign_key="post.id")
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
```

Notice what's missing? You don't need to explicitly define:

- Primary key fields (`id`)
- Timestamp fields (`created_at`, `updated_at`)
- Relationship attributes

async-easy-model provides these automatically!

## CRUD Operations Made Simple

Let's explore how async-easy-model simplifies database operations.

### Creating Records

```python
# Creating a single user
user = await User.insert({
    "username": "jane_doe",
    "email": "jane@example.com"
})
print(f"Created user with ID: {user.id}")

# Creating multiple records at once
products = await Product.insert([
    {"name": "Ergonomic Keyboard", "price": 89.99},
    {"name": "Wireless Mouse", "price": 49.99},
    {"name": "Monitor Stand", "price": 29.99}
])
print(f"Created {len(products)} products")

# Creating with relationships
post = await Post.insert({
    "title": "Why async-easy-model is Amazing",
    "content": "Let me count the ways...",
    "user": {"username": "jane_doe"}  # Automatically links to existing user
})
print(f"Created post with title: {post.title} by user: {post.user.username}")
```

### Reading Records

Here's where async-easy-model really shines with its flexible, intuitive query methods:

```python
# Get by ID (single record)
user = await User.select({"id": 1})

# Get all records
all_users = await User.select({}, all=True)
# Or the more expressive shorthand:
all_users = await User.all()

# Get with criteria
active_users = await User.select({"is_active": True}, all=True)

# Pattern matching with wildcards
gmail_users = await User.select({"email": "*@gmail.com"}, all=True)

# Get first matching record
first_user = await User.first()

# Limit results
latest_users = await User.limit(5)

# Order results (ascending by default)
alphabetical_users = await User.all(order_by="username")

# Order results (descending)
newest_users = await User.all(order_by="-created_at")

# Order by multiple fields
sorted_users = await User.all(order_by=["last_name", "first_name"])

# Order by relationship fields
posts_by_author = await Post.all(order_by="user.username")

# Select with relationship criteria
admin_posts = await Post.select({"user": {"role": "admin"}}, all=True)
```

### Updating Records

```python
# Update by ID
updated_user = await User.update({"email": "updated@example.com"}, 1)
print(f"Updated user email to: {updated_user.email}")

# Update by criteria
count = await User.update(
    {"is_active": False},
    {"last_login": None}  # Update all users who haven't logged in
)
print(f"Deactivated {count} inactive users")

# Update with nested relationship fields
await User.update(
    {
        "profile": {"bio": "Python developer and async enthusiast"},
        "settings": {"notifications": True}
    },
    {"username": "jane_doe"}
)
```

### Deleting Records

```python
# Delete by ID
success = await User.delete(1)
if success:
    print("User deleted successfully")

# Delete by criteria
deleted_count = await User.delete({"is_active": False})
print(f"Deleted {deleted_count} inactive users")

# Delete with relationship criteria
await Comment.delete({"post": {"title": "Outdated Post"}})
```

## The Magic of Automatic Relationships

One of the most powerful features of async-easy-model is its automatic relationship handling. When you define foreign keys, the package automatically sets up bidirectional relationships between your models.

```python
# Define your models with foreign keys
class Department(EasyModel, table=True):
    name: str

class Employee(EasyModel, table=True):
    name: str
    department_id: Optional[int] = Field(default=None, foreign_key="department.id")

# Initialize the database 
await init_db()

# Now you can use relationships automatically!
department = await Department.insert({"name": "Engineering"})
employee = await Employee.insert({
    "name": "John Doe", 
    "department_id": department.id
})

# Access relationships directly
employee = await Employee.select({"id": employee.id})  # Relationships are loaded by default
print(f"{employee.name} works in the {employee.department.name} department")

# Access in the reverse direction too
department = await Department.select({"id": department.id})
print(f"The {department.name} department has {len(department.employees)} employees")
```

### Working with Relationships Like a Pro

async-easy-model provides several ways to work with relationships efficiently:

```python
# Load specific relationships for better performance
user = await User.get_with_related(1, ["posts", "comments"])

# Load relationships after fetching
user = await User.select({"id": 1}, include_relationships=False)
await user.load_related(["posts", "comments"])

# Insert with nested relationships
new_post = await Post.insert({
    "title": "Working with Relationships",
    "content": "It's easier than you think!",
    "user": {"id": 1},  # Link by ID
    "comments": [
        {"text": "Great post!", "user": {"username": "fan1"}},
        {"text": "Very helpful", "user": {"username": "fan2"}}
    ]
})

# Access nested data immediately without requerying
print(f"Post by {new_post.user.username} with {len(new_post.comments)} comments")
print(f"First comment by: {new_post.comments[0].user.username}")

# Convert to dictionary with relationships included (default)
post_dict = new_post.to_dict(include_relationships=True)
```

## The Miracle of Automatic Migrations

Here's where async-easy-model truly stands out: **automatic schema migrations without Alembic!**

The package tracks your model definitions with hash codes. When you modify your models and call `init_db()`, it automatically:

1. Detects changes in your model definitions
2. Generates the necessary migration operations
3. Applies them to your database schema

Let's see this in action:

```python
# First, configure database connection
db_config.configure_sqlite("database.db")

# Then, define your models
class Product(EasyModel, table=True):
    name: str
    price: float = Field(gt=0)

# Finally, initialize database after models are defined
await init_db()

# Later, you decide to add a new field
class Product(EasyModel, table=True):
    name: str
    price: float = Field(gt=0)
    description: Optional[str] = Field(default=None)  # New field
    in_stock: bool = Field(default=True)  # Another new field

# Just call init_db() again and the migration happens automatically!
# This must happen after the updated model definitions
migration_results = await init_db()
print("Migration applied:", migration_results)
```

No Alembic scripts, no migration versions to track, no complex commands to run. Just update your models and run your application!

## Real-World Example: Building a Blog API

Let's see how async-easy-model simplifies building a real-world application:

```python
from fastapi import FastAPI, HTTPException
from async_easy_model import EasyModel, init_db, db_config, Field
from typing import Optional, List
from pydantic import BaseModel

# First, configure database connection
db_config.configure_sqlite("blog.db")

# Then, define models
class User(EasyModel, table=True):
    username: str = Field(unique=True)
    email: str
    
class Post(EasyModel, table=True):
    title: str
    content: str
    published: bool = Field(default=False)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    
class Comment(EasyModel, table=True):
    content: str
    post_id: Optional[int] = Field(default=None, foreign_key="post.id")
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")

# Define API schemas
class PostCreate(BaseModel):
    title: str
    content: str
    published: bool = False

class PostResponse(BaseModel):
    id: int
    title: str
    content: str
    published: bool
    created_at: str
    author: str

# Initialize FastAPI
app = FastAPI(title="Blog API")

@app.on_event("startup")
async def startup():
    # Initialize db after all models have been defined
    await init_db()
    
    # Create default user if none exists
    if not await User.first():
        await User.insert({
            "username": "admin",
            "email": "admin@example.com"
        })

@app.get("/posts", response_model=List[PostResponse])
async def get_posts():
    # Get all published posts, ordered by newest first
    posts = await Post.select({"published": True}, order_by="-created_at", all=True)
    
    # Convert to response format
    return [
        PostResponse(
            id=post.id,
            title=post.title,
            content=post.content,
            published=post.published,
            created_at=post.created_at.isoformat(),
            author=post.user.username
        ) for post in posts
    ]

@app.post("/posts", response_model=PostResponse)
async def create_post(post_data: PostCreate):
    # Get the admin user
    admin = await User.first()
    
    # Create the post with relationship
    post = await Post.insert({
        "title": post_data.title,
        "content": post_data.content,
        "published": post_data.published,
        "user_id": admin.id
    })
    
    # Load the user relationship
    await post.load_related("user")
    
    # Return the response
    return PostResponse(
        id=post.id,
        title=post.title,
        content=post.content,
        published=post.published,
        created_at=post.created_at.isoformat(),
        author=post.user.username
    )
```

## Performance Benefits

Using async-easy-model doesn't just make your code more readable – it can significantly improve performance:

1. **Reduced database round-trips**: Relationship loading is optimized with eager loading strategies
2. **Efficient querying**: The package generates optimized SQL queries
3. **Async design**: Built for non-blocking I/O operations
4. **Simplified codebase**: Less code means fewer bugs and better maintenance

## Why You Should Start Using async-easy-model Today

1. **Productivity boost**: Write less code and get more done
2. **Code readability**: Clean, intuitive API that makes your intentions clear
3. **Maintainability**: No migration scripts to maintain
4. **Flexibility**: Works with both SQLite and PostgreSQL
5. **Modern Python**: Fully async with type hints for better IDE support
6. **Reliability**: Built on the solid foundations of SQLModel and SQLAlchemy

## Conclusion

The async-easy-model package represents a significant step forward in simplifying database operations for Python developers. By combining the power of SQLAlchemy with an intuitive, developer-friendly API, it eliminates much of the boilerplate and complexity usually associated with ORMs.

Whether you're building a small personal project or a large-scale application, async-easy-model can help you write cleaner, more maintainable code with fewer bugs. The automatic migration system alone can save you hours of development time and prevent countless headaches.

So what are you waiting for? Give async-easy-model a try in your next project:

```bash
pip install async-easy-model
```

Your future self will thank you for it! Happy coding! 🚀

---

*Have you tried async-easy-model? What has been your experience? Share in the comments below!*
