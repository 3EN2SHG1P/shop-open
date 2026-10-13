from fastapi import APIRouter, Depends, Request

from core.config import config
from core.deps import AuthMember, client_ip, get_current_member
from core.response import ok
from schemas.shop_auth import LoginReq, PasswordChangeReq, ProfileUpdateReq, RegisterReq, SendCodeReq
from services import shop_auth as service

router = APIRouter(prefix="/api/v1/shop", tags=["商城前台-会员认证"])


@router.post("/auth/send-code")
async def send_code(body: SendCodeReq, request: Request):
    code = await service.send_code(body.phone, body.scene, client_ip(request))
    data = {"expiresIn": config.sms_code_expire_seconds}
    if not config.sms_mock:
        return ok(data, "验证码已发送")
    # 演示通道没有真实短信：必须同时说清「没发短信」和「码是什么」，否则用户永远等不到。
    data["devCode"] = code
    return ok(data, "验证码已生成（演示通道：未真实发送短信，验证码已在 devCode 返回）")


@router.post("/auth/register")
async def register(body: RegisterReq, request: Request):
    await service.register(body.phone, body.code, body.password, client_ip(request))
    return ok(message="注册成功")


@router.post("/auth/login")
async def login(body: LoginReq, request: Request):
    data = await service.login(body.phone, body.password, client_ip(request))
    return ok(data)


@router.get("/auth/me")
async def me(member: AuthMember = Depends(get_current_member)):
    return ok(await service.member_detail(member.id))


@router.put("/auth/password")
async def change_password(body: PasswordChangeReq, request: Request, member: AuthMember = Depends(get_current_member)):
    await service.change_password(member.id, body.old_password, body.new_password, client_ip(request))
    return ok(message="密码修改成功")


@router.put("/auth/profile")
async def update_profile(body: ProfileUpdateReq, request: Request, member: AuthMember = Depends(get_current_member)):
    return ok(await service.update_profile(member.id, body.nickname, body.avatar, client_ip(request)))


@router.post("/auth/logout")
async def logout(request: Request, member: AuthMember = Depends(get_current_member)):
    await service.logout(member.id, client_ip(request))
    return ok(message="已退出登录")
