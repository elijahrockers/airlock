from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.routes import datasets, health, keys, patients, studies


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="Airlock", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(studies.router)
app.include_router(keys.router)
app.include_router(patients.router)
app.include_router(datasets.router)
