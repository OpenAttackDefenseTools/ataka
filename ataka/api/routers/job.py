import time
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ataka.api.dependencies import get_session, get_channel
from ataka.common.database.models import Execution, Job
from ataka.common.job_execution_status import JobExecutionStatus
from ataka.common.queue import JobQueue, JobMessage, JobAction, OutputQueue, OutputMessage

router = APIRouter(prefix="/job", tags=['job'])


class NewJob(BaseModel):
    targets: list[int]
    exploit_id: str | None
    manual_id: None | str
    timeout: int


@router.post("/")
async def post_job(job: NewJob, session: AsyncSession = Depends(get_session), channel=Depends(get_channel)):
    if job.exploit_id is not None and job.manual_id is not None:
        raise HTTPException(400, detail="Can't supply both exploit_id and manual_id")
    elif job.exploit_id is None and job.manual_id is None:
        raise HTTPException(400, detail="Need to provide either exploit_id and manual_id")

    if len(job.targets) == 0:
        raise HTTPException(400, detail="Need to provide at least one target")

    new_job = Job(status=JobExecutionStatus.QUEUED if job.exploit_id is not None else JobExecutionStatus.RUNNING,
                  exploit_id=job.exploit_id, manual_id=job.manual_id,
                  timeout=datetime.fromtimestamp(time.time() + job.timeout))

    session.add(new_job)
    executions = [Execution(job=new_job, target_id=target, status=JobExecutionStatus.RUNNING) for target in job.targets]
    session.add_all(executions)

    await session.commit()

    if job.exploit_id is not None:
        job_queue = await JobQueue.get(channel)
        await job_queue.send_message(JobMessage(action=JobAction.QUEUE, job_id=new_job.id))

    return new_job.to_dict() | {"executions": [e.to_dict() for e in executions]}


class ExecutionResult(BaseModel):
    stdout: str
    stderr: str
    status: JobExecutionStatus = JobExecutionStatus.CANCELLED

@router.post("/execution/{execution_id}/finish")
async def finish_execution(execution_id: int, execution: ExecutionResult, session: AsyncSession = Depends(get_session),
                           channel=Depends(get_channel)):
    update_execution = update(Execution) \
        .where(Execution.id == execution_id) \
        .values(status=execution.status,
                stdout=execution.stdout,
                stderr=execution.stderr)
    await session.execute(update_execution)
    await session.commit()

    stdout_message = OutputMessage(execution_id=execution_id, stdout=True, output=execution.stdout)
    stderr_message = OutputMessage(execution_id=execution_id, stdout=False, output=execution.stderr)
    output_queue = await OutputQueue.get(channel)
    await output_queue.send_message(stdout_message)
    await output_queue.send_message(stderr_message)

    return {}


@router.post("/{job_id}/finish")
async def finish_execution(job_id: int, status: JobExecutionStatus = JobExecutionStatus.FINISHED, session: AsyncSession = Depends(get_session)):
    print(job_id, status)
    update_job = update(Job).where(Job.id == job_id).values(status=status)
    await session.execute(update_job)
    await session.commit()
    return {}


@router.get("/{job_id}")
async def get_job(job_id: int, session: AsyncSession = Depends(get_session)):
    get_job = select(Job) \
        .where(Job.id == job_id) \
        .options(selectinload(Job.executions).selectinload(Execution.target))
    job = (await session.execute(get_job)).scalar_one()

    return job.to_dict() | {"executions": [x.to_dict() | {"target": x.target.to_dict()} for x in job.executions]}
