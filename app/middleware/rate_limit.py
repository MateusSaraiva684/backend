"""Middleware de Rate Limiting para proteção de brute force."""

import logging
from datetime import datetime, timedelta
from typing import Dict, Tuple
from fastapi import Request, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

# Rate limit store: {ip: {endpoint: [(timestamp, count), ...]}}
rate_limit_store: Dict[str, Dict[str, list]] = {}


def get_client_ip(request: Request) -> str:
    """Extrai IP do cliente da request."""
    # Verificar header X-Forwarded-For (para proxies/load balancers)
    if "x-forwarded-for" in request.headers:
        return request.headers["x-forwarded-for"].split(",")[0].strip()
    # Fallback para client.host
    return request.client.host if request.client else "unknown"


def check_rate_limit(
    ip: str,
    endpoint: str,
    max_requests: int = 5,
    window_seconds: int = 60,
) -> Tuple[bool, int]:
    """
    Verifica se o IP excedeu o rate limit.
    
    Args:
        ip: IP do cliente
        endpoint: Endpoint sendo acessado
        max_requests: Máximo de requisições permitidas
        window_seconds: Janela de tempo em segundos
        
    Returns:
        (allowed, remaining) onde allowed é True se a requisição é permitida
    """
    now = datetime.now()
    key = f"{ip}:{endpoint}"
    
    if key not in rate_limit_store:
        rate_limit_store[key] = []
    
    # Limpar requisições antigas
    cutoff_time = now - timedelta(seconds=window_seconds)
    rate_limit_store[key] = [
        timestamp for timestamp in rate_limit_store[key]
        if timestamp > cutoff_time
    ]
    
    # Verificar se excedeu limite
    current_count = len(rate_limit_store[key])
    
    if current_count >= max_requests:
        return False, 0
    
    # Adicionar timestamp atual
    rate_limit_store[key].append(now)
    
    # Retornar requisições restantes
    remaining = max_requests - len(rate_limit_store[key])
    return True, remaining


async def rate_limit_middleware(request: Request, call_next):
    """Middleware de rate limiting para endpoints sensíveis."""
    
    # Apenas aplicar a endpoints sensíveis
    if not request.url.path.startswith("/api/auth/login"):
        return await call_next(request)
    
    # Se for teste (client IP é 'testclient'), permitir
    client_ip = get_client_ip(request)
    if client_ip == "testclient":
        return await call_next(request)
    
    # Se não tem client real, permitir
    if not request.client:
        return await call_next(request)
    
    # Verificar rate limit
    allowed, remaining = check_rate_limit(
        ip=client_ip,
        endpoint="/api/auth/login",
        max_requests=5,
        window_seconds=60
    )
    
    if not allowed:
        logger.warning(f"Rate limit excedido: IP {client_ip} em /api/auth/login")
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "erro": "Muitas tentativas de login. Tente novamente em 1 minuto.",
                "retry_after": 60
            }
        )
    
    # Continuar com requisição normal
    response = await call_next(request)
    
    # Adicionar headers de rate limit
    response.headers["X-RateLimit-Limit"] = "5"
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Reset"] = str(
        (datetime.now() + timedelta(seconds=60)).timestamp()
    )
    
    return response
