import os
import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.logging_config import configurar_logging
from app.middleware.logging import request_logging_middleware
from app.routes import admin, alunos, auth

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
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])

os.makedirs("uploads/alunos", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(status_code=exc.status_code, content={"erro": exc.detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    erros = [f"{' -> '.join(str(l) for l in e['loc'])}: {e['msg']}" for e in exc.errors()]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"erro": "Dados invalidos", "detalhe": erros},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.exception("Erro inesperado em %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"erro": "Erro interno do servidor"})


@app.on_event("startup")
def startup():
    logger.info("Aplicacao iniciada - ambiente: %s", settings.ENVIRONMENT)


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "2.0.0"}


@app.on_event("startup")
def _seed_admin():
    """Cria, promove e sincroniza o admin automaticamente."""
    if not settings.ADMIN_EMAIL or not settings.ADMIN_PASSWORD:
        logger.debug("Seed admin desabilitado: credenciais não configuradas")
        return

    from sqlalchemy.orm import Session as DBSession
    from app.database.session import SessionLocal
    from app.models.models import Usuario as UsuarioModel
    from app.core.security import hash_senha, verificar_senha

    db: DBSession = SessionLocal()
    try:
        admin_user = db.query(UsuarioModel).filter(
            UsuarioModel.email == settings.ADMIN_EMAIL
        ).first()

        if not admin_user:
            logger.info("Criando novo usuario admin: %s", settings.ADMIN_EMAIL)
            admin_user = UsuarioModel(
                nome="Administrador",
                email=settings.ADMIN_EMAIL,
                senha=hash_senha(settings.ADMIN_PASSWORD),
                is_superuser=True,
                ativo=True,
            )
            db.add(admin_user)
            db.flush()
            db.commit()
            logger.info("Admin criado com sucesso: %s", settings.ADMIN_EMAIL)

        else:
            logger.info("Sincronizando admin existente: %s", settings.ADMIN_EMAIL)
            
            mudou = False
            
            if not admin_user.is_superuser:
                logger.debug("Elevando permissoes para superuser")
                admin_user.is_superuser = True
                mudou = True
            
            senha_sincronizada = verificar_senha(settings.ADMIN_PASSWORD, admin_user.senha)
            if not senha_sincronizada:
                if settings.sync_admin_password_on_startup:
                    logger.debug("Sincronizando senha com .env")
                    admin_user.senha = hash_senha(settings.ADMIN_PASSWORD)
                    mudou = True
                else:
                    logger.warning(
                        "Senha do admin difere de ADMIN_PASSWORD; sincronizacao automatica desabilitada"
                    )
            
            if mudou:
                db.flush()
                db.commit()
                logger.info("Admin sincronizado: %s", settings.ADMIN_EMAIL)
            else:
                logger.debug("Admin ja estava sincronizado")

    except Exception as e:
        logger.error("Erro ao sincronizar admin: %s", str(e), exc_info=True)
    finally:
        db.close()
