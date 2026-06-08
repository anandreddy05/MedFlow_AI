import os
from fastapi import (
    APIRouter,
    UploadFile,
    File,
    Form,
    HTTPException,
    Depends,
)

from sqlalchemy.orm import Session
from typing import Annotated, Optional
from datetime import datetime
from pathlib import Path
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import tempfile
from openai import OpenAI
import base64
from langfuse import propagate_attributes

from src.rag.utils.prompts import (
    FINANCE_SYSTEM_PROMPT,
    CLINICAL_SYSTEM_PROMPT,
    PATIENT_SYSTEM_PROMPT,
    GENERAL_HEALTH_SYSTEM_PROMPT,
)

from src.models import (
    Patient,
    DoctorPatientAssignment,
)
from src.ingestion.schemas import (
    ChatRequest,
)
from .auth import get_current_user, get_db
from src.rag.utils.intent_classifier import RetrieverIntent
from src.rag.shared_resources import (
    retriever,
    latest_retriever,
    intent_router,
    langfuse,
    handler,
)
from src.guardrails.input_router import InputGuard
from src.guardrails.output_auditor import OutputGuard
from src.utils.logger import get_logger, log_ctx, timed_log

from src.cache.kb_cache import kb_cache

load_dotenv(override=True)

logger = get_logger(__name__)

router = APIRouter()

