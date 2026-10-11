import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database.session import engine, Base
from app.api.routes import router as api_router
from app.services.handwriting.ocr_engine import handwriting_service
from app.services.grading.engine import grading_engine

# Initialize SQLite tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Grade Script API",
    description="Deep Learning Handwritten Exam Evaluation API with Microsoft TrOCR & Sentence Transformers",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static file serving for uploads (page previews, crops)
UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "uploads"))
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Include API routes
app.include_router(api_router, prefix="/api")

@app.on_event("startup")
async def startup_event():
    # Models will be lazily loaded or warmed up asynchronously in the background
    pass

@app.get("/api/health")

def health_check():
    return {
        "status": "healthy",
        "ocr_device": handwriting_service.device,
        "ocr_loaded": handwriting_service._loaded,
        "grading_loaded": grading_engine._embedder_loaded
    }
