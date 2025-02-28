from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from configs.config import DB_LITE, DB_URL
from database.models import Base
from database.utils.role_utils import add_initial_roles
from database.utils.user_utils import add_initial_super_admin

# echo=True implies to show sql commands on console
# engine = create_async_engine(DB_URL, echo=True)
engine = create_async_engine(DB_LITE, echo=True)

# expire_on_commit=False instructs not to close the current session after commit command in order to continue
# working with the current session
session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


async def get_session():
    async with session_maker() as session:  # Create an AsyncSession and use it as context
        return session


async def create_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def on_startup():
    run_param = False

    # drop db if necessary
    if run_param:
        await drop_db()

    # create db
    await create_db()

    # add the initial default roles and a super admin
    session = await get_session()
    await add_initial_roles(session=session)
    await add_initial_super_admin(session=session)


async def on_shutdown():
    print('Bot shut down...')