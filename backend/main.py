from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import init_db
from routes.auth_routes import router as auth_router
from routes.analyze import router as analyze_router
from routes.chat import router as chat_router
from routes.history import router as history_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on startup."""
    init_db()
    yield


app = FastAPI(
    title="Code Repository Onboarding API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow the Vite dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth_router)
app.include_router(analyze_router)
app.include_router(chat_router)
app.include_router(history_router)


@app.get("/")
def root():
    return {"status": "ok", "message": "Code Repository Onboarding API"}
