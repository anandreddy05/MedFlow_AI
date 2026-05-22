from fastapi import FastAPI
from src.routers import auth, medflow
from .models import Base
from .database import engine

app = FastAPI(title="MedFlow AI")

Base.metadata.create_all(bind=engine)

app.include_router(auth.router)
app.include_router(medflow.router)
