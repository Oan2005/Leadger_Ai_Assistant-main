from supabase import create_client,Client
from dotenv import load_dotenv
import os
# load .env keys
load_dotenv(dotenv_path=".env.test")

SUPABASE_URL = os.getenv("TEST_SUPABASE_URL")
SUPABASE_KEY = os.getenv("TEST_SUPABASE_KEY")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("TEST_SUPABASE_SERVICE_ROLE_KEY")

Supabase_client: Client = create_client(
    supabase_url=SUPABASE_URL,
    supabase_key=SUPABASE_KEY,
)

Supabase_admin: Client = create_client(
    supabase_url=SUPABASE_URL,
    supabase_key=SUPABASE_SERVICE_ROLE_KEY,
)
