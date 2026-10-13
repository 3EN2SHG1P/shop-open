import uuid
from core.timezone import now
from pathlib import Path

from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.concurrency import run_in_threadpool

from core.config import PROJECT_ROOT, config
from core.deps import require_permission
from core.errors import bad_request
from core.response import ok

router = APIRouter(prefix="/api/v1", tags=["common"])

P = require_permission

# 不含 svg：SVG 可内嵌脚本，同源托管会带来存储型 XSS
_ALLOWED_EXTS = {"jpg", "jpeg", "png", "gif", "webp"}
# 仅按文件名后缀判断并不可靠，声明的内容类型一并校验（为空时放行，避免误伤客户端）
_ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}


def _upload_root() -> Path:
    p = Path(config.upload_dir)
    return p if p.is_absolute() else PROJECT_ROOT / p


@router.post("/upload")
async def upload_image(
    request: Request,
    file: UploadFile = File(...),
    _user=Depends(P("upload:add")),
):
    name = (file.filename or "").strip()
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext not in _ALLOWED_EXTS:
        bad_request("仅支持 jpg/jpeg/png/gif/webp 图片")
    ctype = (file.content_type or "").split(";")[0].strip().lower()
    if ctype and ctype not in _ALLOWED_CONTENT_TYPES:
        bad_request(f"不支持的文件类型：{ctype}")
    max_bytes = config.upload_max_mb * 1024 * 1024
    content = await file.read(max_bytes + 1)
    if not content:
        bad_request("文件内容为空")
    if len(content) > max_bytes:
        bad_request(f"图片大小不能超过 {config.upload_max_mb}MB")
    now_dt = now()
    rel_dir = Path(str(now_dt.year)) / f"{now_dt.month:02d}"
    target = _upload_root() / rel_dir
    target.mkdir(parents=True, exist_ok=True)
    fname = f"{uuid.uuid4().hex}.{ext}"
    # 同步写盘会阻塞事件循环，交给线程池
    await run_in_threadpool((target / fname).write_bytes, content)
    base = (config.upload_public_base or str(request.base_url)).rstrip("/")
    return ok({
        "url": f"{base}/uploads/{rel_dir.as_posix()}/{fname}",
        "name": name,
        "size": len(content),
    })
