# Leadger Assistant API

The FastAPI application is defined in `main.py` and exposes the routes below.
Protected routes require a Supabase access token in the `Authorization: Bearer
<token>` header.

## Public authentication routes

- `POST /signup` - Create a company and its first administrator.
- `POST /signup/invited` - Create an application user from an unused invitation.
- `POST /signin` - Authenticate with Supabase.
- `POST /refresh_token` - Refresh a Supabase session.
- `GET /company/invite/validate?token=...` - Validate an invitation token.
- `GET /` - Basic health response.

## Authenticated routes

- `POST /logout` - Sign out the current user.
- `POST /company/users/me` - Return the current application user.
- `POST /employee/question` - Answer an employee question using the company's
  Pinecone namespace and the LLM service.

## Administrator routes

- `POST /admin/invite` - Create and send an invitation.
- `POST /upload` - Process and store a supported HR document.
- `POST /archive/{document_id}` - Archive a document.
- `POST /unarchive/{document_id}` - Restore an archived document.
- `POST /delete/{document_id}` - Mark a document deleted and remove its vectors.
- `DELETE /company/users/{user_id}` - Delete a user in the administrator's company.
- `PATCH /company/users/{user_id}/{role}` - Change a same-company user's role.
- `POST /company/users/invite_user` - Create an employee invitation.
- `PATCH /admin/employee/{employee_id}` - Update an employee.
- `DELETE /delete_company` - Delete the current administrator's company.
- `GET /company/users` - List users in the administrator's company.
- `GET /company/company_id` - Return the company's Pinecone namespace.
- `PATCH /company/company_id/{new_name}` - Rename the company.
- `GET /test-current-user` - Return the current application user.

## HR and administrator routes

- `GET /analysis` - Return company analytics.
- `POST /analysis_dashboard` - Return the analytics dashboard data.
- `GET /namespace/stats/` - Return Pinecone namespace statistics.

## Employee profile route

- `PATCH /employee/{employee_id}` - Update the authenticated employee's own
  profile. The current implementation derives the user and company from the
  access token rather than trusting the path value.

Responses preserve the existing endpoint-specific structures. Validation
errors are returned by FastAPI as `422`; authentication and authorization
failures use `401` and `403`; missing resources use `404`; conflicts use
`409`; and external-service failures use `503` where the route can identify
them.
