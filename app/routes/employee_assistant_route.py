import uuid
from .route_services import HTTPException
from .route_services import get_current_user
from .route_services import APIRouter,Depends
from ..RAG.vector_database.llm_response.LLM import LLM_response
from ..RAG.vector_database.query import pinecone_query
from ..analysis.conversation_analysis import analysis_process
from ..database.crud.company_crud import get_namespace_by_company_id
from ..database.crud.conversation_analysis_crud import insert_conversation_analysis
from ..database.crud.conversation_crud import create_conversation
from ..database.crud.conversation_document_crud import create_documents_from_pinecone
from ..database.crud.users_crud import get_user_by_id
from .route_services import time
from .route_services import json

employee_router = APIRouter(tags=["chat"])

@employee_router.post("/employee/question")
async def employee_chat(
    question: str,
    session_id: str | None = None,
    current_user=Depends(get_current_user)
):
    # Create a new session if needed
    session_id = session_id or str(uuid.uuid4())
    # Get user information
    requested_info = get_user_by_id(current_user.id)

    if not requested_info or requested_info is None:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    company_id = requested_info["company_id"]
    user_id = requested_info["user_id"]
    # Get company namespace
    namespace_result = get_namespace_by_company_id(company_id)

    if not namespace_result.get("success"):
        raise HTTPException(
            status_code=404,
            detail="Company not found"
        )

    company_namespace = str(
        namespace_result["namespace"]
    ).lower()

    # Retrieve relevant documents
    pinecone_documents = pinecone_query(
        employee_question=question,
        top_k=3,
        employee_namespace=company_namespace
    )

    # Make sure retrieval returned the expected structure
    if not isinstance(pinecone_documents, list):
        raise HTTPException(
            status_code=500,
            detail="Invalid document retrieval response"
        )

    # Generate LLM response
    start_time = time.perf_counter()

    chat_response = LLM_response(
        employee_question=question,
        docs=pinecone_documents
    )
    print(chat_response)

    response_time_ms = round(
        (time.perf_counter() - start_time) * 1000,
        3
    )

    # Parse LLM response
    llm_response = json.loads(chat_response["response"])
    print(llm_response)

    answer = llm_response["answer"]
    confidence = llm_response["confidence"]
    print(confidence, answer)

    # Save conversation
    insert_request = create_conversation(
        company_id=company_id,
        session_id=session_id,
        user_id=user_id,
        question=question,
        answer=answer,
        response_time_ms=response_time_ms,
        confidence=confidence,
        prompt_tokens=chat_response["usage"].prompt_tokens,
        completion_tokens=chat_response["usage"].completion_tokens,
        cached=False
    )
    if insert_request is False:
        raise HTTPException(status_code=400, detail="Failed to create conversation")

    # Save retrieved documents
    create_documents_from_pinecone(
        conversation_id=insert_request["conversation_id"],
        pinecone_documents=pinecone_documents
    )

    # Run analysis
    analysis_process(
        conversation_id=insert_request["conversation_id"]
    )

    return {
        "answer": answer,
        "confidence": confidence,
        "session_id": session_id
    }





