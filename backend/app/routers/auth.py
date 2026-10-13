from fastapi import APIRouter, Depends, Request

from core.deps import get_current_user
from core.response import ok
from schemas.auth import LoginReq, PasswordReq
from services import auth as auth_service

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login")
async def login(req: Request, body: LoginReq):
    data = await auth_service.login(body.username, body.password, req.client.host if req.client else "", req.headers.get("user-agent", ""))
    return ok(data)


@router.post("/logout")
async def logout(req: Request, user=Depends(get_current_user)):
    await auth_service.logout(user, req.client.host if req.client else "")
    return ok()


@router.get("/me")
async def me(user=Depends(get_current_user)):
    return ok(await auth_service.me(user.id))


@router.put("/password")
async def change_password(body: PasswordReq, user=Depends(get_current_user)):
    await auth_service.change_password(user.id, body.old_password, body.new_password)
    return ok()
