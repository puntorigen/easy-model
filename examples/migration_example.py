"""
Migration Example - Demonstrating Automatic Schema Migrations

This example shows how EasyModel automatically handles database schema migrations
when model definitions change. It walks through several scenarios:

1. Creating initial models and database
2. Adding new fields to existing models
3. Adding new models with relationships to existing ones
4. Modifying field types
5. Adding and modifying relationships

Each step simulates changes you might make to your models during development.
"""

import asyncio
import os
import json
import shutil
from pathlib import Path
from typing import Optional, List
from datetime import datetime
import sys

# Import from the library
from async_easy_model import (
    EasyModel, db_config, init_db,
    MigrationManager, Relationship
)
# Import Field directly from sqlmodel to avoid import issues
from sqlmodel import Field
from sqlmodel import SQLModel
from sqlalchemy import MetaData, inspect, create_engine, Column, String, Boolean, DateTime, text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import declarative_base

# Set up database file and migrations directory
DB_FILE = "migration_example.db"
MIGRATIONS_DIR = ".easy_model_migrations"

# Function to clear existing database and migrations directory
def clear_previous_state():
    """Remove previous database and migrations directory if they exist."""
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
        print(f"Removed existing database: {DB_FILE}")
    
    if os.path.exists(MIGRATIONS_DIR):
        shutil.rmtree(MIGRATIONS_DIR)
        print(f"Removed existing migrations directory: {MIGRATIONS_DIR}")
    
    # Initialize an empty migrations directory
    Path(MIGRATIONS_DIR).mkdir(exist_ok=True)

# Set up the database configuration
def setup_db_config():
    """Configure the database connection for the example."""
    db_config.configure_sqlite(DB_FILE)  # Use configure_sqlite method

# Stage 1: Initial setup with a simple User model
class UserV1(EasyModel, table=True):
    """Basic user model with minimal fields."""
    __tablename__ = "user"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True)
    email: str = Field(unique=True)
    created_at: datetime = Field(default_factory=datetime.now)

# Stage 2: Add new fields to the User model
class UserV2(EasyModel, table=True):
    """Enhanced user model with additional fields."""
    __tablename__ = "user"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True)
    email: str = Field(unique=True)
    full_name: Optional[str] = Field(default=None)  # New field
    is_active: bool = Field(default=True)  # New field
    last_login: Optional[datetime] = Field(default=None)  # New field
    created_at: datetime = Field(default_factory=datetime.now)

# Stage 3: Add a new model with relationship to User
class UserV3(EasyModel, table=True):
    """User model with relationships."""
    __tablename__ = "user"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True)
    email: str = Field(unique=True)
    full_name: Optional[str] = Field(default=None)
    is_active: bool = Field(default=True)
    last_login: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.now)
    
    # Relationship field will be populated automatically
    posts: List["PostV1"] = Relationship(back_populates="author")

class PostV1(EasyModel, table=True):
    """Blog post model with user relationship."""
    __tablename__ = "post"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    content: str
    published: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.now)
    
    # Relationship to User model
    author_id: int = Field(foreign_key="user.id")
    author: UserV3 = Relationship(back_populates="posts")

# Stage 4: Modify field types and add another related model
class UserV4(EasyModel, table=True):
    """User model with modified fields and additional relationships."""
    __tablename__ = "user"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(max_length=50, index=True)  # Added max_length constraint
    email: str = Field(unique=True)
    full_name: Optional[str] = Field(default=None, max_length=100)  # Added max_length
    is_active: bool = Field(default=True)
    last_login: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.now)
    
    # Relationships
    posts: List["PostV2"] = Relationship(back_populates="author")
    comments: List["CommentV1"] = Relationship(back_populates="author")

class PostV2(EasyModel, table=True):
    """Enhanced blog post model."""
    __tablename__ = "post"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(max_length=200, index=True)  # Added max_length
    content: str
    summary: Optional[str] = Field(default=None, max_length=500)  # New field
    published: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.now)
    
    # Relationships
    author_id: int = Field(foreign_key="user.id")
    author: UserV4 = Relationship(back_populates="posts")
    comments: List["CommentV1"] = Relationship(back_populates="post")

