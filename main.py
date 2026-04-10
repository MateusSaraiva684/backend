import os
import logging
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.logging_config import configurar_logging
from app.database.session import Base, engine
from app.middleware.logging import request_logging_middleware
from app.routes import alunos, auth
from app.routes import admin  # ← novo

configurar_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Sistema Escolar API",
    version="2.0.0",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url=None,
)

origins = ["http://localhost:5173", "http://localhost:3000"]
if settings.FRONTEND_URL:
    origins.append(settings.FRONTEND_URL)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.middleware("http")(request_logging_middleware)

app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(alunos.router, prefix="/api/alunos", tags=["Alunos"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])  # ← novo

os.makedirs("uploads/alunos", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(status_code=exc.status_code, content={"erro": exc.detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    erros = [f"{' → '.join(str(l) for l in e['loc'])}: {e['msg']}" for e in exc.errors()]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"erro": "Dados inválidos", "detalhe": erros},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.exception("Erro inesperado em %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"erro": "Erro interno do servidor"})


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    logger.info("Aplicação iniciada — ambiente: %s", settings.ENVIRONMENT)


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "2.0.0"}


# Sobrescreve o startup anterior
@app.on_event("startup")
def _promote_admin():
    """Promove ADMIN_EMAIL a superusuário automaticamente."""
    if not settings.ADMIN_EMAIL:
        return
    from sqlalchemy.orm import Session as DBSession
    from app.database.session import SessionLocal
    from app.models.models import Usuario as UsuarioModel
    db: DBSession = SessionLocal()
    try:
        admin = db.query(UsuarioModel).filter(
            UsuarioModel.email == settings.ADMIN_EMAIL
        ).first()
        if admin and not admin.is_superuser:
            admin.is_superuser = True
            db.commit()
            logger.info("Usuário '%s' promovido a superusuário", settings.ADMIN_EMAIL)
    finally:
        db.close()
