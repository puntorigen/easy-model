"""
Compatibility Layer Demo - Showing how to use both EasyModel and SQLAlchemy APIs

This example demonstrates how the compatibility layer allows seamless usage of:
1. EasyModel's simplified async CRUD methods
2. Standard SQLAlchemy/SQLModel query patterns
3. Mixed usage patterns for gradual migration
"""

import asyncio
from typing import Optional, List
from datetime import datetime
from sqlmodel import Field, Relationship, select
from sqlalchemy import and_, or_, func
from async_easy_model import EasyModel, init_db, db_config
from async_easy_model.compat import selectinload, joinedload


class User(EasyModel, table=True):
    """User model demonstrating compatibility features"""
    __tablename__ = "users"
    
    username: str = Field(index=True, unique=True)
    email: str = Field(index=True)
    full_name: Optional[str] = None
    is_active: bool = Field(default=True)
    age: Optional[int] = None
    
    # Relationships
    posts: List["Post"] = Relationship(back_populates="author")
    comments: List["Comment"] = Relationship(back_populates="user")


class Post(EasyModel, table=True):
    """Post model with relationships"""
    __tablename__ = "posts"
    
    title: str
    content: str
    published: bool = Field(default=False)
    views: int = Field(default=0)
    
    # Foreign key
    author_id: int = Field(foreign_key="users.id")
    
    # Relationships
    author: User = Relationship(back_populates="posts")
    comments: List["Comment"] = Relationship(back_populates="post")
    tags: List["Tag"] = Relationship(back_populates="posts", link_model="PostTag")


class Comment(EasyModel, table=True):
    """Comment model"""
    __tablename__ = "comments"
    
    content: str
    
    # Foreign keys
    user_id: int = Field(foreign_key="users.id")
    post_id: int = Field(foreign_key="posts.id")
    
    # Relationships
    user: User = Relationship(back_populates="comments")
    post: Post = Relationship(back_populates="comments")


class Tag(EasyModel, table=True):
    """Tag model for posts"""
    __tablename__ = "tags"
    
    name: str = Field(unique=True)
    
    # Relationships
    posts: List[Post] = Relationship(back_populates="tags", link_model="PostTag")


class PostTag(EasyModel, table=True):
    """Junction table for Post-Tag many-to-many relationship"""
    __tablename__ = "post_tags"
    
    post_id: int = Field(foreign_key="posts.id", primary_key=True)
    tag_id: int = Field(foreign_key="tags.id", primary_key=True)


async def demo_easymodel_methods():
    """Demonstrate EasyModel's native async methods"""
    print("\n=== EasyModel Native Methods ===\n")
    
    # 1. Create users using EasyModel's insert method
    user1 = await User.insert({
        "username": "john_doe",
        "email": "john@example.com",
        "full_name": "John Doe",
        "age": 30
    })
    print(f"Created user with EasyModel: {user1.username}")
    
    # 2. Bulk insert
    users = await User.insert([
        {"username": "jane_smith", "email": "jane@example.com", "full_name": "Jane Smith", "age": 28},
        {"username": "bob_wilson", "email": "bob@example.com", "full_name": "Bob Wilson", "age": 35}
    ])
    print(f"Bulk created {len(users)} users")
    
    # 3. Query with relationships
    user_with_posts = await User.get_by_id(user1.id, include_relationships=True)
    print(f"Fetched user with relationships: {user_with_posts.username}")
    
    # 4. Update
    updated = await User.update(
        criteria={"username": "john_doe"},
        data={"age": 31}
    )
    print(f"Updated {updated} user(s)")
    
    # 5. Select with criteria
    active_users = await User.select(
        criteria={"is_active": True},
        all=True,
        order_by=["username"]
    )
    print(f"Found {len(active_users)} active users")
    
    return user1