UPLOAD_DIR = Path("storage/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


@timed_log(logger, "openai_generation")
def _invoke_llm(model, messages_for_llm, callbacks=None):
    config = {"callbacks": callbacks} if callbacks else {}
    return model.invoke(messages_for_llm, config=config)


@timed_log(logger, "openai_transcription")
def _transcribe_voice(temp_audio_path: str, prompt: str) -> str:
    client = OpenAI(base_url="https://us.api.openai.com/v1")
    with open(temp_audio_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            prompt=prompt,
        )
    return transcription.text


@router.post("/chat")
async def question(user: user_dependency, db: db_dependency, request: ChatRequest):
    role = user.get("role")
    logger.info(
        "Chat request received",
        extra=log_ctx(
            user_id=user.get("id"),
            role=role,
            patient_id=request.patient_id,
            query_length=len(request.query),
        ),
    )
    target_patient_id = None

    # --- 1. Role-Based Identity Resolution ---
    if role == "finance":
        target_patient_id = "COMPLIANCE_DOMAIN"
        target_collection = "knowledge_base"
        target_report_type = "finance_compliance"
        active_system_prompt = FINANCE_SYSTEM_PROMPT

    elif role == "patient":
        patient_profile = (
            db.query(Patient).filter(Patient.user_id == user.get("id")).first()
        )
        if not patient_profile:
            raise HTTPException(status_code=404, detail="Patient profile not found.")
        target_collection = "medical_documents"
        target_patient_id = str(patient_profile.patient_id)
        target_report_type = None
        active_system_prompt = PATIENT_SYSTEM_PROMPT

    elif role == "doctor":
        if not request.patient_id:
            raise HTTPException(
                status_code=400,
                detail="Doctors must provide a patient_id in the request.",
            )

        # Security: Is this doctor actively assigned to this patient?
        assignment = (
            db.query(DoctorPatientAssignment)
            .filter(
                DoctorPatientAssignment.doctor_id == user.get("id"),
                DoctorPatientAssignment.patient_id == request.patient_id,
                DoctorPatientAssignment.status == "active",
            )
            .first()
        )

        if not assignment:
            logger.warning(
                "Authorization failure: doctor chat for unassigned patient",
                extra=log_ctx(
                    doctor_id=user.get("id"),
                    patient_id=request.patient_id,
                ),
            )
            raise HTTPException(
                status_code=403,
                detail="You are not authorized to view this patient's records.",
            )
        target_patient_id = request.patient_id
        target_collection = "medical_documents"
        target_report_type = None
        active_system_prompt = CLINICAL_SYSTEM_PROMPT

    else:
        logger.warning(
            "Authorization failure: chat endpoint",
            extra=log_ctx(user_id=user.get("id"), role=role),
        )
        raise HTTPException(
            status_code=403, detail="Role not authorized for conversational AI."
        )

    with langfuse.start_as_current_observation(
        as_type="span", name="medflow_chat"
    ) as root_span:
        root_span.update(
            input={
                "query": request.query,
                "role": role,
                "patient_id": target_patient_id,
            }
        )

        with propagate_attributes(
            session_id=target_patient_id,
            user_id=str(role),
            tags=[role],
        ):
            input_check = InputGuard.verify(request.query, callbacks=[handler])
            if not input_check.is_safe:
                return {
                    "user_query": request.query,
                    "final_answer": input_check.fallback_message,
                    "sources": [],
                }

            if input_check.route == "general_health" and role in [
                "patient",
                "doctor",
                "nurse",
            ]:
                target_patient_id = "PUBLIC_DOMAIN"
                target_collection = "knowledge_base"
                target_report_type = "general_health"
                active_system_prompt = GENERAL_HEALTH_SYSTEM_PROMPT

            elif input_check.route == "personal_health" and role in [
                "patient",
                "doctor",
            ]:
                pass

            intent = intent_router.route_query(request.query)
            if target_collection == "knowledge_base":
                intent = RetrieverIntent.HISTORICAL

                cached_answer = kb_cache.get(
                    query=request.query,
                    role=role,
                    report_type=target_report_type,
                )

                if cached_answer:
                    logger.info(
                        "Knowledge base cache hit",
                        extra=log_ctx(
                            role=role,
                            report_type=target_report_type,
                        ),
                    )

                    return {
                        "user_query": request.query,
                        "final_answer": cached_answer,
                        "sources": [],
                        "cached": True,
                    }

                logger.info(
                    "Knowledge base cache miss",
                    extra=log_ctx(
                        role=role,
                        report_type=target_report_type,
                    ),
                )
            if intent == RetrieverIntent.CURRENT_CONTEXT:
                latest_docs = latest_retriever.retrieve(
                    db=db,
                    patient_id=target_patient_id,
                )

                context = latest_retriever.build_context(latest_docs)

                retrieved_docs = []

                for doc in latest_docs.values():
                    retrieved_docs.append(
                        {
                            "content": doc.content_markdown,
                            "metadata": {
                                "document_id": doc.document_id,
                                "report_type": doc.report_type,
                                "created_at": doc.created_at.isoformat()
                                if doc.created_at
                                else None,
                            },
                        }
                    )

            else:
                logger.info(
                    "Qdrant retrieval requested",
                    extra=log_ctx(
                        collection=target_collection,
                        report_type=target_report_type,
                        patient_id=target_patient_id,
                    ),
                )

                retrieved_docs = retriever.retrieve(
                    query=request.query,
                    patient_id=target_patient_id,
                    collection_name=target_collection,
                    report_type=target_report_type,
                )

                if retrieved_docs and len(retrieved_docs) > 0:
                    context_parts = []
                    for idx, doc in enumerate(retrieved_docs, start=1):
                        context_parts.append(f"[SOURCE {idx}]\n{doc['content']}")
                    context = "\n\n".join(context_parts)
                else:
                    context = "No relevant documents found."

            history = [
                {"role": msg.role, "content": msg.content} for msg in request.history
            ]

            # --- 3. LLM Generation ---
            model = ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0,
                base_url="https://us.api.openai.com/v1",
            )

            current_date = datetime.now().strftime("%B %d, %Y")
            anchored_query = (
                f"[System Note: Today is {current_date}]\nUser Query: {request.query}"
            )
            messages_for_llm = [
                {"role": "system", "content": active_system_prompt},
                {"role": "system", "content": f"Medical Record Context:\n{context}"},
                *history,
                {"role": "user", "content": anchored_query},
            ]

            final_answer = _invoke_llm(model, messages_for_llm, callbacks=[handler])

            logger.debug(
                "Raw LLM output before auditor",
                extra=log_ctx(
                    answer_preview=(final_answer.content or "")[:200],
                    role=role,
                ),
            )

            if (
                target_collection == "knowledge_base"  # ← was checking stale names
                or intent == RetrieverIntent.CURRENT_CONTEXT
            ):
                display_text = final_answer.content
                is_response_safe = True

            else:
                # Strict auditing remains active for Historical Qdrant Vector searches!
                output_check = OutputGuard.verify(
                    context=context,
                    proposed_answer=final_answer.content,
                    callbacks=[handler] if handler else None,
                )
                display_text = (
                    final_answer.content
                    if output_check.is_safe
                    else output_check.safe_content
                )
                is_response_safe = output_check.is_safe
            # --- 4. Source Mapping ---
            sources = []
            seen_documents = set()
            for idx, doc in enumerate(retrieved_docs, start=1):
                metadata = doc["metadata"]
                doc_id = (
                    metadata.get("document_id")
                    or metadata.get("source_file")
                    or f"Unknown_Doc_{idx}"
                )

                if doc_id not in seen_documents:
                    seen_documents.add(doc_id)

                    raw_type = metadata.get("report_type", "")

                    if raw_type == "general_health":
                        source_file = metadata.get("source_file")
                        if source_file:
                            clean_name = os.path.splitext(
                                os.path.basename(source_file)
                            )[0]
                            display_type = (
                                clean_name.replace("_", " ").replace("-", " ").title()
                            )
                        else:
                            display_type = "Medical Knowledge Base"
                    else:
                        display_type = raw_type

                    sources.append(
                        {
                            "source_id": len(sources) + 1,
                            "document_id": doc_id,
                            "report_type": display_type,
                            "date": metadata.get("created_at"),
                            "raw_content": doc["content"],
                        }
                    )

            static_fallback = "I apologize, but I am unable to process that request right now. Please consult your healthcare provider."

            if target_collection == "knowledge_base" and display_text:
                kb_cache.set(
                    query=request.query,
                    role=role,
                    report_type=target_report_type,
                    answer=display_text,
                )
            return {
                "user_query": request.query,
                "final_answer": display_text or static_fallback,
                "sources": sources if is_response_safe else [],
            }


