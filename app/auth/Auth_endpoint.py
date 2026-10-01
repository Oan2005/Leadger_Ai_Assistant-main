from fastapi import APIRouter,Depends,HTTPException
from app.features.invitation.routes import create_invite_from_admin, validate_invitation
from app.auth.user_auth import require_admin
from app.auth.sign_in_workflow import sign_in
from app.database.crud.company_crud import create_app, get_company_by_id, delete_company
from app.database.crud.users_crud import get_user_by_id, create_invited_user, users
from app.models.pydantic_classes.users_pydantic import RefreshTokenRequest
from app.supabase_client_package.supabase_connection import Supabase_client,Supabase_admin
from app.auth.user_auth import get_current_user
from app.RAG.vector_database.pinecone_client import create_namespace
import hashlib
import logging
from app.database.crud.company_crud import Company
from app.models.pydantic_classes.auth_pydantic import *
from datetime import datetime, timezone
from app.database.crud.invitation_crud import get_invitation, check_invitation_accepted, mark_as_accepted
from app.auth.auth_exceptions import (
InvalidCredentialsError
)

logger = logging.getLogger(__name__)
auth_router: APIRouter = APIRouter(tags=["auth"])
@auth_router.post(
    "/signup/invited",
    response_model=InvitedSignupResponse
)
async def sign_up_invited(data: InvitedSignupRequest):
    try:
        hashed_token = hashlib.sha256(
            data.token.encode()
        ).hexdigest()

        # 1. Get invitation
        invitation_response = get_invitation(
            token_hash=hashed_token
        )

        invitation = invitation_response

        if invitation is None:
            raise HTTPException(
                status_code=400,
                detail="Invalid invitation."
            )

        # 2. Check whether invitation was already used
        if invitation["accepted_at"] is not None:
            raise HTTPException(
                status_code=400,
                detail="Invitation already used."
            )

        # 3. Check expiration
        if invitation["expires_at"] <= datetime.now(timezone.utc):
            raise HTTPException(
                status_code=400,
                detail="Invitation has expired."
            )

        # 4. Email comes ONLY from invitation
        email = invitation["email"]

        # 5. Create Supabase Auth account
        response = Supabase_admin.auth.admin.create_user({
            "email": email,
            "password": data.password,
            "email_confirm": True
        })
        if not response.user.id:
            raise HTTPException(status_code=400, detail="failed to create auth table for user")


        user_id = response.user.id

        # 6. Create application user
        user_creation = create_invited_user(
            user_id=user_id,
            company_id=invitation["company_id"],
            full_name=data.full_name,
            email=email,
            role=invitation["role"],
            phone=invitation["phone"],
        )

        if not user_creation:
            Supabase_admin.auth.admin.delete_user(user_id)
            raise HTTPException(
                status_code=400,
                detail="Error during creating user record."
            )

        request_to_mark = mark_as_accepted(token_hash=hashed_token)
        if not request_to_mark:
            Supabase_admin.auth.admin.delete_user(user_id)
            raise HTTPException(status_code=400,detail="failed to mark the invtiation as accepted")

        return {
            "full_name": data.full_name,
            "email": email,
            "message": "Account created successfully."
        }

    except HTTPException:
        raise

    except Exception as e:
        logger.exception("Invited signup failed")
        #Supabase_admin.auth.admin.delete_user(user_id)
        raise HTTPException(
            status_code=500,
            detail="Unable to complete account registration."
        )
@auth_router.post(
    "/signin",
    response_model=SignInResponse
)
def login(data: SignInRequest):
    try:

        # 1. Authenticate with Supabase
        auth_response = sign_in(data=data)

        # 2. Get SkyJet application user
        user_info = get_user_by_id(
            auth_response["user_id"]
        )

        # Auth account exists, but application account doesn't
        if not user_info:
            logger.error("Auth user has no application user record")

            raise HTTPException(
                status_code=403,
                detail="User Account Is Not Available."
            )

        # 3. Return clean response
        return {
            "success": True,
            "message": f"Welcome {user_info['full_name']}",
            "user_id": auth_response["user_id"],
            "access_token": auth_response["access_token"],
            "refresh_token": auth_response["refresh_token"]
        }

    except InvalidCredentialsError:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password."
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.exception("Signin failed")

        raise HTTPException(
            status_code=500,
            detail="Unable to complete sign in."
        )

