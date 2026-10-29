"""第三方平台联调入口（仅调试，非业务接口）。

敦煌单店与多店编排共用 OpenAPI 标签 common:testAPI:dhgate：
- /testAPI/dhgate/*：单店官方接口，/docs 中排在前面
- /testAPI/dhgate/commerce/*：多店汇总 / 同步，整组排在全部单店接口之后

未写入顺序列表的新单店接口也会排在多店编排之前。
"""

from fastapi import APIRouter

from app.api.common.test_api.commerce import router as commerce_test_router
from app.api.common.test_api.dhgate import router as dhgate_test_router

router = APIRouter(prefix="/testAPI")
router.include_router(dhgate_test_router)
router.include_router(commerce_test_router)

# /docs 展示顺序。路径相对 /api/v1/common/testAPI/dhgate。
# 单店在前；多店编排整组在最后。新增单店接口写进 DHGATE_SINGLE_DOCS_PATH_ORDER，
# 没写入的单店路径也会排在多店之前。
DHGATE_SINGLE_DOCS_PATH_ORDER: tuple[str, ...] = (
    "/punish-brand/list",
    "/punish/list",
    "/dispute/processing/list",
    "/order/disputeopen/list",
    "/wis/core-info",
    "/wis/detail-page",
    "/wis/keywordtop10",
    "/seller/ad/order-report",
    "/seller/ad/prod-report",
    "/category/list",
    "/category/get",
    "/category/path/get",
    "/categorys/commissions",
    "/measures/list",
    "/item/get",
    "/item/html/get",
    "/item/shelf",
    "/item/fission/add",
    "/item/group/list",
    "/item/aftersale/list",
    "/item/img/tweak",
    "/shipping/template/list",
)
DHGATE_MULTI_DOCS_PATH_ORDER: tuple[str, ...] = (
    "/commerce/punish/summary",
    "/commerce/dispute/processing/summary",
    "/commerce/order/disputeopen/summary",
    "/commerce/product/sync",
    "/commerce/product/syncfromfile",
    "/commerce/item/group/sync",
    "/commerce/item/aftersale/sync",
    "/commerce/shipping/template/sync",
)

_DHGATE_DOCS_PREFIX = "/api/v1/common/testAPI/dhgate"


def _dhgate_docs_rank(suffix: str) -> tuple[int, int]:
    """单店（含未登记的新单店）在前，多店编排在后。"""
    if suffix.startswith("/commerce/"):
        try:
            return (1, DHGATE_MULTI_DOCS_PATH_ORDER.index(suffix))
        except ValueError:
            return (1, len(DHGATE_MULTI_DOCS_PATH_ORDER))
    try:
        return (0, DHGATE_SINGLE_DOCS_PATH_ORDER.index(suffix))
    except ValueError:
        return (0, len(DHGATE_SINGLE_DOCS_PATH_ORDER))


def reorder_dhgate_openapi_paths(paths: dict) -> dict:
    """单店联调在前，多店编排整体在最后；其它模块路径的相对顺序不变。"""
    grouped = [
        item for item in paths.items() if item[0].startswith(_DHGATE_DOCS_PREFIX)
    ]
    grouped.sort(
        key=lambda item: (
            *_dhgate_docs_rank(item[0][len(_DHGATE_DOCS_PREFIX) :]),
            item[0],
        )
    )
    pending = iter(grouped)
    rebuilt: dict = {}
    for path, item in paths.items():
        if path.startswith(_DHGATE_DOCS_PREFIX):
            new_path, new_item = next(pending)
            rebuilt[new_path] = new_item
        else:
            rebuilt[path] = item
    return rebuilt
