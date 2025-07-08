# Changelog

All notable changes to the async-easy-model package will be documented in this file.

## [0.3.7] - 2025-07-07

### Fixed
- **CRITICAL PERFORMANCE FIX**: Removed aggressive connection validation that occurred before every database session creation
- **Root Cause**: Version 0.3.6 introduced connection validation before every `get_session()` call, causing massive performance overhead and connection timeouts
- **Solution**: Moved connection validation to error-triggered mode only - now validates connection only when database errors occur

### Performance Improvements
- **Eliminated Connection Overhead**: Database sessions no longer have validation overhead unless there's an actual error
- **Faster Session Creation**: Removed unnecessary `SELECT 1` query and metadata refresh checks from normal operation
- **Reduced Timeout Issues**: Connection timeouts and delays should be resolved

### Technical Details
- Connection validation now only triggers on database-related errors (connection, database, no such column, table errors)
- Maintains all metadata refresh functionality while eliminating performance regression
- Error-triggered validation provides the same protection against stale metadata without the overhead
- Backwards compatible - no API changes

## [0.3.6] - 2025-07-07

### Fixed
- **CRITICAL HOTFIX**: Fixed `name 'text' is not defined` error in connection validation by adding missing SQLAlchemy import
- **CRITICAL HOTFIX**: Fixed `NoForeignKeysError` when determining join conditions for junction table relationships
- **Root Cause**: Aggressive metadata refresh logic was calling `SQLModel.metadata.clear()` which destroyed relationship mappings
- **Solution**: Implemented conservative metadata refresh approach that preserves relationship mappings while still handling stale metadata

### Changed
- **Conservative Metadata Refresh**: Updated `refresh_metadata()` to use temporary metadata objects instead of clearing existing mappings
- **Conservative Junction Table Handling**: Updated `refresh_junction_table_metadata()` to validate table accessibility without disrupting relationships
- **Preserved Relationship Mappings**: Metadata refresh no longer interferes with SQLAlchemy's ability to configure many-to-many relationships

### Technical Details
- Added missing `text` import from SQLAlchemy for connection validation queries
- Replaced destructive `SQLModel.metadata.clear()` with conservative reflection approach
- Junction table validation now uses simple accessibility tests rather than metadata replacement
- Connection validation maintains relationship integrity while ensuring metadata freshness
- Backwards compatible - existing code continues to work without changes

## [0.3.5] - 2025-07-07

### Fixed
- **CRITICAL**: Fixed intermittent SQLAlchemy errors where junction tables would fail with "no such column: tablename.columnname" after database session disconnects
- **Root Cause**: SQLAlchemy's metadata cache becomes stale after database disconnection/reconnection, causing the ORM to lose track of junction table column definitions even though the columns exist and have data
- **Solution**: Implemented comprehensive connection validation and metadata refresh mechanisms with table-agnostic error recovery

### Added
- **Connection Validation**: Added `validate_connection()` method to DatabaseConfig that validates connections before creating sessions
- **Metadata Refresh**: Added `refresh_metadata()` and `refresh_junction_table_metadata()` methods to handle stale metadata
- **Junction Table Recovery**: Added `_ensure_junction_table_metadata()` and `_safe_relationship_query()` methods for automatic error recovery
- **Enhanced Connection Pooling**: Improved connection pool settings with better ping and recycle configurations
- **Dynamic Table Name Extraction**: Error recovery now works with ANY junction table names using regex pattern matching

### Technical Details
- Enhanced `EasyModel.get_session()` to validate connection before creating each session
- Automatic detection and recovery from junction table metadata staleness
- Backwards compatible - no API changes required
- **Table-agnostic error recovery**: Works with any junction table names (brandusers, booktags, usercompanies, etc.)
- Dynamic table name extraction from SQLAlchemy error messages using regex
- Addresses intermittent nature of the error that occurs after session disconnects
- Intelligent retry mechanism: specific table refresh → full metadata refresh → graceful failure
- Comprehensive logging for debugging junction table metadata issues

## [0.3.4] - 2025-07-06

### Fixed
- **CRITICAL**: Fixed JSON serialization error "Object of type Column is not JSON serializable" when using `sa_column=Column(JSON)` in model fields
- **Root Cause**: Migration system was including entire SQLAlchemy Column objects in migration operations, which are not JSON serializable
- **Solution**: Created `_serialize_column()` helper function to convert Column objects to JSON-serializable dictionaries
- Models with `sa_column=Column(JSON)` now work without serialization errors during migrations
- Enhanced `_get_sqlite_type()` to handle both string and object types, plus added explicit JSON type support

### Technical Details
- Added `_serialize_column()` function that extracts essential column information (name, type, nullable, default, etc.)
- Updated `generate_migration_plan()` to use serialized column data instead of raw Column objects
- Modified `apply_migration()` to work with the new serialized column data structure
- Migration history records are now more readable and portable
- Full backward compatibility maintained while fixing the serialization issue
- Reduces memory usage in migration records by storing only essential column information

## [0.3.3] - 2025-07-05

### Fixed
- **Warning Suppression**: Fixed torch.distributed.reduce_op FutureWarning during database initialization
- **Root Cause**: Module discovery was iterating through ALL loaded modules (including torch, numpy, etc.) triggering third-party library warnings
- **Solution**: Added temporary warning suppression during model discovery phase using warnings.catch_warnings() context manager
- Eliminates FutureWarning and DeprecationWarning from third-party libraries during init_db()
- Maintains full model discovery functionality without intrusive blacklists
- Clean, maintainable approach that works with any future third-party libraries

### Technical Details
- Temporarily suppresses FutureWarning and DeprecationWarning during sys.modules iteration
- Uses warnings.catch_warnings() context manager for surgical warning suppression
- Only affects warning behavior during model discovery, not globally
- No hardcoded module lists to maintain - future-proof solution
- Preserves all existing functionality while eliminating noisy warnings

## [0.3.2] - 2025-07-05

### Fixed
- **CRITICAL**: Fixed intermittent SQLAlchemy error "no such column: [junction_table].[foreign_key_column]"
- **Root Cause**: Order-of-operations bug in `init_db` function where relationship processing occurred before table creation
- **Solution**: Moved relationship processing to occur after all tables are created, ensuring complete schema exists before relationships are established
- Eliminates race condition that could leave junction tables (like BrandUsers) with missing foreign key columns
- Maintains all automatic relationship mapping functionality without API changes
- Prevents inconsistent database state during initialization

### Technical Details
- Reordered operations in `init_db()` function: register models → run migrations → create tables → process relationships
- This ensures all tables exist with their complete schema before many-to-many relationships are processed
- The fix resolves intermittent failures in applications using junction tables for many-to-many relationships
- No breaking changes - all existing functionality preserved

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