@router.post("/chat/voice")
async def voice_question(
    user: user_dependency,
    db: db_dependency,
    audio: UploadFile = File(...),
    patient_id: Optional[str] = Form(None),
):
    role = user.get("role")
    logger.info(
        "Voice chat request received",
        extra=log_ctx(user_id=user.get("id"), role=role, patient_id=patient_id),
    )

    if role == "finance":
        target_patient_id = "COMPLIANCE_DOMAIN"
        target_collection = "knowledge_base"
        target_report_type = "finance_compliance"
        active_system_prompt = FINANCE_SYSTEM_PROMPT

    elif role == "patient":
        patient_profile = (
            db.query(Patient).filter(Patient.user_id == user.get("id")).first()
        )
        if not patient_profile:
            raise HTTPException(status_code=404, detail="Patient profile not found.")
        target_patient_id = str(patient_profile.patient_id)
        target_collection = "medical_documents"
        target_report_type = None
        active_system_prompt = PATIENT_SYSTEM_PROMPT

    elif role == "doctor":
        if not patient_id:
            raise HTTPException(
                status_code=400, detail="Doctors must provide a patient_id."
            )
        assignment = (
            db.query(DoctorPatientAssignment)
            .filter(
                DoctorPatientAssignment.doctor_id == user.get("id"),
                DoctorPatientAssignment.patient_id == patient_id,
                DoctorPatientAssignment.status == "active",
            )
            .first()
        )

        if not assignment:
            logger.warning(
                "Authorization failure: voice chat for unassigned patient",
                extra=log_ctx(doctor_id=user.get("id"), patient_id=patient_id),
            )
            raise HTTPException(
                status_code=403,
                detail="You are not authorized to view this patient's records.",
            )

        target_patient_id = patient_id
        target_collection = "medical_documents"
        target_report_type = None
        active_system_prompt = CLINICAL_SYSTEM_PROMPT
    else:
        logger.warning(
            "Authorization failure: voice chat endpoint",
            extra=log_ctx(user_id=user.get("id"), role=role),
        )
        raise HTTPException(status_code=403, detail="Unauthorized role.")

    # 1. Save the incoming audio blob to a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_audio:
        temp_audio.write(await audio.read())
        temp_audio_path = temp_audio.name

    try:
        user_query = _transcribe_voice(temp_audio_path, "The user might speak English.")

    finally:
        # Always clean up the temporary file
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)

    # 2. Actually RUN the InputGuard on the transcribed text
    input_check = InputGuard.verify(user_query)
    if not input_check.is_safe:
        return {
            "user_transcript": user_query,
            "final_answer": input_check.fallback_message,
            "sources": [],
        }

    # 3. Add our routing switch
    if input_check.route == "general_health" and role in ["patient", "doctor", "nurse"]:
        target_patient_id = "PUBLIC_DOMAIN"
        target_collection = "knowledge_base"
        target_report_type = "general_health"
        active_system_prompt = GENERAL_HEALTH_SYSTEM_PROMPT
    
    if target_collection == "knowledge_base":
        cached_answer = kb_cache.get(
            query=user_query,
            role=role,
            report_type=target_report_type,
        )
        if cached_answer:
            logger.info(
                "Voice chat cache hit",
                extra=log_ctx(role=role, report_type=target_report_type),
            )
            return {
                "user_transcript": user_query,
                "final_answer": cached_answer,
                "audio_base64": None,
                "sources": [],
                "cached": True,
            }

    # 4. Pass BOTH variables and the TRANSCRIBED text (user_query) to the retriever
    retrieved_docs = retriever.retrieve(
        query=user_query,
        patient_id=target_patient_id,
        collection_name=target_collection,
        report_type=target_report_type,
    )

    # Handle empty search results so the loop doesn't crash ---
    if isinstance(retrieved_docs, str):
        context = retrieved_docs
        retrieved_docs = []
    else:
        context_parts = []
        for idx, doc in enumerate(retrieved_docs, start=1):
            context_parts.append(f"[SOURCE {idx}]\n{doc['content']}")
        context = "\n\n".join(context_parts)

    model = ChatOpenAI(
        model="gpt-4o-mini", temperature=0, base_url="https://us.api.openai.com/v1"
    )

    messages_for_llm = [
        {"role": "system", "content": active_system_prompt},
        {"role": "system", "content": f"Medical Record Context:\n{context}"},
        {"role": "user", "content": user_query},
    ]

    final_answer = _invoke_llm(model, messages_for_llm)

    if target_collection == "knowledge_base":
        display_text = final_answer.content
        is_response_safe = True
    else:
        output_check = OutputGuard.verify(
            context=context, proposed_answer=final_answer.content
        )
        display_text = (
            final_answer.content if output_check.is_safe else output_check.safe_content
        )
        is_response_safe = output_check.is_safe

    # --- FIX 3: Pretty Citation Names ---
    sources = []
    seen_documents = set()
    for doc in retrieved_docs:
        metadata = doc["metadata"]
        doc_id = (
            metadata.get("document_id") or metadata.get("source_file") or "Unknown_Doc"
        )

        if doc_id not in seen_documents:
            seen_documents.add(doc_id)

            raw_type = metadata.get("report_type", "")
            if raw_type == "general_health":
                source_file = metadata.get("source_file")
                if source_file:
                    clean_name = os.path.splitext(os.path.basename(source_file))[0]
                    display_type = (
                        clean_name.replace("_", " ").replace("-", " ").title()
                    )
                else:
                    display_type = "Medical Knowledge Base"
            else:
                display_type = raw_type

            sources.append(
                {
                    "source_id": len(sources) + 1,
                    "document_id": doc_id,
                    "report_type": display_type,
                    "date": metadata.get("created_at"),
                    "raw_content": doc["content"],
                }
            )

    static_fallback = "I apologize, but I am unable to process that request right now."
    final_text = display_text or static_fallback

    audio_base64 = None

    try:
        tts_client = OpenAI(base_url="https://us.api.openai.com/v1")
        tts_response = tts_client.audio.speech.create(
            model="tts-1", voice="nova", input=final_text
        )
        audio_base64 = base64.b64encode(tts_response.content).decode("utf-8")
    except Exception as e:
        logger.warning(
            "OpenAI TTS generation failed",
            extra=log_ctx(error=str(e), user_id=user.get("id")),
        )
        pass

    return {
        "user_transcript": user_query,
        "final_answer": final_text,
        "audio_base64": audio_base64,
        "sources": sources if is_response_safe else [],
    }
