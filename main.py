from fastapi import FastAPI
from app.auth.Auth_endpoint import auth_router
from app.routes.employee_assistant_route import employee_router
from app.routes.namespace_state_route import namespace_route
from app.routes.users_route import users_route
from app.routes.company_route import company_route
from app.routes.Admin_document_operations import admin_router
from app.routes.analysis_metrics_route import analysis_chat_route


app = FastAPI()

app.include_router(analysis_chat_route)
# auth endpoints



#Endpoint belong to the Admin to Alter Documents from uploading till deleting
app.include_router(admin_router) #DONE

#Endpoint belong to all companies that support login,signup etc..
app.include_router(auth_router) # DONE

#Endpoint enables Admins,Employee to change data such as (Name,Role,Phone) weather it belong to admin or employee him self
app.include_router(users_route) #DONE

#Endpoint for every company to access their AI assistant
app.include_router(employee_router) # DONE

#Endpoint belong to companies to access their company namspace,change company name,delete the company
app.include_router(company_route)

app.include_router(namespace_route)




# backend status
@app.get("/")
def health():
    """
    Basic health check endpoint.

    Returns:
        dict: `{"status": "healthy"}` on success, or
        `{"message": <error string>}` if an exception occurs.
    """
    try:
        return {
            "status": "healthy"
        }
    except Exception as e:
        return {"message": str(e)}





