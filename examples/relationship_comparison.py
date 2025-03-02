"""
This example demonstrates the difference between manual relationship definition and automatic relationship detection.

Manual relationships require explicit definition of Relationship fields, while automatic relationships are detected based on
foreign key fields without requiring any additional code.

Both approaches achieve the same end result, but automatic relationship detection makes the code more concise.
"""

import os
import asyncio
from sqlmodel import Field, SQLModel, Relationship
from typing import List, Optional

from async_easy_model.model import EasyModel
from async_easy_model.auto_relationships import process_all_models_for_relationships, enable_auto_relationships

# Enable auto relationships
enable_auto_relationships()

# Define database URL (SQLite)
DATABASE_URL = "sqlite:///./test_relationship_comparison.db"

# 1. Manual Relationship Definition (Explicit)
class ManualAuthor(EasyModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    books: List["ManualBook"] = Relationship(back_populates="author")


class ManualBook(EasyModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    author_id: Optional[int] = Field(default=None, foreign_key="manual_author.id")
    author: Optional[ManualAuthor] = Relationship(back_populates="books")


# 2. Automatic Relationship Detection (Implicit)
class AutoAuthor(EasyModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str


class AutoBook(EasyModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    author_id: Optional[int] = Field(
        default=None, foreign_key="auto_author.id", description="Foreign key to the author"
    )


def debug_foreign_key_attr(model_cls, attr_name="author_id"):
    """Debug foreign key attribute of a model class"""
    print(f"\n=== Debugging Foreign Key Attribute ===")
    
    # Check if the attribute is a foreign key
    field_info = None
    foreign_key = None
    
    if hasattr(model_cls, "__fields__") and attr_name in model_cls.__fields__:
        field_info = model_cls.__fields__[attr_name]
        if hasattr(field_info, "foreign_key"):
            foreign_key = field_info.foreign_key
    elif hasattr(model_cls, "model_fields") and attr_name in model_cls.model_fields:
        field_info = model_cls.model_fields[attr_name]
        if hasattr(field_info, "foreign_key"):
            foreign_key = field_info.foreign_key
    
    print(f"{model_cls.__name__}.{attr_name} foreign_key: {foreign_key}")
    
    if foreign_key:
        # Extract target model name from foreign_key
        parts = foreign_key.split(".")
        if len(parts) >= 2:
            target_table = parts[0]
            print(f"Target table name: {target_table}")


def debug_model_fields(model_cls):
    """Debug the foreign key detection for a model class."""
    print(f"\n=== Debugging Foreign Key Detection ===")
    # Check if the field exists in the class
    attr_name = "author_id"  # example field name
    print(f"{model_cls.__name__}.{attr_name} is a field: {hasattr(model_cls, attr_name)}")
    
    # Check if field exists in __fields__ or model_fields
    if hasattr(model_cls, "__fields__"):
        print(f"{model_cls.__name__}.__fields__ contains {attr_name}: {attr_name in model_cls.__fields__}")
    
    if hasattr(model_cls, "model_fields"):
        print(f"{model_cls.__name__}.model_fields contains {attr_name}: {attr_name in model_cls.model_fields}")
    
    # Get field info
    field_info = None
    if hasattr(model_cls, "__fields__") and attr_name in model_cls.__fields__:
        field_info = model_cls.__fields__[attr_name]
    elif hasattr(model_cls, "model_fields") and attr_name in model_cls.model_fields:
        field_info = model_cls.model_fields[attr_name]
    
    if field_info:
        # Get field info safely without assuming specific attributes
        print(f"Field info: annotation={getattr(field_info, 'annotation', None)} default={getattr(field_info, 'default', None)} description='{getattr(field_info, 'description', None)}'")
        
        # Print all attributes of the field info
        print("\nField attributes:")
        for attr in dir(field_info):
            if not attr.startswith("__"):
                try:
                    attr_value = getattr(field_info, attr)
                    print(f"  - {attr}: {attr_value}")
                except Exception as e:
                    print(f"  - {attr}: Error accessing: {e}")
    
    # Manually look for foreign keys
    print("\nManually looking for foreign keys in AutoBook:")
    from async_easy_model.auto_relationships import get_foreign_keys_from_model
    foreign_keys = get_foreign_keys_from_model(AutoBook)
    print(f"Found foreign keys: {foreign_keys}")


def debug_relationships(model_cls):
    """Debug the relationships of a model class."""
    print(f"\n=== Debugging Relationships for {model_cls.__name__} ===")
    
    # Get relationships from SQLModel
    rels = {}
    
    # Try to access _sa_relationship_props (SQLAlchemy relationships)
    if hasattr(model_cls, "_sa_relationship_props"):
        print(f"Found _sa_relationship_props: {list(model_cls._sa_relationship_props.keys())}")
        for name, rel in model_cls._sa_relationship_props.items():
            target = rel.mapper.class_ if rel.mapper else None
            back_populates = rel.back_populates
            rels[name] = {
                "target": target.__name__ if target else None,
                "back_populates": back_populates
            }
    else:
        print("No _sa_relationship_props found")
    
    # Check for relationships in __annotations__
    if hasattr(model_cls, "__annotations__"):
        print(f"Annotations: {model_cls.__annotations__}")
    
    return rels


def process_manual_relationships():
    """Inspect the manual relationship definitions."""
    manual_rels = {}
    manual_rels["ManualAuthor"] = debug_relationships(ManualAuthor)
    manual_rels["ManualBook"] = debug_relationships(ManualBook)
    
    # Pretty print
    print("\n=== Manual Relationship Definition ===")
    for model_name, rels in manual_rels.items():
        for rel_name, rel_info in rels.items():
            target = rel_info["target"]
            back_pop = rel_info["back_populates"]
            print(f"{model_name}.{rel_name}: target={target}, back_populates='{back_pop}'")


def process_auto_relationships():
    """Process and inspect the automatic relationship detection."""
    # Apply automatic relationship detection
    process_all_models_for_relationships()
    
    # Debug fields
    debug_model_fields(AutoBook)
    debug_foreign_key_attr(AutoBook)
    
    # Inspect the results
    auto_rels = {}
    auto_rels["AutoAuthor"] = debug_relationships(AutoAuthor)
    auto_rels["AutoBook"] = debug_relationships(AutoBook)
    
    # Pretty print
    print("\n=== Automatic Relationship Detection ===")
    for model_name, rels in auto_rels.items():
        for rel_name, rel_info in rels.items():
            target = rel_info["target"]
            back_pop = rel_info["back_populates"]
            print(f"{model_name}.{rel_name}: target={target}, back_populates='{back_pop}'")
    
    print("\nBoth approaches achieve the same result, but automatic relationship detection requires less code!")


async def create_and_retrieve_data():
    """Create and retrieve data using both manual and auto relationships."""
    # Setup database
    os.environ["DATABASE_URL"] = DATABASE_URL
    
    # Import database initialization
    from async_easy_model.model import init_db
    await init_db()
    
    # Create tables using SQLite
    from sqlmodel import SQLModel
    from async_easy_model.model import get_engine
    
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    
    try:
        # Create data with manual relationships
        manual_author = ManualAuthor(name="John Doe")
        await manual_author.insert()
        
        manual_book = ManualBook(title="Manual Relationships in SQLModel", author_id=manual_author.id)
        await manual_book.insert()
        
        # Create data with auto relationships
        auto_author = AutoAuthor(name="Jane Doe")
        await auto_author.insert()
        
        auto_book = AutoBook(title="Automatic Relationships in SQLModel", author_id=auto_author.id)
        await auto_book.insert()
        
        # Retrieve data with relationships
        print("\n=== Retrieving Data with Relationships ===")
        
        # Manual
        retrieved_manual_book = await ManualBook.get_by_id(manual_book.id, include_relationships=True)
        print("\nManual Relationships:")
        print(f"Book: {retrieved_manual_book.title}")
        print(f"Author: {retrieved_manual_book.author.name if retrieved_manual_book.author else 'No author'}")
        
        # Auto
        retrieved_auto_book = await AutoBook.get_by_id(auto_book.id, include_relationships=True)
        print("\nAutomatic Relationships:")
        print(f"Book: {retrieved_auto_book.title}")
        print(f"Author: {retrieved_auto_book.author.name if retrieved_auto_book.author else 'No author'}")
        
        # Retrieve from the other side (author -> books)
        retrieved_manual_author = await ManualAuthor.get_by_id(manual_author.id, include_relationships=True)
        print("\nManual Author's Books:")
        for book in retrieved_manual_author.books:
            print(f"- {book.title}")
        
        retrieved_auto_author = await AutoAuthor.get_by_id(auto_author.id, include_relationships=True)
        print("\nAutomatic Author's Books:")
        for book in retrieved_auto_author.books:
            print(f"- {book.title}")
    
    except Exception as e:
        print(f"Error during data operations: {e}")


if __name__ == "__main__":
    # Process relationships
    process_manual_relationships()
    process_auto_relationships()
    
    # Create and retrieve data
    print("\nRunning data creation and retrieval...")
    asyncio.run(create_and_retrieve_data())
