from fastapi import APIRouter, Depends, Query

from core.deps import require_permission
from core.response import ok
from schemas.content import AdPositionSave, AdSave, ArticleCategorySave, ArticleSave, NoticeSave
from services import content as svc

router = APIRouter(prefix="/api/v1", tags=["content"])

P = require_permission


# ==================== 文章分类 ====================


@router.get("/article-categories")
async def list_article_categories(_user=Depends(P("content:list"))):
    return ok(await svc.list_article_categories_with_count())


@router.post("/article-categories")
async def create_article_category(body: ArticleCategorySave, user=Depends(P("content:add"))):
    return ok({"id": await svc.save_article_category(None, body, user)})


@router.put("/article-categories/{category_id}")
async def update_article_category(category_id: int, body: ArticleCategorySave, user=Depends(P("content:edit"))):
    return ok({"id": await svc.save_article_category(category_id, body, user)})


@router.delete("/article-categories/{category_id}")
async def delete_article_category(category_id: int, user=Depends(P("content:delete"))):
    await svc.delete_article_category(category_id, user)
    return ok()


# ==================== 文章 ====================


@router.get("/articles")
async def list_articles(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str = "",
    category_id: int | None = None,
    status: int | None = None,
    _user=Depends(P("content:list")),
):
    filters = {"keyword": keyword, "category_id": category_id, "status": status}
    return ok(await svc.list_articles(page, page_size, filters))


@router.post("/articles")
async def create_article(body: ArticleSave, user=Depends(P("content:add"))):
    return ok({"id": await svc.save_article(None, body, user)})


@router.put("/articles/{article_id}")
async def update_article(article_id: int, body: ArticleSave, user=Depends(P("content:edit"))):
    return ok({"id": await svc.save_article(article_id, body, user)})


@router.delete("/articles/{article_id}")
async def delete_article(article_id: int, user=Depends(P("content:delete"))):
    await svc.delete_article(article_id, user)
    return ok()


# ==================== 广告位 ====================


@router.get("/ad-positions")
async def list_ad_positions(_user=Depends(P("content:list"))):
    return ok(await svc.list_ad_positions())


@router.post("/ad-positions")
async def create_ad_position(body: AdPositionSave, user=Depends(P("content:add"))):
    return ok({"id": await svc.save_ad_position(None, body, user)})


@router.put("/ad-positions/{position_id}")
async def update_ad_position(position_id: int, body: AdPositionSave, user=Depends(P("content:edit"))):
    return ok({"id": await svc.save_ad_position(position_id, body, user)})


@router.delete("/ad-positions/{position_id}")
async def delete_ad_position(position_id: int, user=Depends(P("content:delete"))):
    await svc.delete_ad_position(position_id, user)
    return ok()


# ==================== 广告 ====================


@router.get("/ads")
async def list_ads(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str = "",
    position_id: int | None = None,
    status: int | None = None,
    _user=Depends(P("content:list")),
):
    filters = {"keyword": keyword, "position_id": position_id, "status": status}
    return ok(await svc.list_ads(page, page_size, filters))


@router.post("/ads")
async def create_ad(body: AdSave, user=Depends(P("content:add"))):
    return ok({"id": await svc.save_ad(None, body, user)})


@router.put("/ads/{ad_id}")
async def update_ad(ad_id: int, body: AdSave, user=Depends(P("content:edit"))):
    return ok({"id": await svc.save_ad(ad_id, body, user)})


@router.delete("/ads/{ad_id}")
async def delete_ad(ad_id: int, user=Depends(P("content:delete"))):
    await svc.delete_ad(ad_id, user)
    return ok()


# ==================== 公告 ====================


@router.get("/notices")
async def list_notices(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str = "",
    status: int | None = None,
    _user=Depends(P("content:list")),
):
    filters = {"keyword": keyword, "status": status}
    return ok(await svc.list_notices(page, page_size, filters))


@router.post("/notices")
async def create_notice(body: NoticeSave, user=Depends(P("content:add"))):
    return ok({"id": await svc.save_notice(None, body, user)})


@router.put("/notices/{notice_id}")
async def update_notice(notice_id: int, body: NoticeSave, user=Depends(P("content:edit"))):
    return ok({"id": await svc.save_notice(notice_id, body, user)})


@router.delete("/notices/{notice_id}")
async def delete_notice(notice_id: int, user=Depends(P("content:delete"))):
    await svc.delete_notice(notice_id, user)
    return ok()


@router.get("/content/level-options")
async def level_options(_user=Depends(P("content:list"))):
    return ok(await svc.level_options())
