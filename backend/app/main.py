from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.api.deps import get_db
from app.api.v1.router import router as api_router
from app.core.config import get_settings
from app.core.exceptions import CatalogueError

app = FastAPI(title="Construction Product Catalogue", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(CatalogueError)
def catalogue_error_handler(_request: Request, exc: CatalogueError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message, "errors": exc.errors})


@app.exception_handler(IntegrityError)
def integrity_error_handler(_request: Request, _exc: IntegrityError) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={"detail": "That value conflicts with an existing record", "errors": []},
    )


@app.get("/health")
def health(db: Session = Depends(get_db)) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ok"}


app.include_router(api_router, prefix="/api/v1")