async def demo_sqlalchemy_compat():
    """Demonstrate SQLAlchemy compatibility methods"""
    print("\n=== SQLAlchemy Compatibility Methods ===\n")
    
    # 1. Using the familiar create() method (alias for insert)
    user = await User.create(
        username="alice_wonder",
        email="alice@example.com",
        full_name="Alice Wonderland",
        age=25
    )
    print(f"Created user with create(): {user.username}")
    
    # 2. Using save() method on instance
    new_user = User(
        username="charlie_brown",
        email="charlie@example.com",
        full_name="Charlie Brown",
        age=22
    )
    await new_user.save()
    print(f"Saved user with save(): {new_user.username}")
    
    # 3. Using find() and find_by() methods
    found_user = await User.find(user.id)
    print(f"Found user by ID: {found_user.username}")
    
    user_by_email = await User.find_by(email="alice@example.com")
    print(f"Found user by email: {user_by_email.username}")
    
    # 4. Using exists() and count()
    exists = await User.exists(username="alice_wonder")
    print(f"User alice_wonder exists: {exists}")
    
    total_users = await User.count()
    active_count = await User.count({"is_active": True})
    print(f"Total users: {total_users}, Active users: {active_count}")
    
    # 5. Instance methods
    await new_user.refresh()
    print(f"Refreshed user: {new_user.username}")
    
    return user


async def demo_query_builder():
    """Demonstrate the AsyncQuery builder pattern"""
    print("\n=== AsyncQuery Builder Pattern ===\n")
    
    # 1. Simple query with filter
    users = await User.query().filter(User.age > 25).all()
    print(f"Users older than 25: {len(users)}")
    
    # 2. Query with filter_by
    user = await User.query().filter_by(username="alice_wonder").first()
    print(f"Found user with filter_by: {user.username if user else 'None'}")
    
    # 3. Complex query with multiple filters
    young_active_users = await (
        User.query()
        .filter(User.age < 30)
        .filter(User.is_active == True)
        .order_by(User.username)
        .limit(5)
        .all()
    )
    print(f"Young active users: {len(young_active_users)}")
    
    # 4. Query with joins (after creating posts)
    # First create some posts
    post1 = await Post.create(
        title="First Post",
        content="Hello World",
        author_id=user.id,
        published=True
    )
    
    post2 = await Post.create(
        title="Second Post",
        content="Another post",
        author_id=user.id,
        published=False
    )
    
    # Query posts with author
    posts_with_author = await (
        Post.query()
        .join(User)
        .filter(User.username == "alice_wonder")
        .options(selectinload(Post.author))
        .all()
    )
    print(f"Posts by alice_wonder: {len(posts_with_author)}")
    
    # 5. Aggregation query
    post_count = await Post.query().filter(Post.published == True).count()
    print(f"Published posts: {post_count}")
    
    has_posts = await Post.query().filter(Post.author_id == user.id).exists()
    print(f"User has posts: {has_posts}")


async def demo_raw_sqlalchemy():
    """Demonstrate using raw SQLAlchemy patterns with session access"""
    print("\n=== Raw SQLAlchemy Patterns ===\n")
    
    # 1. Using session() context manager (alias for get_session)
    async with User.session() as session:
        # Build complex SQLAlchemy query
        stmt = (
            select(User)
            .where(
                and_(
                    User.is_active == True,
                    or_(
                        User.age > 25,
                        User.username.like("%smith%")
                    )
                )
            )
            .order_by(User.created_at.desc())
        )
        
        result = await session.execute(stmt)
        users = result.scalars().all()
        print(f"Complex query found {len(users)} users")
    
    # 2. Using select_stmt() helper
    stmt = User.select_stmt().where(User.email.like("%example.com"))
    async with User.session() as session:
        result = await session.execute(stmt)
        users = result.scalars().all()
        print(f"Users with example.com email: {len(users)}")
    
    # 3. Using update_stmt() helper
    stmt = User.update_stmt().where(User.username == "bob_wilson").values(age=36)
    async with User.session() as session:
        result = await session.execute(stmt)
        await session.commit()
        print(f"Updated {result.rowcount} rows with raw update")
    
    # 4. Aggregation with func
    async with User.session() as session:
        stmt = select(func.avg(User.age)).where(User.is_active == True)
        result = await session.execute(stmt)
        avg_age = result.scalar()
        print(f"Average age of active users: {avg_age:.1f}")
    
    # 5. Subquery example
    async with Post.session() as session:
        # Get users who have published posts
        subquery = (
            select(Post.author_id)
            .where(Post.published == True)
            .distinct()
            .subquery()
        )
        
        stmt = select(User).where(User.id.in_(select(subquery)))
        result = await session.execute(stmt)
        authors = result.scalars().all()
        print(f"Users with published posts: {len(authors)}")


