# Wallyo Server

A FastAPI server that provides presigned upload/download URLs for encrypted SQLite backups stored in Supabase Storage.

## Features

- JWT-based authentication using Supabase Auth
- Presigned upload URLs for encrypted backup files and manifests
- Presigned download URLs for secure file access
- Path validation to ensure users can only access their own backups

## Setup

1. Create a virtual environment:
```bash
python3 -m venv venv
```

2. Activate the virtual environment:
```bash
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the root directory:
```bash
# .env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_BACKUP_BUCKET=user-backups
PORT=8787
```

**Important**: 
- Never expose `SUPABASE_SERVICE_ROLE_KEY` to clients or front-end applications. This key should only be used server-side.
- `SUPABASE_ANON_KEY` is required for storage operations with Row Level Security (RLS). You can find both keys in Supabase Dashboard > API Settings.

5. **Set up Storage RLS Policies**:
   
   Storage operations require Row Level Security (RLS) policies to be created in Supabase. Run the SQL from `supabase_storage_rls_policies.sql` in your Supabase Dashboard > SQL Editor.
   
   This allows authenticated users to:
   - Upload files to the `user-backups` bucket
   - Read, update, and delete their own files (organized by user ID in the path)

6. Run the server:
```bash
uvicorn main:app --reload --port 8787
```

The server will be available at `http://localhost:8787`

## Environment Variables

- `SUPABASE_URL` (required): Your Supabase project URL (found in Project Settings > API)
- `SUPABASE_SERVICE_ROLE_KEY` (required): Your Supabase service role key (found in Project Settings > API)
- `BUCKET` (optional): Storage bucket name (defaults to "user-backups")
- `PORT` (optional): Server port (defaults to 8000 if not set)
- `LOG_LEVEL` (optional): Logging level - DEBUG, INFO, WARNING, ERROR, CRITICAL (defaults to "INFO")
- `LOG_FILE` (optional): Path to log file. If not set, logs only to console

## API Endpoints

### Health Check
- `GET /` - Returns server status

### Storage Endpoints

#### Presign Upload
- `POST /v1/storage/presign-upload` - Generate presigned upload URLs for backup file and manifest

  **Request:**
  ```json
  {
    "filename": "wallyo.db.enc"
  }
  ```

  **Response:**
  ```json
  {
    "path": "backups/<userId>/<timestamp>-<random>.db.enc",
    "token": "<signed-upload-token>",
    "latest_path": "backups/<userId>/latest.json",
    "latest_token": "<signed-upload-token>"
  }
  ```

#### Presign Download
- `POST /v1/storage/presign-download` - Generate presigned download URL for a storage object

  **Request:**
  ```json
  {
    "path": "backups/<userId>/latest.json",
    "seconds": 900
  }
  ```

  **Response:**
  ```json
  {
    "url": "https://signed-download-url"
  }
  ```

## Authentication

All storage endpoints require a valid Supabase JWT token in the Authorization header:

```
Authorization: Bearer <supabase-jwt-token>
```

The JWT is validated using Supabase Auth, and the user ID is extracted to ensure users can only access their own backups.

## API Documentation

Once the server is running, interactive API documentation is available at:
- Swagger UI: `http://localhost:8787/docs`
- ReDoc: `http://localhost:8787/redoc`

## Logging

The application uses Python's built-in `logging` module configured in `app/core/logger.py`. 

### Usage

Import and use the logger in any module:

```python
from app.core.logger import logger

logger.info("This is an info message")
logger.debug("Debug information")
logger.warning("This is a warning")
logger.error("An error occurred")
logger.critical("Critical error!")
```

### Configuration

- Set `LOG_LEVEL` in your `.env` file to control log verbosity
- Set `LOG_FILE` in your `.env` file to write logs to a file
- Logs are formatted with timestamp, logger name, level, and message

## Architecture

This project follows a Feature-Based Architecture pattern. See `style-guide/architecture.md` for details.

## Testing

Run tests with:
```bash
pytest
```

