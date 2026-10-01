from fastapi import APIRouter, UploadFile, File, Depends, HTTPException

# RAG folders
from app.RAG.chunking.Parse_Documents import Parse_Doc_for_Rag
from app.RAG.vector_database.pincecone_operations import (
    archive_chunks,
    insert_chunks,
    unarchive_documents as unarchive_documents_op,status_documents
)
from app.RAG.embedding.embedding_model import embedd_chunks
from app.RAG.ingestion.extraction_process import extract_to_objects
from app.RAG.ingestion.preprocessing import clean_records
from app.database.crud.users_crud import get_user_by_id,get_users_by_company_id,delete_user_by_id,change_role,create_user
#company crud
from app.database.crud.company_crud import get_namespace_by_company_id,delete_company
#document crud
from app.database.crud.documents_crud import create_documents,documents,archive_documents_from_database,unrchive_documents_from_database,delete_documents_from_database,get_documents
from app.services.main_logics import get_user_role
from app.auth.user_auth import get_current_user,require_admin
from app.services.main_logics import get_user_role
from app.features.invitation.routes import send_invitation_email,create_invite_from_admin,validate_invitation
import time
from app.services.main_logics import get_user_role
import json
from app.auth.user_auth import require_hr,require_hr_admin


