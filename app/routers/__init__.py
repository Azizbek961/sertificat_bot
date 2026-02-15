from .common import router as common_router
from .user import router as user_router
from .admin import router as admin_router

all_routers = [common_router, user_router, admin_router]