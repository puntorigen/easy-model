"""
SQLAlchemy/SQLModel Compatibility Layer for EasyModel

This module provides a compatibility layer that allows users to use standard
SQLAlchemy/SQLModel patterns alongside EasyModel's simplified API.
"""

from typing import Type, TypeVar, Optional, Any, List, Dict, Union, Generic, cast, TYPE_CHECKING, overload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload, Query
from sqlalchemy import select, update, delete, and_, or_, func
from sqlmodel import SQLModel
import contextlib
import sys

# For Python 3.11+ use Self, otherwise use TypeVar
if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

if TYPE_CHECKING:
    from .model import EasyModel

T = TypeVar("T", bound="EasyModel")


class SQLAlchemyCompatMixin:
    """
    Mixin class that provides SQLAlchemy/SQLModel compatibility methods.
    This allows users to use familiar SQLAlchemy patterns with EasyModel.
    """
    
    @classmethod
    @contextlib.asynccontextmanager
    async def session(cls):
        """
        Get a database session using standard SQLAlchemy naming.
        This is an alias for get_session() to match SQLAlchemy conventions.
        
        Usage:
            async with User.session() as session:
                stmt = select(User).where(User.username == "john")
                result = await session.execute(stmt)
                user = result.scalar_one_or_none()
        """
        # Use the existing get_session method
        async with cls.get_session() as session:
            yield session
    
    @classmethod
    def query(cls: Type[T]) -> 'AsyncQuery[T]':
        """
        Create a query builder that mimics SQLAlchemy's query interface.
        Note: This returns an AsyncQuery immediately (not awaited) for chaining.
        
        Usage:
            users = await User.query().filter(User.is_active == True).all()
            user = await User.query().filter_by(username="john").first()
        """
        return AsyncQuery[T](cls)  # type: ignore
    
    async def save(self, session: Optional[AsyncSession] = None) -> 'EasyModel':
        """
        Save the current instance to the database (insert or update).
        Mimics the common save() pattern from other ORMs.
        
        Usage:
            user = User(username="john", email="john@example.com")
            await user.save()
        """
        if session:
            session.add(self)
            await session.commit()
            await session.refresh(self)
        else:
            async with self.get_session() as session:
                session.add(self)
                await session.commit()
                await session.refresh(self)
        return self
    
    async def refresh(self, session: Optional[AsyncSession] = None) -> 'EasyModel':
        """
        Refresh the instance from the database.
        
        Usage:
            await user.refresh()
        """
        if session:
            await session.refresh(self)
        else:
            async with self.get_session() as session:
                await session.refresh(self)
        return self
    
    async def delete_instance(self, session: Optional[AsyncSession] = None) -> None:
        """
        Delete this instance from the database.
        Named delete_instance to avoid conflict with the class method delete().
        
        Usage:
            await user.delete_instance()
        """
        if session:
            await session.delete(self)
            await session.commit()
        else:
            async with self.get_session() as session:
                # Merge the instance into the session context if needed
                merged = await session.merge(self)
                await session.delete(merged)
                await session.commit()
    
    @classmethod
    async def create(cls: Type[T], **kwargs) -> T:
        """
        Create and save a new instance in one step.
        Alias for insert() to match common ORM patterns.
        
        Usage:
            user = await User.create(username="john", email="john@example.com")
        """
        return await cls.insert(kwargs)
    
    @classmethod
    async def find(cls: Type[T], id: Any) -> Optional[T]:
        """
        Find a record by primary key.
        Alias for get_by_id() to match common ORM patterns.
        
        Usage:
            user = await User.find(1)
        """
        return await cls.get_by_id(id)
    
    @classmethod
    async def find_by(cls: Type[T], **kwargs) -> Optional[T]:
        """
        Find a single record by attributes.
        Alias for get_by_attribute() to match common ORM patterns.
        
        Usage:
            user = await User.find_by(username="john")
        """
        return await cls.get_by_attribute(**kwargs)
    
    @classmethod
    async def find_all(cls: Type[T], **kwargs) -> List[T]:
        """
        Find all records matching attributes.
        
        Usage:
            active_users = await User.find_all(is_active=True)
        """
        if kwargs:
            return await cls.get_by_attribute(all=True, **kwargs)
        else:
            return await cls.all()
    
    @classmethod
    async def count(cls: Type[T], criteria: Optional[Dict[str, Any]] = None) -> int:
        """
        Count records matching criteria.
        
        Usage:
            total_users = await User.count()
            active_users = await User.count({"is_active": True})
        """
        async with cls.get_session() as session:
            stmt = select(func.count()).select_from(cls)
            if criteria:
                for field, value in criteria.items():
                    stmt = stmt.where(getattr(cls, field) == value)
            result = await session.execute(stmt)
            return result.scalar() or 0
    
    @classmethod
    async def exists(cls: Type[T], **kwargs) -> bool:
        """
        Check if a record exists with the given attributes.
        
        Usage:
            if await User.exists(username="john"):
                print("Username already taken")
        """
        result = await cls.get_by_attribute(**kwargs)
        return result is not None
    
    @classmethod
    async def bulk_create(cls: Type[T], objects: List[Dict[str, Any]]) -> List[T]:
        """
        Create multiple records in a single transaction.
        Alias for insert() with a list.
        
        Usage:
            users = await User.bulk_create([
                {"username": "user1", "email": "user1@example.com"},
                {"username": "user2", "email": "user2@example.com"}
            ])
        """
        return await cls.insert(objects)
    
    @classmethod
    async def bulk_update(cls: Type[T], updates: List[Dict[str, Any]]) -> int:
        """
        Update multiple records based on their IDs.
        
        Args:
            updates: List of dicts containing 'id' and fields to update
        
        Usage:
            await User.bulk_update([
                {"id": 1, "is_active": False},
                {"id": 2, "email": "newemail@example.com"}
            ])
        """
        count = 0
        async with cls.get_session() as session:
            for update_data in updates:
                if 'id' not in update_data:
                    continue
                    
                obj_id = update_data.pop('id')
                stmt = update(cls).where(cls.id == obj_id).values(**update_data)
                result = await session.execute(stmt)
                count += result.rowcount
            
            await session.commit()
        return count
    
    @classmethod
    def select_stmt(cls: Type[T]) -> select:
        """
        Get a SQLAlchemy select statement for this model.
        This allows users to build complex queries using SQLAlchemy syntax.
        
        Usage:
            stmt = User.select_stmt().where(User.username.like("%john%"))
            async with User.session() as session:
                result = await session.execute(stmt)
                users = result.scalars().all()
        """
        return select(cls)
    
    @classmethod
    def update_stmt(cls: Type[T]) -> update:
        """
        Get a SQLAlchemy update statement for this model.
        
        Usage:
            stmt = User.update_stmt().where(User.id == 1).values(username="new_name")
            async with User.session() as session:
                await session.execute(stmt)
                await session.commit()
        """
        return update(cls)
    
    @classmethod
    def delete_stmt(cls: Type[T]) -> delete:
        """
        Get a SQLAlchemy delete statement for this model.
        
        Usage:
            stmt = User.delete_stmt().where(User.is_active == False)
            async with User.session() as session:
                await session.execute(stmt)
                await session.commit()
        """
        return delete(cls)