async def demo_mixed_usage():
    """Demonstrate mixing EasyModel and SQLAlchemy patterns"""
    print("\n=== Mixed Usage Patterns ===\n")
    
    # 1. Create with EasyModel, query with SQLAlchemy
    tag1 = await Tag.insert({"name": "python"})
    tag2 = await Tag.insert({"name": "async"})
    
    # Query with SQLAlchemy pattern
    tags = await Tag.query().filter(Tag.name.in_(["python", "async"])).all()
    print(f"Found {len(tags)} tags")
    
    # 2. Create with compatibility method, update with EasyModel
    post = await Post.create(
        title="Mixed Usage Demo",
        content="Showing both APIs",
        author_id=1,
        published=False
    )
    
    # Update with EasyModel method
    await Post.update(
        criteria={"id": post.id},
        data={"published": True, "views": 100}
    )
    print("Updated post with EasyModel method")
    
    # 3. Complex relationship handling
    # Associate tags with post using junction table
    await PostTag.insert([
        {"post_id": post.id, "tag_id": tag1.id},
        {"post_id": post.id, "tag_id": tag2.id}
    ])
    
    # Query with relationships using EasyModel
    post_with_tags = await Post.get_by_id(post.id, include_relationships=True)
    print(f"Post has {len(post_with_tags.tags) if hasattr(post_with_tags, 'tags') else 0} tags")
    
    # 4. Bulk operations with both patterns
    # Bulk create with compatibility method
    comments = await Comment.bulk_create([
        {"content": "Great post!", "user_id": 1, "post_id": post.id},
        {"content": "Thanks for sharing", "user_id": 2, "post_id": post.id}
    ])
    print(f"Created {len(comments)} comments")
    
    # Query with SQLAlchemy pattern
    comment_count = await Comment.query().filter(Comment.post_id == post.id).count()
    print(f"Post has {comment_count} comments")


async def main():
    """Run all demonstrations"""
    print("\n" + "="*60)
    print("   EasyModel & SQLAlchemy Compatibility Layer Demo")
    print("="*60)
    
    # Configure database
    db_config.configure_sqlite(database="compatibility_demo.db")
    
    # Initialize database
    await init_db()
    
    # Run demonstrations
    try:
        # 1. Demo EasyModel native methods
        user = await demo_easymodel_methods()
        
        # 2. Demo SQLAlchemy compatibility methods
        await demo_sqlalchemy_compat()
        
        # 3. Demo query builder pattern
        await demo_query_builder()
        
        # 4. Demo raw SQLAlchemy patterns
        await demo_raw_sqlalchemy()
        
        # 5. Demo mixed usage
        await demo_mixed_usage()
        
        print("\n" + "="*60)
        print("   Compatibility Layer Demo Complete!")
        print("="*60)
        print("\nKey Takeaways:")
        print("✓ EasyModel methods work as before - no breaking changes")
        print("✓ SQLAlchemy-style methods available via compatibility layer")
        print("✓ AsyncQuery builder provides familiar query interface")
        print("✓ Direct session access for complex SQLAlchemy queries")
        print("✓ Seamless mixing of both APIs in the same codebase")
        print("✓ Gradual migration path from SQLAlchemy to EasyModel")
        
    except Exception as e:
        print(f"\nError during demo: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
