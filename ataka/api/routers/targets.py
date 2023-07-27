from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ataka.api.dependencies import get_session
from ataka.common.database.models import Target

router = APIRouter(prefix="/targets", tags=['targets'])


@router.get("/")
async def all_targets(service: str = None, session: AsyncSession = Depends(get_session)):
    get_max_version = select(func.max(Target.version))
    version = (await session.execute(get_max_version)).scalar_one()

    get_targets = select(Target).where(Target.version == version)
    if service is not None:
        get_targets = get_targets.where(Target.service == service)
    targets = (await session.execute(get_targets)).scalars()
    return [x.to_dict() for x in targets]
