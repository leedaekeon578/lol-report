from fastapi import FastAPI

from app.api import router
from app.errors import register_handlers

app = FastAPI(title="LoL Report")
register_handlers(app)
app.include_router(router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
