from .start import router as start
from .auth_parent import router as auth_parent
from .auth_employee import router as auth_employee
from .parent import router as parent
from .teacher import router as teacher
from .cashier import router as cashier
from .hr import router as hr
from .admin import router as admin
from .face_enroll import router as face_enroll

__all__ = ["start", "auth_parent", "auth_employee", "parent", "teacher", "cashier", "hr", "admin", "face_enroll"]