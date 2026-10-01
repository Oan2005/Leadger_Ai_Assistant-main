import psycopg2
from dotenv import load_dotenv
import os,logging

# Load environment variables from .env
load_dotenv()
logger = logging.getLogger(__name__)

# Fetch variables
DATABASE_URL = os.getenv("TEST_DATABASE_URL")
# Connect to the database
def connect_to_database():
    """Get a database connection with proper error handling."""
    try:
        if not DATABASE_URL:
            raise ValueError("DATABASE_URL environment variable is not set")

        connection = psycopg2.connect(DATABASE_URL)
        return connection

    except psycopg2.Error as e:
        logger.error(f"Database connection failed: {e}")
        raise Exception("Unable to connect to database. Please check DATABASE_URL configuration.")
    except Exception as e:
        logger.error(f"Unexpected database error: {e}")
        raise



