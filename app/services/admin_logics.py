from app.supabase_client_package.supabase_connection import Supabase_client, Supabase_admin
import logging

logger = logging.getLogger(__name__)



def can_upload(access_token):
    try:
        response = Supabase_client.auth.get_user(access_token)

        user_id = response.user.id

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
        logger.exception("Failed to check upload permission")
        return {"error": "Unable to check upload permission."}


