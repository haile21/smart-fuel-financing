from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uuid

from app.core.config import settings

from .routers import (
    auth,
    users,
    drivers,
    stations,

    loans_transactions,
    credit_scoring,
    bank_integration,
    admin,
    admin,
    reports,
    banks,
)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Fuel Financing Backend",
        description="Backend API for Smart Fuel Financing System",
        version="1.0.0",
    )
    
    @app.get("/", tags=["health"])
    def root():
        """Root endpoint - health check."""
        return {
            "status": "healthy",
            "service": "Fuel Financing Backend",
            "version": "1.0.0",
        }
    
    @app.get("/health", tags=["health"])
    def health_check():
        """Health check endpoint for Render."""
        return {"status": "healthy"}

    # Configure CORS
    # Parse CORS origins from environment variable (comma-separated list, or "*" for all)
    #cors_origins = settings.cors_origins.split(",") if settings.cors_origins != "*" else ["*"]
    cors_origins = ["*"]
    cors_origins = [origin.strip() for origin in cors_origins]
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],  # Allows all methods (GET, POST, PUT, DELETE, etc.)
        allow_headers=["*"],  # Allows all headers
    )

    @app.middleware("http")
    async def add_trace_id(request: Request, call_next):
        trace_id = request.headers.get("x-trace-id") or str(uuid.uuid4())
        request.state.trace_id = trace_id
        response = await call_next(request)
        # Ensure all responses have trace_id
        if isinstance(response, JSONResponse):
            body = response.body
        response.headers["x-trace-id"] = trace_id
        return response

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        trace_id = getattr(request.state, "trace_id", str(uuid.uuid4()))
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal Server Error", "trace_id": trace_id},
        )

    # Main API Routes (RESTful structure)
    app.include_router(auth.router, prefix="/auth", tags=["auth"])
    app.include_router(users.router, prefix="", tags=["users"])
    app.include_router(drivers.router, prefix="/drivers", tags=["drivers"])
    app.include_router(stations.router, prefix="/stations", tags=["stations"])

    app.include_router(loans_transactions.router, prefix="", tags=["loans-transactions"])
    app.include_router(credit_scoring.router, prefix="", tags=["credit-scoring"])
    app.include_router(bank_integration.router, prefix="", tags=["bank-integration"])
    app.include_router(admin.router, prefix="", tags=["admin"])
    app.include_router(reports.router, prefix="", tags=["reports"])
    app.include_router(banks.router, prefix="/banks", tags=["banks"])
    
    return app


app = create_app()


