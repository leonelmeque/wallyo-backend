# Architecture Specification - Wallyo Server

## Architecture Pattern: Feature-Based Architecture

This project uses a **Feature-Based Architecture** to organize code by business domains/features. This approach provides clear separation of concerns, makes it easy to locate related code, and scales well as the application grows.

## Project Structure

```
wallyo-server/
├── main.py                 # FastAPI application entry point
├── app/
│   ├── __init__.py
│   ├── core/               # Shared/core functionality
│   │   ├── __init__.py
│   │   ├── config.py      # Application configuration
│   │   └── supabase.py    # Supabase client initialization
│   └── features/           # Feature modules
│       ├── __init__.py
│       └── {feature_name}/ # Each feature is a self-contained module
│           ├── __init__.py
│           ├── routes.py   # API endpoints/routes
│           ├── service.py  # Business logic layer
│           ├── repository.py # Data access layer
│           └── schemas.py  # Pydantic models/schemas
├── requirements.txt
├── .env                    # Environment variables (not in git)
└── README.md
```

## Feature Structure

Each feature module should follow this structure:

### 1. **schemas.py** - Data Models
- Define Pydantic models for request/response validation
- Use `BaseModel` for data structures
- Include validation rules and type hints
- Example: `CloudBackupCreate`, `CloudBackupResponse`

### 2. **repository.py** - Data Access Layer
- Handle all database operations (Supabase)
- Abstract database implementation details
- Methods should be async where possible
- Return dictionaries or domain objects
- Example: `CloudBackupRepository`

### 3. **service.py** - Business Logic Layer
- Contains business logic and use cases
- Orchestrates repository calls
- Handles validation and error handling
- Should not contain HTTP-specific code
- Example: `CloudBackupService`

### 4. **routes.py** - API Layer
- Define FastAPI routes/endpoints
- Handle HTTP requests and responses
- Use dependency injection for services
- Convert between HTTP and domain models
- Example: `router = APIRouter(prefix="/api/v1/feature-name")`

## Core Principles

### 1. **Separation of Concerns**
- Routes handle HTTP concerns
- Services contain business logic
- Repositories handle data access
- Schemas define data structures

### 2. **Dependency Flow**
```
Routes → Services → Repositories → Supabase
```

### 3. **Feature Independence**
- Each feature should be as independent as possible
- Shared code goes in `app/core/`
- Avoid cross-feature dependencies when possible

### 4. **Naming Conventions**
- Feature folders: `snake_case` (e.g., `cloud_backup`)
- Files: `snake_case.py`
- Classes: `PascalCase` (e.g., `CloudBackupService`)
- Functions/methods: `snake_case`
- Routes prefix: `/api/v1/{feature-name}` (kebab-case)

## Adding a New Feature

1. Create feature directory: `app/features/{feature_name}/`
2. Create `__init__.py` file
3. Create the four core files:
   - `schemas.py` - Define data models
   - `repository.py` - Data access layer
   - `service.py` - Business logic
   - `routes.py` - API endpoints
4. Register router in `main.py`:
   ```python
   from app.features.{feature_name}.routes import router as {feature}_router
   app.include_router({feature}_router)
   ```

## Core Module

The `app/core/` directory contains shared functionality:

- **config.py**: Application settings and environment variables
- **supabase.py**: Supabase client initialization and utilities

## API Versioning

- Use `/api/v1/` prefix for all routes
- Future versions will use `/api/v2/`, etc.
- Version in the route prefix, not the feature name

## Error Handling

- Use FastAPI's `HTTPException` in routes
- Services should raise domain-specific exceptions
- Repositories should handle database errors gracefully

## Type Hints

- Use type hints throughout the codebase
- Leverage Pydantic for runtime validation
- Use `Optional` for nullable values
- Use `List`, `Dict` from `typing` module

## Async/Await

- Prefer async functions for I/O operations
- Use `async def` for route handlers
- Use `await` for database operations

## Example Feature: cloud_backup

```
app/features/cloud_backup/
├── __init__.py
├── schemas.py          # CloudBackupCreate, CloudBackupResponse
├── repository.py       # CloudBackupRepository
├── service.py          # CloudBackupService
└── routes.py           # POST /api/v1/cloud-backup/
```

## Database

- Supabase is used as the database/backend
- Each feature typically has its own table(s)
- Table names should be plural and snake_case (e.g., `cloud_backups`)
- Use the Supabase client from `app.core.supabase`

## Environment Variables

- All configuration via `.env` file
- Load using `python-dotenv` in `app/core/config.py`
- Access via `settings` object from `app.core.config`

## Testing Structure (Future)

When adding tests, mirror the feature structure:
```
tests/
├── features/
│   └── {feature_name}/
│       ├── test_routes.py
│       ├── test_service.py
│       └── test_repository.py
```

## Best Practices

1. **Keep features focused**: Each feature should have a single responsibility
2. **Reuse core utilities**: Don't duplicate code in features
3. **Consistent naming**: Follow the naming conventions above
4. **Type safety**: Use type hints and Pydantic models
5. **Error handling**: Handle errors at the appropriate layer
6. **Documentation**: Add docstrings to classes and functions
7. **API documentation**: FastAPI auto-generates docs at `/docs`

---

**Last Updated**: 2024
**Architecture**: Feature-Based Architecture
**Framework**: FastAPI
**Database**: Supabase

