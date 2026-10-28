from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.errors import AppError
from app.services import tiktok_oauth

router = APIRouter(prefix="/oauth/tiktok", tags=["common:utils"])


@router.get("/callback")
def tiktok_oauth_callback(
    code: str | None = Query(default=None, description="授权码"),
    state: str | None = Query(default=None, description="防 CSRF 的 state"),
    error: str | None = Query(default=None, description="TikTok 返回的错误码"),
    error_description: str | None = Query(
        default=None,
        description="TikTok 返回的错误描述",
    ),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """TikTok OAuth 回调（公开）。换 token 并建档后 302 到前端。"""
    if error:
        message = error_description or error or "授权失败"
        return RedirectResponse(
            tiktok_oauth.build_frontend_redirect(ok=False, message=message),
            status_code=302,
        )

    try:
        result = tiktok_oauth.handle_oauth_callback(
            db,
            code=code,
            state=state,
        )
    except AppError as exc:
        return RedirectResponse(
            tiktok_oauth.build_frontend_redirect(ok=False, message=exc.message),
            status_code=302,
        )
    except Exception:
        return RedirectResponse(
            tiktok_oauth.build_frontend_redirect(
                ok=False,
                message="授权处理失败，请重试",
            ),
            status_code=302,
        )

    return RedirectResponse(
        tiktok_oauth.build_frontend_redirect(
            ok=True,
            store_id=result.store_id,
            message=result.message,
        ),
        status_code=302,
    )
