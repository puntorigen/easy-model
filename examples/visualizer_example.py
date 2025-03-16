"""
Example of using ModelVisualizer to generate an ER diagram for EasyModel models.

This script demonstrates how to:
1. Define EasyModel model classes
2. Initialize the database
3. Use ModelVisualizer to generate a Mermaid ER diagram

Note: We don't set relationships directly on the model classes, as EasyModel
automatically handles relationships based on foreign keys.
"""

import os
import asyncio
from typing import Optional, List
from sqlmodel import Field, SQLModel
from async_easy_model import EasyModel, init_db, db_config, ModelVisualizer


# Define some example models
class Author(EasyModel, table=True):
    """Author model with books relationship."""
    __tablename__ = "author"
    name: str
    email: Optional[str] = None


class Tag(EasyModel, table=True):
    """Tag model that can be associated with books."""
    __tablename__ = "tag"
    name: str


class Book(EasyModel, table=True):
    """Book model with author relationship and tags through many-to-many."""
    __tablename__ = "book"
    title: str
    author_id: Optional[int] = Field(default=None, foreign_key="author.id")
    isbn: Optional[str] = None
    published_year: Optional[int] = None


class BookTag(EasyModel, table=True):
    """Junction table for many-to-many relationship between Book and Tag."""
    __tablename__ = "book_tag"
    book_id: int = Field(foreign_key="book.id")
    tag_id: int = Field(foreign_key="tag.id")


class Review(EasyModel, table=True):
    """Review model with a relationship to Book."""
    __tablename__ = "review"
    book_id: int = Field(foreign_key="book.id")
    rating: int
    comment: Optional[str] = None
    reviewer_name: str


async def main():
    """
    Main function to initialize the database and generate the ER diagram.
    """
    # Configure SQLite database in memory for this example
    db_config.configure_sqlite(":memory:")
    
    # Define the model classes we'll use
    models = [Author, Book, Tag, BookTag, Review]
    
    try:
        # Initialize the database with our models
        # Don't perform any relationship registration here, as we're only interested in visualization
        await init_db(model_classes=models)
        print("Database initialized successfully")
        
        # Create a visualizer instance
        visualizer = ModelVisualizer()
        
        # Generate the Mermaid ER diagram
        er_diagram = visualizer.mermaid()
        
        # Print the ER diagram markup
        print("\nGenerated Mermaid ER Diagram:\n")
        print(er_diagram)
        
        # Optionally, save the diagram to a file
        with open("er_diagram.md", "w") as f:
            f.write("# Database Schema ER Diagram\n\n")
            f.write("This diagram shows the database schema with tables, fields, and relationships.\n\n")
            f.write(er_diagram)
        
        print("\nER diagram saved to er_diagram.md")
        
        # Explain what the diagram shows
        print("\nThe ER diagram visualizes:")
        print("1. All tables (Author, Book, Tag, BookTag, Review)")
        print("2. Fields with their data types")
        print("3. Primary keys (PK) and Foreign keys (FK)")
        print("4. Relationships between tables:")
        print("   - One-to-many relationships (identified by foreign keys)")
        print("   - Many-to-many relationship between Books and Tags (via BookTag junction table)")
        
        print("\nImportant visualization features:")
        print("- Primary keys are automatically identified")
        print("- Foreign keys are detected and shown with FK indicator")
        print("- Junction tables are recognized for many-to-many relationships")
        print("- Relationship cardinality is displayed using Mermaid notation:")
        print("  - ||--o{ : One-to-many")
        print("  - }o--o{ : Many-to-many")
    
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
