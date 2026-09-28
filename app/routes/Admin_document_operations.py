"""
Admin document routes.
=======================

Admin-only endpoints for ingesting, archiving, and unarchiving
company documents in the knowledge base.
"""
import os.path
import tempfile
from pathlib import Path

from .route_services import APIRouter, UploadFile, File, Depends, HTTPException
from .route_services import Parse_Doc_for_Rag
from .route_services import (
    archive_chunks,
    insert_chunks,
    unarchive_documents_op,
)
from .route_services import create_documents, documents, archive_documents_from_database, \
    unrchive_documents_from_database, delete_documents_from_database
from .route_services import embedd_chunks, extract_to_objects
from .route_services import get_namespace_by_company_id
from .route_services import get_user_by_id, require_admin
from ..RAG.vector_database.pincecone_operations import delete_chunks, status_documents
from ..database.crud.company_crud import can_add_to_namespace

admin_router = APIRouter(tags=["admin-documents"])


#works good
#should be optimized
#old one
# @admin_router.post("/upload")
# async def upload_documents(
#     file: UploadFile = File(...),
#     current_user=Depends(require_admin),
# ):
#     """
#     Upload and ingest a document into the company's vector database.
#     """
#
#     # Get user/company information
#     requested_info = get_user_by_id(current_user.id)
#
#     company_id = requested_info["users"][0][1]
#     uploaded_by = requested_info["users"][0][0]
#
#     # Get company's Pinecone namespace
#     get_namespace = get_namespace_by_company_id(company_id)
#     company_namespace = str(get_namespace["namespace"][0]).lower()
#
#     # Read uploaded file
#     contents = await file.read()
#
#     with open(file.filename, "wb") as f:
#         f.write(contents)
#     # Extract
#     extract = extract_to_objects(file.filename)
#     # Parse / chunk
#     parse_docs = Parse_Doc_for_Rag(
#         objects=extract,
#         file_path=file.filename,
#         company_id=company_id
#     )
#     # Embed
#     vectors = parse_docs["vectors"]
#     embedd_docs = embedd_chunks(vectors)
#
#     # Insert into company's namespace
#     result = insert_chunks(
#         embedd_docs[1:],
#         namespace_name=company_namespace
#     )
#
#     # Create document record
#     doc_id = parse_docs["document_id"]
#
#     doc = documents(
#         document_id=doc_id,
#         company_id=company_id,
#         uploaded_by=uploaded_by,
#         filename=file.filename,
#         version=1,
#         status="ready",
#         pinecone_namespace=company_namespace,
#         total_chunks=len(embedd_docs),
#     )
#
#     insertion_request = create_documents(data=doc)
#
#     if insertion_request["success"]:
#         return {"status": "Success"}
#
#     return {"message": insertion_request}
#new endpoint
@admin_router.post("/upload")
async def upload_documents(
    file: UploadFile = File(...),
    current_user=Depends(require_admin),
):
    """
    Upload and ingest a document into the company's vector database.
    """

    try:
        # --------------------------------------------------
        # 1. Validate file
        # --------------------------------------------------

        if not file.filename:
            raise HTTPException(
                status_code=400,
                detail="No file was provided."
            )

        # --------------------------------------------------
        # 2. Get user/company information
        # --------------------------------------------------

        requested_info = get_user_by_id(current_user.id)

        if not requested_info or requested_info is None:
            raise HTTPException(
                status_code=404,
                detail="User information not found."
            )

        company_id = requested_info["company_id"]
        uploaded_by = requested_info["user_id"]

        # --------------------------------------------------
        # 3. Get company namespace
        # --------------------------------------------------

        namespace_data = get_namespace_by_company_id(company_id)

        if (
            namespace_data["success"] == False
            or
            namespace_data is False
        ):
            raise HTTPException(
                status_code=404,
                detail="Company namespace not found."
            )

        company_namespace = str(
            namespace_data["namespace"]
        ).lower()

        # --------------------------------------------------
        # 4. Read file
        # --------------------------------------------------

        contents = await file.read()

        if not contents:
            raise HTTPException(
                status_code=400,
                detail="The uploaded file is empty."
            )

        # --------------------------------------------------
        # 5. Save temporarily
        # --------------------------------------------------

        safe_filename = Path(file.filename).name

        with tempfile.TemporaryDirectory() as temp_dir:

            file_path = os.path.join(
                temp_dir,
                safe_filename
            )

            with open(file_path, "wb") as f:
                f.write(contents)

            # --------------------------------------------------
            # 6. Extract
            # --------------------------------------------------

            try:
                extract = extract_to_objects(file_path)

            except Exception as e:
                print(f"Document extraction error: {e}")

                raise HTTPException(
                    status_code=400,
                    detail="Unable to extract content from the uploaded document."
                )

            if not extract:
                raise HTTPException(
                    status_code=400,
                    detail="The document contains no readable content."
                )

            # --------------------------------------------------
            # 7. Parse / chunk
            # --------------------------------------------------

            try:
                parse_docs = Parse_Doc_for_Rag(
                    objects=extract,
                    file_path=file_path,
                    company_id=company_id
                )

            except Exception as e:
                print(f"Document parsing error: {e}")

                raise HTTPException(
                    status_code=500,
                    detail="Failed to process the document."
                )

            if not parse_docs:
                raise HTTPException(
                    status_code=500,
                    detail="Document processing returned no result."
                )

            # --------------------------------------------------
            # 8. Embeddings
            # --------------------------------------------------

            try:
                vectors = parse_docs["vectors"]

                if not vectors:
                    raise HTTPException(
                        status_code=400,
                        detail="No chunks were generated from the document."
                    )

                embedd_docs = embedd_chunks(vectors)

            except HTTPException:
                raise

            except Exception as e:
                print(f"Embedding error: {e}")

                raise HTTPException(
                    status_code=503,
                    detail="Embedding service is currently unavailable."
                )
            #check if the Admin Or hr has free space to load their documents into Namespace
            if can_add_to_namespace(company_id=company_id,vectors_numbers=len(embedd_docs)) is False:
                raise HTTPException(status_code=413,
                                    detail="Your Reached The maximum Limit of the storage.upgrade for scalable space"
                                    )


            # --------------------------------------------------
            # 9. Pinecone insertion
            # --------------------------------------------------

            try:
                result = insert_chunks(
                    embedd_docs[1:],
                    namespace_name=company_namespace
                )

            except Exception as e:
                print(f"Pinecone insertion error: {e}")

                raise HTTPException(
                    status_code=503,
                    detail="Unable to store document vectors."
                )

            # --------------------------------------------------
            # 10. Create document record
            # --------------------------------------------------

            try:
                doc_id = parse_docs["document_id"]

                doc = documents(
                    document_id=doc_id,
                    company_id=company_id,
                    uploaded_by=uploaded_by,
                    filename=safe_filename,
                    version=1,
                    status="ready",
                    pinecone_namespace=company_namespace,
                    total_chunks=len(embedd_docs),
                )

                insertion_request = create_documents(
                    data=doc
                )
                if insertion_request == False:
                    raise HTTPException(status_code=503,detail="Unable to insert documents.")

            except Exception as e:
                print(f"Document database error: {e}")

                raise HTTPException(
                    status_code=500,
                    detail="Document vectors were stored, but the document record could not be created."
                )

            if not insertion_request.get("success"):
                raise HTTPException(
                    status_code=500,
                    detail="Failed to create document record."
                )

        # --------------------------------------------------
        # Success
        # --------------------------------------------------

        return {
            "status": True,
            "message": "Document uploaded successfully.",
            "document_id": doc_id,
            "filename": safe_filename,
            "total_chunks": len(embedd_docs)
        }

    except HTTPException:
        raise

    except Exception as e:
        print(f"Unexpected upload error: {e}")

        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while uploading the document."
        )





