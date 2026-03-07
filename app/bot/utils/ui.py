from __future__ import annotations

from app.bot.keyboards.start import start_kb
from app.bot.keyboards.parent import parent_menu_kb
from app.bot.keyboards.teacher import teacher_menu_kb
from app.bot.keyboards.cashier import cashier_menu_kb
from app.bot.keyboards.hr import hr_menu_kb
from app.bot.keyboards.admin import admin_menu_kb
from app.i18n import t
from app.models.enums import UserRole

DEFAULT_LANG = "uz"


def role_menu(role: UserRole, lang: str = DEFAULT_LANG):
    if role == UserRole.PARENT:
        return t("menu.parent.title", lang), parent_menu_kb(lang)
    if role == UserRole.TEACHER:
        return t("menu.teacher.title", lang), teacher_menu_kb(lang)
    if role == UserRole.CASHIER:
        return t("menu.cashier.title", lang), cashier_menu_kb(lang)
    if role == UserRole.HR:
        return t("menu.hr.title", lang), hr_menu_kb(lang)
    if role == UserRole.ADMIN:
        return t("menu.admin.title", lang), admin_menu_kb(lang)
    return t("start.title", lang), start_kb(lang)
