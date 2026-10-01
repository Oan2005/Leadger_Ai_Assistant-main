from typing import Literal
from .route_services import HTTPException,APIRouter
from .route_services import get_current_user,Depends

from .route_services import change_role
from .route_services import delete_user_by_id
from ..auth.user_auth import require_admin
from ..database.crud.company_crud import get_company_by_id
from ..database.crud.invitation_crud import check_invitation_accepted
from ..database.crud.users_crud import get_user_by_id, admin_update_employee, employee_update, check_user_exists, \
    get_users_by_company_id
from ..features.invitation.routes import create_invite_from_admin, validate_invitation
from ..models.pydantic_classes.users_pydantic import UpdateEmployeeByAdminRequest, \
    UpdateEmployeeByAdminResponse, SendInvitationToEmployee, UpdateEmployeeByEmployeeRequest
import logging
users_route = APIRouter(tags=['users'])
logger = logging.getLogger(__name__)
#test endpoint
@users_route.post('/company/users/me')
def active_user(current_user=Depends(get_current_user)):
    try:
        return get_user_by_id(current_user.id)

    except HTTPException:
        raise

    except Exception:
        logger.exception("Failed to retrieve active user")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )
#Later
@users_route.delete('/company/users/{user_id}')
def delete_user(
    user_id: str,
    current_user=Depends(require_admin)
):
    try:
        requested_info = get_user_by_id(current_user.id)
        if not requested_info:
            raise HTTPException(
                status_code=404,
                detail="User information not found"
            )

        check_user_valid = check_user_exists(
            user_id,
            company_id=requested_info["company_id"]
        )
        if not check_user_valid:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        return delete_user_by_id(
            user_id=user_id,
            company_id=requested_info["company_id"]
        )


    except HTTPException:
        raise

    except Exception:
        logger.exception("Error while deleting user")

        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred"
        )

#Works Good
@users_route.patch('/company/users/{user_id}/{role}')
async def update_role(
    user_id: str,
    role: Literal["admin", "hr", "employee"],
    current_user=Depends(require_admin)
):
    try:
        # returns True OR False
        check_user_valid = check_user_exists(user_id)
        if(
            not check_user_valid
        ):
            raise HTTPException(status_code=404,detail='User not found')
        requested_info = get_user_by_id(current_user.id)
        requested_company = requested_info["company_id"]
        response = change_role(user_id, company_id=requested_company, role=role)
        if response is False:
            raise HTTPException(status_code=403,detail='Failed to Update the User Role')
        return {"message":"User Role Updated Successfully"}
    except HTTPException:
        raise
#Done
@users_route.post("/company/users/invite_user")
async def invite_user(
    data:SendInvitationToEmployee,
    current_user=Depends(require_admin)
):
    try:
        email = data.email
        # Check if an active invitation already exists
        if check_invitation_accepted(email):
            raise HTTPException(
                status_code=409,
                detail="An active invitation already exists for this email nor Didnt accpeted."
            )

        # Get current user's information
        requested_information = get_user_by_id(current_user.id)

        if not requested_information or requested_information is None:
            raise HTTPException(
                status_code=404,
                detail="User information not found."
            )

        company_id = requested_information["company_id"]

        # Get company information
        requested_company = get_company_by_id(company_id)

        if not requested_company or requested_company.get("success") is not True:
            raise HTTPException(
                status_code=404,
                detail="Company not found."
            )

        company_name = requested_company["company_name"]

        # Create invitation
        invite_request = create_invite_from_admin(
            email,
            data.role,
            data.phone,
            company_name=company_name,
            company_id=company_id,
            admin_id=requested_information["user_id"],
        )

        return invite_request

    except HTTPException:
        raise

    except Exception:
        logger.exception("Invitation error")

        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while creating the invitation."
        )



#Works Good
@users_route.patch("/admin/employee/{employee_id}")
async def update_employee_by_admin(
    employee_id: str,
    data: UpdateEmployeeByAdminRequest,
    current_user=Depends(require_admin)
):

    check_user = check_user_exists(employee_id)
    if not check_user:
        raise HTTPException(status_code=404,detail='Employee not found')
    requested_info = get_user_by_id(current_user.id)
    company_id = requested_info["company_id"]

    request = admin_update_employee(
        company_id=company_id,
        user_id=employee_id,
        full_name=data.full_name,
        phone=data.phone,
        role=data.role,
    )

    if not request["success"]:
        raise HTTPException(status_code=404, detail=request["error"])

    return {
        "full_name":data.full_name,
        "phone":data.phone,
        "role":data.role,
    }
#Works Good
@users_route.patch("/employee/{employee_id}")
async def update_employee_by_employee(
    data:UpdateEmployeeByEmployeeRequest,
    current_user=Depends(get_current_user)
):
    try:
        requested_info = get_user_by_id(current_user.id)

        if not requested_info or requested_info is None:
            raise HTTPException(
                status_code=404,
                detail="Employee not found."
            )

        user_id = requested_info["user_id"]
        company_id = requested_info["company_id"]
        user_name = requested_info["full_name"]

        request = employee_update(
            full_name=data.full_name,
            phone=data.phone,
            company_id=company_id,
            user_id=user_id
        )

        if request.get("success") is True:
            return {
                "success": True,
                "message": f"{user_name} updated successfully."
            }

        raise HTTPException(
            status_code=404,
            detail=request.get("error", "Employee could not be updated.")
        )

    except HTTPException:
        raise

    except Exception:
        logger.exception("Employee update error")

        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while updating the employee."
        )

