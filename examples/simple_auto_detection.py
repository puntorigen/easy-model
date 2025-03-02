"""
Example demonstrating automatic relationship detection with SQLite.

This script shows how to enable automatic relationship detection based on foreign keys,
allowing you to use relationships without explicitly defining them.

Note: This approach uses explicit SQLModel Relationships to avoid conflicts 
with SQLModel's metaclass, but demonstrates how the automatic detection works.
"""

import os
import sys
import asyncio
from typing import List, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

# Ensure we're using the local package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Field, SQLModel, Relationship
from async_easy_model.model import EasyModel, init_db, db_config
from async_easy_model.auto_relationships import enable_auto_relationships, setup_relationship_between_models

# Configure SQLite database
db_config.configure_sqlite("./auto_detection.db")

# Enable auto relationships without patching the metaclass
enable_auto_relationships(patch_metaclass=False)

# Define models without relationship fields
class Department(EasyModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    # No explicit 'employees' relationship needed!

class Employee(EasyModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    job_title: str
    department_id: Optional[int] = Field(default=None, foreign_key="department.id")
    # No explicit 'department' relationship needed!

# Manually set up the relationships (simulating what the auto-detection would do)
def setup_relationships():
    """Set up relationships between models manually."""
    print("Setting up relationships between models manually...")
    setup_relationship_between_models(
        source_model=Employee,
        target_model=Department,
        foreign_key_name="department_id",
        source_attr_name="department",  # Employee.department
        target_attr_name="employees"    # Department.employees
    )
    print("Relationships set up successfully!")

async def run_example():
    """Run the auto-detection example."""
    print(f"Using database: {db_config.get_connection_url()}")
    
    # Set up relationships manually
    setup_relationships()
    
    # Initialize database
    await init_db()
    
    # Create tables
    engine = db_config.get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)
    
    try:
        # Create test data
        print("\n=== Creating test data ===")
        
        # Create departments
        engineering = await Department.insert({"name": "Engineering"})
        marketing = await Department.insert({"name": "Marketing"})
        
        # Create employees
        await Employee.insert({
            "name": "Alice Johnson",
            "job_title": "Software Engineer",
            "department_id": engineering.id
        })
        
        await Employee.insert({
            "name": "Bob Smith",
            "job_title": "Senior Developer",
            "department_id": engineering.id
        })
        
        await Employee.insert({
            "name": "Carol Williams",
            "job_title": "Marketing Specialist",
            "department_id": marketing.id
        })
        
        print("Created 2 departments and 3 employees")
        
        # Test retrieving with relationships
        print("\n=== Testing department with employees ===")
        dept = await Department.get_by_id(engineering.id, include_relationships=True)
        print(f"Department: {dept.name}")
        print(f"Employees in {dept.name}:")
        for emp in dept.employees:
            print(f"  - {emp.name}, {emp.job_title}")
        
        print("\n=== Testing employee with department ===")
        emp = await Employee.get_by_attribute(name="Carol Williams", all=True, include_relationships=True)
        if emp and len(emp) > 0:
            employee = emp[0]
            print(f"Employee: {employee.name}, {employee.job_title}")
            print(f"Department: {employee.department.name}")
        
        print("\n=== Testing all() with relationships ===")
        all_employees = await Employee.all(include_relationships=True)
        for emp in all_employees:
            print(f"Employee: {emp.name} works in {emp.department.name}")
            
    except Exception as e:
        print(f"Error during example: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up
        await engine.dispose()
        print("\nExample completed.")

if __name__ == "__main__":
    asyncio.run(run_example())
