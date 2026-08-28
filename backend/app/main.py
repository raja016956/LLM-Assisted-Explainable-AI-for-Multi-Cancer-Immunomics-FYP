from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.upload import router as upload_router
from app.routes.analysis import router as analysis_router


app = FastAPI(
    title="ImmunoXAI Analysis API",
    description="Backend API for single-cell immune-state analysis.",
    version="1.0.0",
)


# ---------------------------------------------------------
# CORS
# ---------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://immuno-xai-insight.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# Routes
# ---------------------------------------------------------

app.include_router(
    upload_router,
    prefix="/api",
)

app.include_router(
    analysis_router,
    prefix="/api",
)


# ---------------------------------------------------------
# Health check
# ---------------------------------------------------------

@app.get("/")
async def root():
    return {
        "name": "ImmunoXAI Analysis API",
        "status": "running",
        "version": "1.0.0",
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
    }