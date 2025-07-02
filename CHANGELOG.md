# Changelog

All notable changes to the async-easy-model package will be documented in this file.

## [0.3.1] - 2025-06-30

### Fixed
- **Pydantic V2 Compatibility**: Fixed all deprecated `__fields__` usage, replaced with `model_fields`
- **SQLAlchemy Compatibility**: Fixed deprecated `Column.copy()` usage in migrations module
- Eliminated all deprecation warnings when using Pydantic V2.x and modern SQLAlchemy
- Updated auto_relationships.py, model.py, visualization.py, and migrations.py for modern API compliance
- No breaking changes - all functionality remains identical

### Technical Details
- Replaced 7 instances of deprecated `__fields__` with `model_fields` across codebase
- Replaced `Column.copy()` with manual column creation in migration system
- All changes maintain full backward compatibility
- Package now fully compliant with Pydantic V2 and SQLAlchemy 2.x standards

## [0.3.0] - 2025-06-30

### Added
- **PostgreSQL DateTime Compatibility**: Automatic datetime normalization for PostgreSQL TIMESTAMP WITHOUT TIME ZONE columns
- Backend detection system that automatically converts timezone-aware datetimes to timezone-naive for PostgreSQL
- Maintains backward compatibility with SQLite by preserving timezone-aware datetimes
- Comprehensive datetime handling in `insert()` and `update()` methods
- Updated event listener for `updated_at` field to use normalized datetimes

### Fixed
- **CRITICAL**: Fixed `asyncpg.exceptions.DataError` when using timezone-aware datetimes with PostgreSQL
- Resolved "can't subtract offset-naive and offset-aware datetimes" errors during database operations
- EasyModel now automatically detects PostgreSQL backend and normalizes datetime objects transparently

### Technical Details
- Added `_normalize_datetime_for_db()` helper function for datetime conversion
- Added `_normalize_data_for_db()` for batch datetime normalization
- Added `_get_normalized_datetime()` for backend-appropriate datetime generation
- Updated `created_at` and `updated_at` field defaults to use normalized datetime function
- All changes are transparent to application code - no API changes required

## [0.2.9] - 2025-06-29

### Fixed
- **CRITICAL**: Enhanced async session management with explicit exception handling and cleanup
- **CRITICAL**: Fixed memory leaks from unclosed database sessions
- **CRITICAL**: Improved connection pool configuration for all database types (not just PostgreSQL)
- Added explicit `await session.rollback()` on exceptions to prevent hanging transactions
- Added explicit `await session.close()` in finally blocks to guarantee session cleanup
- Extended connection pool settings (pool_size, max_overflow, pool_timeout, pool_recycle, pool_pre_ping) to all database types
- Improved session lifecycle documentation and error handling

### Changed
- Enhanced `get_session()` method with robust cleanup patterns
- Connection pool configuration now applies universally instead of PostgreSQL-only

## [0.2.5] - 2025-03-15

### Added
- New visualization class for database schema diagram generation
- Method `mermaid` for generating mermaid.js ER diagrams of defined models
- Method `mermaid_link` to generate and return a mermaid.live link with the database schema
- Customizable title support for database schema diagrams

## [0.2.4] - 2025-03-15

### Added
- Comprehensive support for many-to-many relationships
- Automatic detection of many-to-many relationships through junction tables
- Virtual relationship fields (using pluralized names) for many-to-many relationships
- Support for inserting, updating and deleting records with many-to-many relationships
- Junction table records automatically managed when models are deleted

### Fixed
- Improvements to nested data handling in query results
- Bug fixes around nesting returned data on insert and select methods

## [0.2.3] - 2025-03-14

### Changed
- Implemented nested insertion support directly within the `insert` method
- Eliminated need for separate `insert_with_related` method as all functionality is now handled by `insert`

### Documentation
- Updated documentation to reflect new insertion capabilities
- Updated examples and tutorial

## [0.2.2] - 2025-03-14

### Changed
- Renamed `create_with_related` to `insert_with_related` for API consistency

### Documentation
- Improved README with better examples
- Enhanced documentation styling

## [0.2.1] - 2025-03-14

### Added
- Ability to access virtual fields (relationships) as table fields directly within the results of a `select` method

### Fixed
- Fixed `to_dict` method for nested related results
- Fixed auto-relationships detection and management (enabled by default)

## [0.2.0] - 2025-03-14

### Changed
- Standardized API methods for more intuitive and consistent usage
- Enhanced relationship handling capabilities

## [0.1.12] - 2025-03-14

### Added
- Support for automatic database migrations
- Migration example script

### Improved
- Enhanced base class `EasyModel` to allow extending existing table definitions implicitly
- No need to specify `extend_existing` argument when annotating tables

## [0.1.11] - 2025-03-03

### Added
- Automatic relationship creation when using foreign_key fields
- Relation and Field helper methods

### Documentation
- Improved documentation with examples

## [0.1.10] - 2025-03-01

### Added
- Support for optional `order_by` parameter in all query methods
- Flexible ordering with ascending/descending options (using "-" prefix)
- Multiple field ordering via lists
- Relationship field ordering using dot notation
- Helper methods `all()`, `first()`, and `limit()` for common query operations
- Support for populating relationship fields on query with `include_relationships` parameter
- Automatic `created_at` field

## [0.1.0] - 2025-02-23

### Added
- SQLite support alongside PostgreSQL
- Automatic database connection handling

### Fixed
- Improved compatibility between SQLite and PostgreSQL

## [0.0.1] - 2025-02-20

### Added
- Initial release
- Package renamed from original to async-easy-model
- Basic ORM functionality built on SQLModel
- Async database operations support
