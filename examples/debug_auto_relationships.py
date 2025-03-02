"""
Script to debug automatic relationship detection
"""

import sys
import os

# Add the parent directory to the Python path so we can import the local package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlmodel import SQLModel, Field, Relationship
from async_easy_model import enable_auto_relationships, EasyModel, disable_auto_relationships
import logging

# Set logging level to DEBUG
logging.basicConfig(level=logging.DEBUG)

# Disable first to ensure we start fresh
disable_auto_relationships()

# Define models BEFORE enabling auto-relationships
class Author(EasyModel, table=True):
    name: str = ""

class Book(EasyModel, table=True):
    title: str = ""
    author_id: int = Field(default=None, foreign_key="author.id")

# Check initial state
print("\nBEFORE enabling auto-relationships:")
print(f"Author relationships: {getattr(Author, '__sqlmodel_relationships__', None)}")
print(f"Book relationships: {getattr(Book, '__sqlmodel_relationships__', None)}")

# Now enable auto-relationships
enable_auto_relationships()

# Manually create a relationship to see how it's registered
class ManualAuthor(EasyModel, table=True):
    name: str = ""
    books: list["ManualBook"] = Relationship(back_populates="author")

class ManualBook(EasyModel, table=True):
    title: str = ""
    author_id: int = Field(default=None, foreign_key="manualauthor.id")
    author: "ManualAuthor" = Relationship(back_populates="books")

# Check relationship metadata
print("\nAFTER enabling auto-relationships:")
print(f"Author relationships: {getattr(Author, '__sqlmodel_relationships__', None)}")
print(f"Book relationships: {getattr(Book, '__sqlmodel_relationships__', None)}")
print(f"ManualAuthor relationships: {getattr(ManualAuthor, '__sqlmodel_relationships__', None)}")
print(f"ManualBook relationships: {getattr(ManualBook, '__sqlmodel_relationships__', None)}")

# Check if relationship attributes are directly available on the class
print("\nRelationship attributes:")
print(f"Author has 'books' attribute: {'books' in dir(Author)}")
print(f"Book has 'author' attribute: {'author' in dir(Book)}")
print(f"ManualAuthor has 'books' attribute: {'books' in dir(ManualAuthor)}")
print(f"ManualBook has 'author' attribute: {'author' in dir(ManualBook)}")

# Print all field and relationship info for the classes
for cls in [Author, Book, ManualAuthor, ManualBook]:
    print(f"\n{cls.__name__} fields and relationships:")
    for name in dir(cls):
        if not name.startswith('_') and hasattr(cls, name):
            attr = getattr(cls, name)
            if not callable(attr):
                print(f"  - {name}: {type(attr)}")
                if hasattr(attr, 'back_populates'):
                    print(f"    back_populates: {attr.back_populates}")

# Now, let's manually add relationships to our models
if 'books' not in dir(Author):
    books_rel = Relationship(back_populates="author", sa_relationship_kwargs={"lazy": "selectin"})
    setattr(Author, "books", books_rel)
    # Register with SQLModel metadata
    if not hasattr(Author, "__sqlmodel_relationships__"):
        Author.__sqlmodel_relationships__ = {}
    Author.__sqlmodel_relationships__["books"] = None
    print("\nManually added 'books' relationship to Author")

if 'author' not in dir(Book):
    author_rel = Relationship(back_populates="books", sa_relationship_kwargs={"lazy": "selectin"})
    setattr(Book, "author", author_rel)
    # Register with SQLModel metadata
    if not hasattr(Book, "__sqlmodel_relationships__"):
        Book.__sqlmodel_relationships__ = {}
    Book.__sqlmodel_relationships__["author"] = None
    print("Manually added 'author' relationship to Book")

# Check again after manual addition
print("\nAFTER manual relationship addition:")
print(f"Author has 'books' attribute: {'books' in dir(Author)}")
print(f"Book has 'author' attribute: {'author' in dir(Book)}")
print(f"Author relationships: {getattr(Author, '__sqlmodel_relationships__', None)}")
print(f"Book relationships: {getattr(Book, '__sqlmodel_relationships__', None)}")
