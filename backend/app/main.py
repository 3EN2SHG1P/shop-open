import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.cors import CORSMiddleware

from core import database
from core.config import config
from core.errors import BizError
from core.response import error_body, ok


@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.init_pool()
    yield
    await database.close_pool()


app = FastAPI(
    title="商城后台管理系统",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

if "*" in config.cors_origins:
    print("[warn] CORS_ORIGINS=* ，跨域完全放开，仅允许本地调试，部署前必须配置白名单")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if "*" in config.cors_origins else config.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(BizError)
async def biz_error_handler(request: Request, exc: BizError):
    return JSONResponse(status_code=exc.http_status, content=error_body(exc.code, exc.message))


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    first = exc.errors()[0] if exc.errors() else {}
    loc = ".".join(str(x) for x in first.get("loc", []) if x not in ("body", "query", "path"))
    msg = first.get("msg", "参数校验失败")
    text = f"{loc}: {msg}" if loc else msg
    return JSONResponse(status_code=422, content=error_body(2001, text))


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(status_code=exc.status_code, content=error_body(2001, str(exc.detail)))


@app.exception_handler(Exception)
async def unhandled_handler(request: Request, exc: Exception):
    # 必须落日志：否则对外只看到 500，外部部署者无从定位
    logging.getLogger("shop").exception("unhandled error: %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content=error_body(5000, "服务器内部错误"))


@app.get("/api/v1/health")
async def health():
    try:
        await database.fetch_one("SELECT 1 AS v")
        db_status = "up"
    except Exception:
        logging.getLogger("shop").exception("health check: database unreachable")
        db_status = "down"
    return ok({"status": "up", "db": db_status, "app": config.app_name})


def register_routers():
    import importlib
    import pkgutil

    import routers

    for mod in pkgutil.iter_modules(routers.__path__):
        module = importlib.import_module(f"routers.{mod.name}")
        router = getattr(module, "router", None)
        if router is not None:
            app.include_router(router)


def register_static():
    """托管后台管理系统(manager)静态页面（8001 同源、根路径跳登录）与上传文件目录 /uploads。
    商城前台(front)已独立静态托管于 8000 端口，不再由后端 mount。"""

    @app.middleware("http")
    async def no_cache_static(request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/manager"):
            response.headers.setdefault("Cache-Control", "no-cache")
        return response

    @app.get("/", include_in_schema=False)
    async def index():
        return RedirectResponse(url="/manager/login.html")

    manager_dir = Path(config.manager_dir)
    if manager_dir.is_dir():
        app.mount("/manager", StaticFiles(directory=manager_dir, html=True), name="manager")

    uploads_dir = Path(config.upload_dir)
    if not uploads_dir.is_absolute():
        uploads_dir = Path(__file__).resolve().parents[2] / uploads_dir
    uploads_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=uploads_dir, html=False), name="uploads")


register_routers()
register_static()