class CommentV1(EasyModel, table=True):
    """Comment model with relationships to both User and Post."""
    __tablename__ = "comment"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    content: str
    created_at: datetime = Field(default_factory=datetime.now)
    
    # Relationships
    author_id: int = Field(foreign_key="user.id")
    author: UserV4 = Relationship(back_populates="comments")
    
    post_id: int = Field(foreign_key="post.id")
    post: PostV2 = Relationship(back_populates="comments")

# Stage 5: Using MigrationManager API directly
class TagV1(EasyModel, table=True):
    """Tag model for categorizing posts."""
    __tablename__ = "tag"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True)
    description: Optional[str] = Field(default=None)

# Helper function to display migration tracking information
async def show_migration_info():
    """Display the current migration tracking information."""
    model_hashes_path = Path(MIGRATIONS_DIR) / "model_hashes.json"
    migration_history_path = Path(MIGRATIONS_DIR) / "migration_history.json"
    
    print("\nModel Hashes:")
    if model_hashes_path.exists():
        with open(model_hashes_path, 'r') as f:
            hashes = json.load(f)
            for model_name, hash_value in hashes.items():
                print(f"  {model_name}: {hash_value[:8]}...")
    else:
        print("  No model hashes file found.")
    
    print("\nMigration History:")
    if migration_history_path.exists():
        with open(migration_history_path, 'r') as f:
            history = json.load(f)
            # Check if history is a dictionary with 'migrations' key
            if isinstance(history, dict) and 'migrations' in history:
                migrations = history['migrations']
                if not migrations:
                    print("  No migrations recorded yet.")
                for entry in migrations:
                    if isinstance(entry, dict) and 'timestamp' in entry:
                        dt = datetime.fromisoformat(entry['timestamp'])
                        formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S")
                        operations = entry.get('operations', [])
                        ops_str = ', '.join(op.get('operation', 'unknown') for op in operations)
                        print(f"  {formatted_time} - {entry.get('model', 'unknown')}: {ops_str}")
            else:
                print("  Migration history file has an unexpected format.")
    else:
        print("  No migration history file found.")

# Stage 1: Initial setup
async def stage1():
    """Stage 1: Create initial database with basic User model."""
    print("\n========== STAGE 1: INITIAL SETUP ==========\n")
    
    # Initialize the database with our model
    await init_db(model_classes=[UserV1])
    print("Initial database created with User model.")
    
    # Create a sample user
    user = await UserV1.insert({
        "username": "john_doe", 
        "email": "john@example.com"
    })
    
    print(f"Created user: {user.username} ({user.email})")
    
    # Retrieve all users
    users = await UserV1.all()
    print(f"Total users: {len(users)}")
    
    # Display migration tracking information
    await show_migration_info()

# Stage 2: Add new fields
async def stage2():
    """Stage 2: Add new fields to the User model."""
    print("\n========== STAGE 2: ADDING NEW FIELDS ==========\n")
    
    # Initialize the database with our updated model
    await init_db(model_classes=[UserV2])
    print("Applied migrations to add new fields to User model.")
    
    # Retrieve existing users
    users = await UserV2.all()
    print(f"Retrieved {len(users)} existing users.")
    
    # Update the existing user with new fields
    user = users[0]
    updated_user = await UserV2.update(user.id, {
        "full_name": "John Doe",
        "last_login": datetime.now()
    })
    print(f"Updated user: {updated_user.username} with full_name: {updated_user.full_name}")
    
    # Create a new user with all fields
    new_user = await UserV2.insert({
        "username": "jane_smith",
        "email": "jane@example.com",
        "full_name": "Jane Smith",
        "is_active": True,
        "last_login": datetime.now()
    })
    
    print(f"Created new user: {new_user.username} ({new_user.full_name})")
    
    # Display migration tracking information
    await show_migration_info()

# Stage 3: Add new models with relationships
async def stage3():
    """Stage 3: Add a new Post model with relationship to User."""
    print("\n========== STAGE 3: ADDING RELATED MODELS ==========\n")
    
    # Initialize the database with our updated models
    await init_db(model_classes=[UserV3, PostV1])
    print("Applied migrations to create Post model and relationships.")
    
    # Retrieve existing users
    users = await UserV3.all()
    
    # Create posts for the first user
    user = users[0]
    post1 = await PostV1.insert({
        "title": "First Post",
        "content": "This is my first blog post!",
        "author_id": user.id
    })
    
    post2 = await PostV1.insert({
        "title": "Second Post",
        "content": "This is my second blog post!",
        "author_id": user.id
    })
    
    print(f"Created 2 posts for user: {user.username}")
    
    # Retrieve users with posts
    users_with_posts = await UserV3.all(include_relationships=True)
    user_with_posts = users_with_posts[0]
    print(f"User {user_with_posts.username} has {len(user_with_posts.posts)} posts")
    
    # Display migration tracking information
    await show_migration_info()

