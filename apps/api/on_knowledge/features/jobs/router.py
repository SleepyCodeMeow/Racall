from fastapi import APIRouter

from .schemas import GenerationRequest, RetryRequest
from .service import GenerationService


def create_router(service: GenerationService) -> APIRouter:
    router = APIRouter()

    @router.get("/api/notebooks/{notebook}/jobs")
    def job_list(notebook: str):
        return service.list(notebook)

    @router.post("/api/notebooks/{notebook}/jobs", status_code=202)
    def job_submit(notebook: str, body: GenerationRequest):
        return service.submit(notebook, body)

    @router.get("/api/notebooks/{notebook}/jobs/{job}")
    def job_get(notebook: str, job: str):
        return service.get(notebook, job)

    @router.post("/api/notebooks/{notebook}/jobs/{job}/cancel")
    def job_cancel(notebook: str, job: str):
        return service.cancel(notebook, job)

    @router.post("/api/notebooks/{notebook}/jobs/{job}/retry", status_code=202)
    def job_retry(notebook: str, job: str, body: RetryRequest):
        return service.retry(notebook, job, body.request_id)

    return router
