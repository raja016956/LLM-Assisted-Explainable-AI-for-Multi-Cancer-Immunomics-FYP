# FastAPI provides the backend application and HTTP API functionality.
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import routers that contain the upload and analysis API endpoints.
from app.routes.upload import router as upload_router
from app.routes.analysis import router as analysis_router


# ---------------------------------------------------------
# FastAPI Application
# ---------------------------------------------------------

# Create the main FastAPI application with basic API metadata.
app = FastAPI(
    title="ImmunoXAI Analysis API",
    description="Backend API for single-cell immune-state analysis.",
    version="1.0.0",
)


# ---------------------------------------------------------
# CORS
# ---------------------------------------------------------

# Allow the local and deployed frontend applications
# to send requests to the FastAPI backend.
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
# API Routes
# ---------------------------------------------------------

# Register upload and analysis routers under the /api prefix.
# Routes inside these routers become available as /api/...
app.include_router(
    upload_router,
    prefix="/api",
)

app.include_router(
    analysis_router,
    prefix="/api",
)


# ---------------------------------------------------------
# Health Checks
# ---------------------------------------------------------

# Root endpoint used to confirm that the backend is running.
@app.get("/")
async def root():
    return {
        "name": "ImmunoXAI Analysis API",
        "status": "running",
        "version": "1.0.0",
    }


# Health endpoint used to verify that the API is healthy.
@app.get("/health")
async def health():
    return {
        "status": "healthy",
    }
