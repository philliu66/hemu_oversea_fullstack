from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.errors import AppError, bad_request
from app.schemas.common import ApiResponse, success
from app.schemas.store import DhgateOauthCodePublic
from app.services.dhgate import oauth as dhgate_oauth

router = APIRouter(prefix="/oauth/dhgate", tags=["common:utils"])


@router.get(
    "/code",
    response_model=ApiResponse[DhgateOauthCodePublic],
    summary="[联调] 获取敦煌 OAuth code",
)
def dhgate_oauth_code(
    code: str | None = Query(default=None, description="敦煌回调带回的授权码"),
    state: str | None = Query(default=None, description="防 CSRF 的 state"),
    error: str | None = Query(default=None, description="敦煌返回的错误码"),
    error_description: str | None = Query(
        default=None,
        description="敦煌返回的错误描述",
    ),
) -> ApiResponse[DhgateOauthCodePublic]:
    """
    按敦煌文档获取 Authorization Code，不需要店铺。

    授权地址只带 client_id、response_type、redirect_uri、scope、state。
    不传参数时返回 authorize_url；浏览器完成授权后，敦煌重定向回本接口，
    响应中的 code、state 再传给 /callback。换 token 写入哪家店在 callback 里指定。
    """
    if error:
        raise bad_request(error_description or error or "授权失败")

    redirect_uri = dhgate_oauth.code_redirect_uri()
    if code:
        if not state:
            raise bad_request("缺少 state")
        return success(
            DhgateOauthCodePublic(
                code=code,
                state=state,
                redirect_uri=redirect_uri,
            ),
            message="请使用 code 与 state 调用 /oauth/dhgate/callback，并带上 store_id",
        )

    authorize_url, pending_state = dhgate_oauth.create_code_authorize_url()
    return success(
        DhgateOauthCodePublic(
            authorize_url=authorize_url,
            state=pending_state,
            redirect_uri=redirect_uri,
        ),
        message="请在浏览器打开 authorize_url，授权后本接口会返回 code",
    )


@router.get("/callback")
def dhgate_oauth_callback(
    code: str | None = Query(default=None, description="授权码"),
    state: str | None = Query(default=None, description="防 CSRF 的 state"),
    store_id: int | None = Query(
        default=None,
        description="联调：把 /code 拿到的 token 写入的店铺 ID。正式授权由 state 识别店铺，可不传",
    ),
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
            store_id=store_id,
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
