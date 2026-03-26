from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.config import settings
from api.db import Base, engine
from api.routes import export, imports, parse, prices, products, settings as settings_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Price Parser API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


@app.middleware("http")
async def api_key_middleware(request: Request, call_next):
    if request.url.path.startswith("/api") and request.headers.get("X-API-Key") != settings.api_key:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
    return await call_next(request)


app.include_router(products.router, prefix="/api")
app.include_router(prices.router, prefix="/api")
app.include_router(imports.router, prefix="/api")
app.include_router(settings_router.router, prefix="/api")
app.include_router(export.router, prefix="/api")
app.include_router(parse.router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}
