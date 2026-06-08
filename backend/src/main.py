from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from src.utils.logger import get_logger, log_ctx
from src.routers import (
    auth,
    admin,
    chat,
    doctor,
    finance,
    patient,
    prescriptions,
    registration,
    report,
)
from .models import Base
from .database import engine

tags_metadata = [
    {"name": "Health", "description": "System health checks"},
    {"name": "Authentication", "description": "Login and authentication"},
    {"name": "Patient Registration", "description": "Patient registration operations"},
    {"name": "Doctor Operations", "description": "Doctor dashboard and patient management"},
    {"name": "Documents", "description": "Document upload and retrieval"},
    {"name": "Reports", "description": "Report review and approval"},
    {"name": "Prescriptions", "description": "Prescription management"},
    {"name": "Patient Portal", "description": "Patient-facing endpoints"},
    {"name": "Finance", "description": "Finance operations"},
    {"name": "Admin", "description": "Administrative endpoints"},
    {"name": "AI Chat", "description": "Medical AI chat and voice interactions"},
]

app = FastAPI(
    title="MedFlow AI",
    version="1.0.0",
    openapi_tags=tags_metadata
)

logger = get_logger(__name__)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(
        "Incoming request",
        extra=log_ctx(
            method=request.method,
            path=request.url.path,
            client=request.client.host if request.client else None,
        ),
    )
    response = await call_next(request)
    logger.info(
        "Request completed",
        extra=log_ctx(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
        ),
    )
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)


@app.get("/healthy", tags=["Health"])
def health_check():
    return {"status": "Healthy"}



app.include_router(auth.router)
app.include_router(admin.router, tags=["Admin"])
app.include_router(chat.router, tags=["AI Chat"])
app.include_router(doctor.router, tags=["Doctor Operations"])
app.include_router(finance.router, tags=["Finance"])
app.include_router(patient.router, tags=["Patient Portal"])
app.include_router(prescriptions.router, tags=["Prescriptions"])
app.include_router(registration.router, tags=["Patient Registration"])
app.include_router(report.router)


Instrumentator().instrument(app).expose(app)