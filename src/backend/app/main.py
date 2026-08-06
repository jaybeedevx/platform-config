import logging
import os

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("webapp-backend")

APP_ENV = os.getenv("APP_ENV", "development")

app = FastAPI(title="webapp-backend", version="0.1.0")


@app.get("/api")
def api_root():
    return {"service": "webapp-backend", "env": APP_ENV, "status": "ok"}


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/readyz")
def readyz():
    # A real app would check its DB/upstream dependencies here.
    return {"status": "ready"}


Instrumentator().instrument(app).expose(app)
