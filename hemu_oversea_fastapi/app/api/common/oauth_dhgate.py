from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.errors import AppError
from app.services.dhgate import oauth as dhgate_oauth

router = APIRouter(prefix="/oauth/dhgate", tags=["common:utils"])


@router.get("/callback")
def dhgate_oauth_callback(
    code: str | None = Query(default=None, description="授权码"),
    state: str | None = Query(default=None, description="防 CSRF 的 state"),
    error: str | None = Query(default=None, description="敦煌返回的错误码"),
    error_description: str | None = Query(
        default=None,
        description="敦煌返回的错误描述",
    ),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """敦煌 OAuth 回调（公开）。换 token 后 302 到前端，并带 status / msg。"""
    if error:
        message = error_description or error or "授权失败"
        return RedirectResponse(
            dhgate_oauth.build_frontend_redirect(ok=False, message=message),
            status_code=302,
        )

    try:
        store = dhgate_oauth.handle_oauth_callback(
            db,
            code=code,
            state=state,
        )
    except AppError as exc:
        return RedirectResponse(
            dhgate_oauth.build_frontend_redirect(ok=False, message=exc.message),
            status_code=302,
        )
    except Exception:
        return RedirectResponse(
            dhgate_oauth.build_frontend_redirect(
                ok=False,
                message="授权处理失败，请重试",
            ),
            status_code=302,
        )

    return RedirectResponse(
        dhgate_oauth.build_frontend_redirect(
            ok=True,
            store_id=store.id,
            message="授权成功",
        ),
        status_code=302,
    )