#works good
@admin_router.post("/archive/{document_id}")
async def archive_documents(
    document_id: str,
    current_user=Depends(require_admin)
):
    try:
        # Get user/company information
        requested_info = get_user_by_id(current_user.id)

        if not requested_info or requested_info is None:
            raise HTTPException(
                status_code=404,
                detail="User information not found."
            )

        company_id = requested_info["company_id"]

        # Get company's Pinecone namespace
        get_namespace = get_namespace_by_company_id(company_id)

        if (
                get_namespace["success"] == False
                or
                get_namespace is False
        ):
            raise HTTPException(
                status_code=404,
                detail="Company namespace not found."
            )

        company_namespace = str(
            get_namespace["namespace"]
        ).lower()

        # Check document status
        try:
            check_status = status_documents(
                document_id,
                company_namespace
            )
        except HTTPException:
            raise
        except Exception as e:
            print(f"Document status check error: {e}")
            raise HTTPException(
                status_code=503,
                detail="Unable to check document status."
            )

        if check_status == "archived":
            return {
                "status": True,
                "message": "Document already archived."
            }

        # Archive document in Pinecone
        try:
            request = archive_chunks(
                document_id,
                company_namespace
            )
        except Exception as e:
            print(f"Pinecone archive error: {e}")
            raise HTTPException(
                status_code=503,
                detail="Unable to archive document."
            )

        if not request or request.get("status") != "success":
            raise HTTPException(
                status_code=503,
                detail="Unable to archive document."
            )

        # Archive document in database
        try:
            archive_documents_from_database(
                document_id,
                company_id
            )
        except Exception as e:
            print(f"Database archive error: {e}")
            raise HTTPException(
                status_code=500,
                detail=(
                    "Document was archived in the vector database, "
                    "but the database record could not be updated."
                )
            )

        return {
            "status": True,
            "message": "Document archived successfully.",
            "document_id": document_id
        }

    except HTTPException:
        raise

    except Exception as e:
        print(f"Unexpected archive error: {e}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while archiving the document."
        )
