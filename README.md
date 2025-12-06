# Wallyo Server

A simple FastAPI server that returns "Hello World".

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
SUPABASE_URL=your-supabase-project-url
SUPABASE_KEY=your-supabase-anon-key
```

5. Run the server:
```bash
uvicorn main:app --reload
```

The server will be available at `http://localhost:8000`

## Endpoints

- `GET /` - Returns "Hello World"

## Supabase Setup

The Supabase client is initialized in `main.py` and will be available as the `supabase` variable. Make sure to add your Supabase credentials to the `.env` file:

- `SUPABASE_URL`: Your Supabase project URL (found in Project Settings > API)
- `SUPABASE_KEY`: Your Supabase anon/public key (found in Project Settings > API)

## Accessing Environment Variables

You can access environment variables in your code using:
```python
import os
value = os.getenv("VARIABLE_NAME")
```

