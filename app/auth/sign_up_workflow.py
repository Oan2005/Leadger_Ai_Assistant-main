from app.supabase_client_package.supabase_connection import Supabase_client, Supabase_admin
from .auth_exceptions import *

def sign_up(company_name, full_name, email, password, namespace, phone):

    user_id = None
    company_id = None

    try:

        # 1. Create Supabase Auth user
        sign_up_request = Supabase_client.auth.sign_up({
            "email": email,
            "password": password,
        })

        if not sign_up_request.user:
            raise SignupError(
                "Unable to create authentication account."
            )

        user_id = sign_up_request.user.id

        # 2. Create company
        company_creation = (
            Supabase_admin
            .table("companies")
            .insert({
                "company_name": company_name,
                "namespace": namespace,
            })
            .execute()
        )

        if not company_creation.data:
            raise SignupError(
                "Unable to create company."
            )

        company_id = company_creation.data[0]["company_id"]

        # 3. Create application user
        user_creation = (
            Supabase_admin
            .table("users")
            .insert({
                "user_id": user_id,
                "company_id": company_id,
                "full_name": full_name,
                "email": email,
                "role": "admin",
                "phone": phone,
            })
            .execute()
        )

        if not user_creation.data:
            raise SignupError(
                "Unable to create application user."
            )

        # 4. Successful signup
        return {
            "success": True,
            "data": {
                "user_id": user_id,
                "email": email,
                "full_name": full_name,
                "company_id": company_id,
                "role": "admin"
            }
        }

    except SignupError:
        raise

    except Exception as e:

        print(f"Company signup error: {e}")

        # Rollback application data
        if company_id:
            try:
                (
                    Supabase_admin
                    .table("companies")
                    .delete()
                    .eq("company_id", company_id)
                    .execute()
                )
            except Exception as rollback_error:
                print(
                    f"Company rollback failed: {rollback_error}"
                )

        # Rollback Auth user
        if user_id:
            try:
                Supabase_admin.auth.admin.delete_user(user_id)
            except Exception as rollback_error:
                print(
                    f"Auth user rollback failed: {rollback_error}"
                )

        raise SignupError(
            "Unable to complete company registration."
        ) from e