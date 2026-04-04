import time
import logging
from fastapi import Request

logger = logging.getLogger("api.requests")


async def request_logging_middleware(request: Request, call_next):
    inicio = time.perf_counter()
    response = await call_next(request)
    duracao = (time.perf_counter() - inicio) * 1000

    logger.info(
        "%s %s → %d (%.0fms)",
        request.method,
        request.url.path,
        response.status_code,
        duracao,
    )
    return response
