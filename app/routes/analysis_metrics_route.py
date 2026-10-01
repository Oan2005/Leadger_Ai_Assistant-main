from fastapi import APIRouter
from app.database.crud.analysis_crud import get_company_analytics
from .route_services import Depends,HTTPException
from .route_services import require_hr,require_hr_admin
from ..auth.user_auth import require_hr_admin
from ..database.crud.dashboard_analysis_crud import get_dashboard_data
from ..database.crud.users_crud import get_user_by_id

analysis_chat_route :APIRouter =  APIRouter(tags=['analysis'])

@analysis_chat_route.get("/analysis")
async def get_analysis(current_user = Depends(require_hr_admin)):
    requested_user = get_user_by_id(current_user.id)
    if requested_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    company_id = requested_user["company_id"]
    return get_company_analytics(company_id)

@analysis_chat_route.get("/analysis_dashboard")
async def get_dashboard_anlysis(current_user = Depends(require_hr_admin)):
    requested_user = get_user_by_id(current_user.id)
    if requested_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    company_id = requested_user["company_id"]
    return get_dashboard_data(company_id)


