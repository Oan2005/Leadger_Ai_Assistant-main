import os
import resend
from dotenv import load_dotenv
from datetime import datetime,timezone,timedelta
import secrets,hashlib
from fastapi import HTTPException
from app.supabase_client_package.supabase_connection import Supabase_admin


