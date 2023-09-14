from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from ataka.api.dependencies import get_session, get_channel
from ataka.common.database.models import Flag, Execution
from ataka.common.job_execution_status import JobExecutionStatus
from ataka.common.queue import OutputMessage, OutputQueue

router = APIRouter(prefix="/flag", tags=['flag'])


class FlagSubmission(BaseModel):
    flags: str


@router.post("/submit")
async def submit_flag(submission: FlagSubmission, session: AsyncSession = Depends(get_session),
                      channel=Depends(get_channel)):
    execution = Execution(status=JobExecutionStatus.FINISHED, stdout=submission.flags, stderr='')
    session.add(execution)
    await session.commit()

    output_message = OutputMessage(execution_id=execution.id, stdout=True, output=submission.flags)
    output_queue = await OutputQueue.get(channel)
    await output_queue.send_message(output_message)

    return {"execution_id": execution.id}


@router.get("/execution/{execution_id}")
async def get_flags_by_execution(execution_id: int, session: AsyncSession = Depends(get_session)):
    get_flags = select(Flag).where(Flag.execution_id == execution_id).options(joinedload(Flag.execution)
                                                                              .joinedload(Execution.target))
    flags = (await session.execute(get_flags)).unique().scalars()
    return [flag.to_dict() |
            ({} if flag.execution.target is None else {"target": flag.execution.target.to_dict()})
            for flag in flags]