@auth_router.post("/signup", response_model=SignUpResponse)
def sign_up(data: SignUpRequest):

    user_id = None
    company_id = None
    namespace_created = False

    try:
        # =========================================================
        # 1. Create Supabase Auth user
        # =========================================================
        sign_up_request = Supabase_client.auth.sign_up({
            "email": data.email,
            "password": data.password,
        })

        if not sign_up_request.user:
            raise HTTPException(
                status_code=400,
                detail="Unable to create authenticated account."
            )

        user_id = sign_up_request.user.id

        logger.info(
            "Supabase Auth user created: %s",
            user_id
        )

        # =========================================================
        # 2. Create company + first admin
        # =========================================================
        app_creation = create_app(
            company_data=Company(
                company_name=data.company_name,
                namespace=data.namespace
            ),
            full_name=data.full_name,
            email=data.email,
            phone=data.phone,
            user_supabase_id=user_id
        )

        company_id = app_creation["company_id"]

        logger.info(
            "Company created: %s",
            company_id
        )

        # =========================================================
        # 3. Create Pinecone namespace
        # =========================================================
        company_namespace = create_namespace(data.namespace)

        if not company_namespace :
            raise HTTPException(
                status_code=409,
                detail="Namespace already exists. Choose another one."
            )

        namespace_created = True

        logger.info(
            "Pinecone namespace created: %s",
            data.namespace
        )

        # =========================================================
        # 4. Success
        # =========================================================
        return {
            "success": True,
            "data": {
                "user_id": user_id,
                "email": data.email,
                "full_name": data.full_name,
                "company_id": company_id,
                "role": "admin",
                "namespace": data.namespace
            }
        }

    except HTTPException:
        # ---------------------------------------------------------
        # Rollback expected errors
        # ---------------------------------------------------------

        if company_id:
            try:
                delete_company(company_id)
            except Exception:
                logger.exception(
                    "Failed to rollback company: %s",
                    company_id
                )

        if user_id:
            try:
                Supabase_admin.auth.admin.delete_user(user_id)
            except Exception:
                logger.exception(
                    "Failed to rollback Auth user: %s",
                    user_id
                )

        raise

    except Exception:
        # ---------------------------------------------------------
        # Rollback unexpected errors
        # ---------------------------------------------------------

        logger.exception(
            "Unexpected signup failure. user_id=%s company_id=%s namespace=%s",
            user_id,
            company_id,
            data.namespace
        )

        if company_id:
            try:
                delete_company(company_id)
            except Exception:
                logger.exception(
                    "Failed to rollback company: %s",
                    company_id
                )

        if user_id:
            try:
                Supabase_admin.auth.admin.delete_user(user_id)
            except Exception:
                logger.exception(
                    "Failed to rollback Auth user: %s",
                    user_id
                )

        raise HTTPException(
            status_code=500,
            detail="Unable to complete signup."
        )

@auth_router.post("/logout")
async def sign_out(
    current_user=Depends(get_current_user)
):
    try:

        Supabase_client.auth.sign_out()

        return {
            "success": True,
            "message": "Logged out successfully."
        }

    except Exception as e:

        logger.exception("Logout failed")

        raise HTTPException(
            status_code=500,
            detail="Unable to log out."
        )


@auth_router.post("/refresh_token")
async def refresh_token(data: RefreshTokenRequest):
    refresh_token = data.refresh_token
    try:
        response = Supabase_client.auth.refresh_session(
            refresh_token=refresh_token
        )

        return {
            "success": True,
            "access_token": response.session.access_token,
            "refresh_token": response.session.refresh_token
        }

    except Exception as e:

        logger.exception("Refresh token refresh failed")

        raise HTTPException(
            status_code=401,
            detail="Invalid or expired refresh token."
        )

@auth_router.get("/test-current-user")
async def test_current_user(
    current_user=Depends(require_admin)
):
    user_information = get_user_by_id(current_user.id)
    return {
        "current_user": user_information
    }



@auth_router.post("/admin/invite",response_model=SignUpInvitationResponse)
async def create_invitation(
    data:SignUpInvitationRequest,
    current_user=Depends(require_admin)
):
    try:
        email = data.email
        role = data.role
        phone = data.phone


        requested_info = get_user_by_id(current_user.id)
        if requested_info is None:
            raise HTTPException(status_code=404,detail="User not found.")
        company_name = get_company_by_id(requested_info["company_id"])
        if company_name is None:
            raise HTTPException(status_code=404,detail="Company not found.")
        company_name = company_name["company_name"]

        check_email_invited = check_invitation_accepted(email=email)
        if check_email_invited == True:
            raise HTTPException(detail="Email exists and invitation was accepted",status_code=400)
        elif check_email_invited == False:
            raise HTTPException(detail="Email exists and invitation was not accepted",status_code=400)

        response= create_invite_from_admin(
            email,role,phone,company_name=company_name,
            company_id=requested_info["company_id"],
            admin_id=requested_info["user_id"]
        )

        return {
                "success":True,
                "data":{
                    "email":email,
                    "role":role,
                }
            }
    except HTTPException:
        raise

    except Exception:
        logger.exception("Invitation endpoint failed")
        raise HTTPException(
            status_code=500,
            detail="Unable to create invitation."
        )


@auth_router.get("/company/invite/validate")
async def validate_invite(token:str):
    return await validate_invitation(token)