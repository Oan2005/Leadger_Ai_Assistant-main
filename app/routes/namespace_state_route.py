from fastapi import FastAPI, APIRouter, Depends, HTTPException
from .route_services import require_hr_admin
from ..database.crud.company_crud import get_namespace_index_stats
from ..database.crud.users_crud import get_user_by_id

namespace_route = APIRouter(tags=["namespace"])


@namespace_route.get("/namespace/stats/")
async def get_namespace_stats(current_user=Depends(require_hr_admin)):
    requested_person = get_user_by_id(current_user.id)
    if requested_person is None:
        raise HTTPException(status_code=404, detail="User Not Found")
    company_id = requested_person["company_id"]
    return get_namespace_index_stats(company_id=company_id)
