// FastAPI creates the backend web application and exposes HTTP API endpoints.
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

// Upload routes handle user datasets and preloaded dataset selection.
from app.routes.upload import router as upload_router
// Analysis routes start jobs, report results, visualizations, and PDF reports.
from app.routes.analysis import router as analysis_router


app = FastAPI(
    title="ImmunoXAI Analysis API",
    description="Backend API for single-cell immune-state analysis.",
    version="1.0.0",
)


// Allow the frontend development and deployed origins to call this API.
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


// Register the feature-specific routers under the /api prefix.
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


// Simple endpoints used to confirm that the backend is running.
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