@admin_router.post("/unarchive/{document_id}")
async def unarchive_documents(
    document_id: str,
    current_user=Depends(require_admin)
):
    try:
        # -----------------------------------
        # 1. Validate document ID
        # -----------------------------------

        if not document_id:
            raise HTTPException(
                status_code=400,
                detail="Document ID is required."
            )

        # -----------------------------------
        # 2. Get user/company information
        # -----------------------------------

        requested_info = get_user_by_id(current_user.id)

        if requested_info is None or not requested_info:
            raise HTTPException(
                status_code=404,
                detail="User information not found."
            )

        company_id = requested_info["company_id"]

        # -----------------------------------
        # 3. Get company namespace
        # -----------------------------------

        get_namespace = get_namespace_by_company_id(company_id)

        if (
            get_namespace == False
            or
            get_namespace["success"] == False
        ):
            raise HTTPException(
                status_code=404,
                detail="Company namespace not found."
            )

        company_namespace = str(
            get_namespace["namespace"]
        ).lower()

        # -----------------------------------
        # 4. Check document status
        # -----------------------------------

        try:
            check_status = status_documents(
                document_id,
                company_namespace
            )

        except HTTPException:
            raise

        except Exception as e:
            print(f"Document status error: {e}")

            raise HTTPException(
                status_code=503,
                detail="Unable to check document status."
            )

        # -----------------------------------
        # 5. Check if already unarchived
        # -----------------------------------

        if check_status == "ready":
            raise HTTPException(
                status_code=400,
                detail="The document is already unarchived."
            )

        # -----------------------------------
        # 6. Unarchive in Pinecone
        # -----------------------------------

        try:
            request = unarchive_documents_op(
                document_id,
                company_namespace
            )

        except HTTPException:
            raise

        except Exception as e:
            print(f"Pinecone unarchive error: {e}")

            raise HTTPException(
                status_code=503,
                detail="Unable to unarchive document."
            )

        if not request.get("status"):
            raise HTTPException(
                status_code=503,
                detail="Unable to unarchive document."
            )

        # -----------------------------------
        # 7. Update database
        # -----------------------------------

        try:
            database_request = unrchive_documents_from_database(
                document_id,
                company_id
            )

        except Exception as e:
            print(f"Database unarchive error: {e}")

            # IMPORTANT:
            # Pinecone was already updated.
            # Database update failed.

            raise HTTPException(
                status_code=500,
                detail="Document was updated in the vector database, but the database status could not be updated."
            )

        # -----------------------------------
        # 8. Success
        # -----------------------------------

        return {
            "status": True,
            "message": "Document unarchived successfully.",
            "document_id": document_id
        }

    except HTTPException:
        raise

    except Exception as e:
        print(f"Unexpected unarchive error: {e}")

        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while unarchiving the document."
        )


@admin_router.post("/delete/{document_id}")
async def delete_documents(
    document_id: str,
    current_user=Depends(require_admin)
):
    try:
        requested_info = get_user_by_id(current_user.id)

        if not requested_info or requested_info is None:
            raise HTTPException(
                status_code=404,
                detail="User information not found."
            )

        company_id = requested_info["company_id"]

        get_namespace = get_namespace_by_company_id(company_id)

        if (
            get_namespace is False
            or
            get_namespace["success"] ==False
        ):
            raise HTTPException(
                status_code=404,
                detail="Company namespace not found."
            )

        company_namespace = str(
            get_namespace["namespace"]
        ).lower()

        request = delete_chunks(
            document_id,
            company_namespace
        )

        if not request or request.get("status") != "success":
            raise HTTPException(
                status_code=503,
                detail="Unable to delete document."
            )

        delete_docs = delete_documents_from_database(
            document_id,
            company_id
        )
        if delete_docs is False:
            raise HTTPException(status_code=404,detail="Document is Not Found")

        return {
            "status": True,
            "message": "Document deleted successfully.",
            "document_id": document_id
        }

    except HTTPException:
        raise

    except Exception as e:
        print(f"Delete document error: {e}")

        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred."
        )