class AsyncQuery(Generic[T]):
    """
    Async query builder that mimics SQLAlchemy's Query interface.
    Provides a familiar API for users coming from SQLAlchemy.
    """
    
    def __init__(self, model_class: Type[T]):
        self.model_class: Type[T] = model_class
        self.statement = select(model_class)
        self._limit: Optional[int] = None
        self._offset: Optional[int] = None
        self._order_by: List = []
    
    def filter(self, *criterion) -> 'AsyncQuery[T]':
        """
        Add filter criteria using SQLAlchemy expressions.
        
        Usage:
            query.filter(User.age > 18, User.is_active == True)
        """
        for crit in criterion:
            self.statement = self.statement.where(crit)
        return self
    
    def filter_by(self, **kwargs) -> 'AsyncQuery[T]':
        """
        Add filter criteria using keyword arguments.
        
        Usage:
            query.filter_by(username="john", is_active=True)
        """
        for field, value in kwargs.items():
            self.statement = self.statement.where(getattr(self.model_class, field) == value)
        return self
    
    def order_by(self, *columns) -> 'AsyncQuery[T]':
        """
        Add ordering to the query.
        
        Usage:
            query.order_by(User.created_at.desc())
        """
        self._order_by.extend(columns)
        self.statement = self.statement.order_by(*columns)
        return self
    
    def limit(self, limit: int) -> 'AsyncQuery[T]':
        """
        Limit the number of results.
        
        Usage:
            query.limit(10)
        """
        self._limit = limit
        self.statement = self.statement.limit(limit)
        return self
    
    def offset(self, offset: int) -> 'AsyncQuery[T]':
        """
        Set the offset for results.
        
        Usage:
            query.offset(20)
        """
        self._offset = offset
        self.statement = self.statement.offset(offset)
        return self
    
    def options(self, *options) -> 'AsyncQuery[T]':
        """
        Add loading options (like eager loading).
        
        Usage:
            query.options(selectinload(User.posts))
        """
        self.statement = self.statement.options(*options)
        return self
    
    def join(self, *targets, **kwargs) -> 'AsyncQuery[T]':
        """
        Add a join to the query.
        
        Usage:
            query.join(Post).filter(Post.published == True)
        """
        self.statement = self.statement.join(*targets, **kwargs)
        return self
    
    def outerjoin(self, *targets, **kwargs) -> 'AsyncQuery[T]':
        """
        Add an outer join to the query.
        
        Usage:
            query.outerjoin(Post)
        """
        self.statement = self.statement.outerjoin(*targets, **kwargs)
        return self
    
    def group_by(self, *columns) -> 'AsyncQuery[T]':
        """
        Add GROUP BY clause.
        
        Usage:
            query.group_by(User.department_id)
        """
        self.statement = self.statement.group_by(*columns)
        return self
    
    def having(self, *criterion) -> 'AsyncQuery[T]':
        """
        Add HAVING clause.
        
        Usage:
            query.group_by(User.department_id).having(func.count(User.id) > 5)
        """
        self.statement = self.statement.having(*criterion)
        return self
    
    async def all(self) -> List[T]:
        """Execute the query and return all results."""
        async with self.model_class.get_session() as session:
            result = await session.execute(self.statement)
            return result.scalars().all()
    
    async def first(self) -> Optional[T]:
        """Execute the query and return the first result."""
        self.statement = self.statement.limit(1)
        async with self.model_class.get_session() as session:
            result = await session.execute(self.statement)
            return result.scalars().first()
    
    async def one(self) -> T:
        """Execute the query and return exactly one result, raise if not found."""
        async with self.model_class.get_session() as session:
            result = await session.execute(self.statement)
            return result.scalar_one()
    
    async def one_or_none(self) -> Optional[T]:
        """Execute the query and return one result or None."""
        async with self.model_class.get_session() as session:
            result = await session.execute(self.statement)
            return result.scalar_one_or_none()
    
    async def count(self) -> int:
        """Return the count of records matching the query."""
        count_stmt = select(func.count()).select_from(self.model_class)
        # Apply the same filters from the original statement
        if self.statement.whereclause is not None:
            count_stmt = count_stmt.where(self.statement.whereclause)
        
        async with self.model_class.get_session() as session:
            result = await session.execute(count_stmt)
            return result.scalar() or 0
    
    async def exists(self) -> bool:
        """Check if any records match the query."""
        count = await self.count()
        return count > 0


# Export commonly used SQLAlchemy constructs for convenience
__all__ = [
    'SQLAlchemyCompatMixin',
    'AsyncQuery',
    'select',
    'update',
    'delete',
    'and_',
    'or_',
    'func',
    'selectinload',
    'joinedload'
]
