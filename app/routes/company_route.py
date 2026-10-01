from .route_services import HTTPException,APIRouter
from .route_services import Depends
from .route_services import delete_company,get_users_by_company_id
from ..auth.user_auth import require_admin
from ..database.crud.company_crud import get_namespace_by_company_id, update_company_name, check_company_existence
from ..database.crud.users_crud import get_user_by_id
import logging

company_route = APIRouter(tags=['company'])
logger = logging.getLogger(__name__)


#DONE
@company_route.delete("/delete_company")
async def delete_all_company(current_user = Depends(require_admin)):
    try:
        user_information = get_user_by_id(current_user.id)
        if (
            not user_information or  user_information is None
        ):
            raise HTTPException(status_code=404, detail="User not found")
        user_company_id = user_information["company_id"]
        user_id = user_information["user_id"]
        user_name = user_information["full_name"]


        request = delete_company(user_company_id)
        if not request["success"]:
            raise HTTPException(status_code=404, detail=request["message"])
        return {"message":"{} deleted all company records".format(user_name)}
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to delete company")
        raise HTTPException(status_code=500, detail="Unable to delete company.")

@company_route.get("/company/users")
async def get_company_users(current_user = Depends(require_admin)):
    requested_person = get_user_by_id(current_user.id)

    if requested_person is None:
        raise HTTPException(status_code=404, detail="User not found")
    user_company_id = requested_person["company_id"]

    users = get_users_by_company_id(user_company_id)
    if users is False:
        raise HTTPException(status_code=404, detail="No users exists in the Company")
    return users


#DONE
@company_route.get("/company/company_id")
async def get_namespace(current_user = Depends(require_admin)):
    try:
        requested_person = get_user_by_id(current_user.id)
        if requested_person is None:
            raise HTTPException(status_code=404, detail="User not found")

        user_company_id = requested_person["company_id"]
        if check_company_existence(user_company_id) is False:
            raise HTTPException(status_code=404, detail="Company does not exist")

        company_namespace = get_namespace_by_company_id(user_company_id)
        if company_namespace is False:
            raise HTTPException(status_code=404, detail="Company namespace doesnt exists")
        return company_namespace["namespace"]
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to retrieve company namespace")
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve company namespace."
        )

#DONE
@company_route.patch("/company/company_id/{new_name}")
async def change_company_name(new_name:str,current_user = Depends(require_admin)):
    requested_person = get_user_by_id(current_user.id)
    if requested_person is None:
        raise HTTPException(status_code=404, detail="User not found")
    if check_company_existence(requested_person["company_id"]) is False:
        raise HTTPException(status_code=404, detail="Company does not exist")
    requested_company = requested_person["company_id"]
    update_request = update_company_name(requested_company,new_name)
    if update_request is False:
        raise HTTPException(status_code=409, detail="Company name already exists")
    return update_request