# Stage 4: Modify field types and add more relationships
async def stage4():
    """Stage 4: Modify field types and add Comment model."""
    print("\n========== STAGE 4: MODIFYING FIELD TYPES AND MORE RELATIONSHIPS ==========\n")
    
    # Initialize the database with our updated models
    await init_db(model_classes=[UserV4, PostV2, CommentV1])
    print("Applied migrations to modify field types and create Comment model.")
    
    # Retrieve existing posts
    posts = await PostV2.all()
    
    # Update the existing post to add a summary
    post = posts[0]
    updated_post = await PostV2.update(post.id, {
        "summary": "A short summary of the first blog post."
    })
    print(f"Updated post '{updated_post.title}' with a summary")
    
    # Create comments for the post
    user = await UserV4.get_by_id(post.author_id)
    
    comment1 = await CommentV1.insert({
        "content": "Great post!",
        "author_id": user.id,
        "post_id": post.id
    })
    
    # Get the second user to add a comment
    users = await UserV4.all()
    second_user = users[1] if len(users) > 1 else users[0]
    
    comment2 = await CommentV1.insert({
        "content": "Thanks for sharing this.",
        "author_id": second_user.id,
        "post_id": post.id
    })
    
    print(f"Added 2 comments to post '{post.title}'")
    
    # Retrieve post with comments
    post_with_comments = await PostV2.get_with_related(post.id, "comments", "author")
    print(f"Post '{post_with_comments.title}' has {len(post_with_comments.comments)} comments")
    
    # Display migration tracking information
    await show_migration_info()

# Stage 5: Using MigrationManager API directly
async def stage5():
    """Stage 5: Using MigrationManager API directly."""
    print("\n========== STAGE 5: USING MIGRATION MANAGER API ==========\n")
    
    # Create a MigrationManager instance for demonstration purposes
    migration_manager = MigrationManager(base_dir=os.getcwd())
    
    # Check for pending migrations without applying them
    pending_changes = await migration_manager.detect_model_changes([TagV1])
    
    print("Pending changes detected:")
    for model_name, changes in pending_changes.items():
        print(f"  Model: {model_name}")
        # Handle different structures that might be returned
        if isinstance(changes, list):
            for change in changes:
                if isinstance(change, dict):
                    print(f"    - {change.get('operation', 'unknown')}: {change.get('table_name', '')}")
                else:
                    print(f"    - {change}")
        else:
            print(f"    - {changes}")
    
    # Apply migrations for the Tag model
    await init_db(model_classes=[TagV1])
    print("\nApplied migrations for Tag model")
    
    # Create some tags
    tag1 = await TagV1.insert({
        "name": "technology", 
        "description": "Tech-related content"
    })
    
    tag2 = await TagV1.insert({
        "name": "tutorial", 
        "description": "How-to guides and tutorials"
    })
    
    print(f"Created tags: {tag1.name}, {tag2.name}")
    
    # Display final migration information
    await show_migration_info()

# Main function to run the example
async def main():
    """Run the complete migration example."""
    # Clear any previous state
    clear_previous_state()
    
    # Set up database configuration
    setup_db_config()
    
    # Run through all stages
    await stage1()  # Initial setup
    await stage2()  # Add new fields
    await stage3()  # Add new models with relationships
    await stage4()  # Modify field types and add more relationships
    await stage5()  # Use MigrationManager API directly
    
    print("\n========== EXAMPLE COMPLETE ==========")
    print("\nThe example has demonstrated how EasyModel handles:")
    print("  1. Creating initial database schema")
    print("  2. Adding new fields to existing models")
    print("  3. Adding new models with relationships")
    print("  4. Modifying field types")
    print("  5. Using MigrationManager API directly")
    print("\nMigration information is stored in the .easy_model_migrations directory.")

# Run the example
if __name__ == "__main__":
    asyncio.run(main())
