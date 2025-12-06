from fastapi import FastAPI
from dotenv import load_dotenv
from supabase import create_client, Client
import os

# Load environment variables from .env file
load_dotenv()

app = FastAPI()

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

if supabase_url and supabase_key:
    supabase: Client = create_client(supabase_url, supabase_key)
else:
    supabase = None


@app.get("/")
async def hello_world() -> dict[str, str]:
    return {"message": "Hello World"}
