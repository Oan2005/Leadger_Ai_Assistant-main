from .services import (load_dotenv,os,resend,datetime,
                       timezone,timedelta,secrets,hashlib,Supabase_admin,HTTPException)
from ...database.crud.invitation_crud import create_invitation

load_dotenv()


resend.api_key = os.getenv("RESEND_API_KEY")


def send_invitation_email(
    recipient_email,
    company_name,
    role,
    invitation_token
):
    resend.Emails.send({
        "from": "onboarding@resend.dev",
        "to": recipient_email,
        "subject": f"Invitation to {company_name}",
        "html": f"""
            <h2>You're invited!</h2>

            <p>You have been invited to join
            <strong>{company_name}</strong>.</p>

            <p>Role: <strong>{role}</strong></p>

            <p>Your invitation url:</p>

            <a href="https://numeric-oven-suitcase.ngrok-free.dev/company/invite/validate?token={invitation_token}">
    Accept Invitation
</a>
        """
    })


def create_invite_from_admin(email:str,role:str,phone:str,company_name:str,company_id:str,admin_id:str):
    try:
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=24)

        hashed_token = hashlib.sha256(
            token.encode()
        ).hexdigest()

        # Store invitation
        # result =  Supabase_admin.table("invitations").insert({
        #     "email": email,
        #     "company_id": "ca1550f0-c096-46eb-a174-88a7e6c8ae61",
        #     "role": role,
        #     "token_hash": hashed_token,
        #     "created_by": "3800bca6-3868-42e2-a024-2e2dfb9186b7",
        #     "phone":phone,
        #     "expires_at": expires_at.isoformat(),
        # }).execute()
        result = create_invitation(
            email = email,
            company_id=company_id,
            role=role,
            token_hash=hashed_token,
            admin_id=admin_id,
            phone=phone,
        )
        if result is None:
            raise HTTPException(detail="error during creating invitation", status_code=500)

        # Send email
        send_invitation_email(
            email,
            company_name=company_name,
            role=role,
            invitation_token=token
        )

        return True

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


async def validate_invitation(token: str):

    hashed_token = hashlib.sha256(
        token.encode()
    ).hexdigest()

    # Find invitation
    result =  Supabase_admin.table("invitations") \
        .select("*") \
        .eq("token_hash", hashed_token) \
        .execute()

    if not result.data:
        raise HTTPException(
            status_code=400,
            detail="Invalid invitation token"
        )

    invitation = result.data[0]

    # Already used
    if invitation["accepted_at"] is not None:
        raise HTTPException(
            status_code=400,
            detail="Invitation has already been used"
        )

    # Expiration
    expires_at = datetime.fromisoformat(
        invitation["expires_at"].replace("Z", "+00:00")
    )

    if datetime.now(timezone.utc) > expires_at:
        raise HTTPException(
            status_code=400,
            detail="Invitation has expired"
        )


    return {
        "valid": True,
        "email": invitation["email"],
        "role": invitation["role"],
        "company_id": invitation["company_id"],
    }


