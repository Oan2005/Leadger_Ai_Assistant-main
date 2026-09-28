from http.client import HTTPException
from app.database.crud.users_crud import get_user_by_id
from app.supabase_client_package.supabase_connection import Supabase_client, Supabase_admin
from .auth_exceptions import InvalidCredentialsError
from app.supabase_client_package.supabase_connection import Supabase_client
from app.auth.auth_exceptions import InvalidCredentialsError
from pydantic import BaseModel,EmailStr
class SignInRequest(BaseModel):
    email:EmailStr
    password:str


def sign_in(data: SignInRequest):
    try:
        response = Supabase_client.auth.sign_in_with_password({
            "email": data.email,
            "password": data.password
        })

        if not response.session or not response.user:
            raise InvalidCredentialsError(
                "Authentication was unsuccessful."
            )

        return {
            "user_id": response.user.id,
            "email": response.user.email,
            "access_token": response.session.access_token,
            "refresh_token": response.session.refresh_token
        }

    except InvalidCredentialsError:
        raise

    except Exception as e:
        print(f"Sign in workflow error: {e}")
        raise









