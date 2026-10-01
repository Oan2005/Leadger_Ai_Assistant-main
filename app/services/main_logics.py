from app.supabase_client_package.supabase_connection import Supabase_client, Supabase_admin
import logging

logger = logging.getLogger(__name__)

def get_user_role(user_id):
    try:
        user_information = (
            Supabase_client
            .table("users")
            .select("role")
            .eq("user_id", user_id)
            .single()
            .execute()
        )

        role = user_information.data["role"]
        return role
    except Exception:
        logger.exception("Failed to retrieve user role")
        return {"error": "Unable to retrieve user role."}