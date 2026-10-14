from fastapi import APIRouter

from app.api.admin.auth import router as auth_router
from app.api.admin.categories import router as categories_router
from app.api.admin.missions import router as missions_router
from app.api.admin.permissions import router as permissions_router
from app.api.admin.platform_roles import router as platform_roles_router
from app.api.admin.platform_staff import router as platform_staff_router
from app.api.admin.products import router as products_router
from app.api.admin.sku import router as sku_router
from app.api.admin.stores import router as stores_router
from app.api.admin.supplier_roles import router as supplier_roles_router
from app.api.admin.supplier_staff import router as supplier_staff_router
from app.api.admin.suppliers import router as suppliers_router
from app.api.admin.templates import router as templates_router
from app.api.admin.users import router as users_router

router = APIRouter(prefix="/admin")
router.include_router(auth_router)
router.include_router(users_router)
router.include_router(permissions_router)
router.include_router(platform_roles_router)
router.include_router(platform_staff_router)
router.include_router(supplier_roles_router)
router.include_router(suppliers_router)
router.include_router(supplier_staff_router)
router.include_router(stores_router)
router.include_router(products_router)
router.include_router(categories_router)
router.include_router(missions_router)
router.include_router(templates_router)
router.include_router(sku_router)
