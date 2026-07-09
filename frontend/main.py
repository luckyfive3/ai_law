"""
AI法律助手 v1.0 — 前端服务入口
基于 FastAPI + Jinja2 的服务端渲染前端
"""

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pathlib import Path
import uvicorn

from routes.pages import router as pages_router
from routes.api import router as api_router

app = FastAPI(title="AI法律助手", version="1.0.0", docs_url=None, redoc_url=None)

BASE_DIR = Path(__file__).resolve().parent

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.include_router(pages_router)
app.include_router(api_router, prefix="/api/v1/proxy")


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    from fastapi.templating import Jinja2Templates
    templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
    return HTMLResponse(
        templates.get_template("pages/404.html").render({"request": request}),
        status_code=404,
    )


@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    from fastapi.templating import Jinja2Templates
    templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
    return HTMLResponse(
        templates.get_template("pages/500.html").render({"request": request}),
        status_code=500,
    )


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=3000, reload=True)
