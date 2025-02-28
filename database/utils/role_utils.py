from sqlalchemy.ext.asyncio import AsyncSession

from database.cruds.role_crud import get_roles, add_roles
from enums.telegram_eunms import UserPrivileges, RoleType
from database.models import Role


async def add_initial_roles(session: AsyncSession) -> None:
    roles = await get_roles(session=session)
    if roles.__len__() == 0:
        await add_roles(session=session, roles=get_initial_roles())


def get_initial_roles():
    user_role = Role(
        name=RoleType.USER.name,
        privileges=f'{UserPrivileges.ASK_QUESTIONS.name}'
    )
    admin_role = Role(
        name=RoleType.ADMIN.name,
        privileges=f'{UserPrivileges.ASK_QUESTIONS.name};{UserPrivileges.VIEW_MESSAGES.name}'
    )
    superior_admin_role = Role(
        name=RoleType.SUPERIOR_ADMIN.name,
        privileges=f'{UserPrivileges.ASK_QUESTIONS.name};'
                   f'{UserPrivileges.VIEW_MESSAGES.name};'
                   f'{UserPrivileges.VIEW_FILES.name}'
    )
    super_admin_role = Role(
        name=RoleType.SUPER_ADMIN.name,
        privileges=f'{UserPrivileges.ASK_QUESTIONS.name};'
                   f'{UserPrivileges.VIEW_MESSAGES.name};'
                   f'{UserPrivileges.VIEW_FILES.name};'
                   f'{UserPrivileges.VIEW_ADMINS.name}'
    )

    return [user_role, admin_role, superior_admin_role, super_admin_role]