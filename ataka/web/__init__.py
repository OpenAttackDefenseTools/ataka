from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.future import select
from sqlalchemy.orm import Session

from ataka.common import queue, database
from ataka.common.database.models import Job, Target
from ataka.common.queue import ControlQueue
from ataka.web.schemas import FlagSubmission

app = FastAPI()


@app.on_event("startup")
async def startup_event():
    await queue.connect()
    await database.connect()


@app.on_event("shutdown")
async def shutdown_event():
    await queue.disconnect()
    await database.disconnect()


async def get_session():
    async with database.get_session() as session:
        yield session


async def get_channel():
    async with await queue.get_channel() as channel:
        yield channel


@app.get("/api/targets")
async def all_targets(session: Session = Depends(get_session)):
    get_targets = select(Target).limit(100)
    target_objs = (await session.execute(get_targets)).scalars()
    targets = [x.to_dict() for x in target_objs]

    return targets


@app.get("/api/targets/service/{service_name}")
async def targets_by_service(service_name, session: Session = Depends(get_session)):
    get_targets = select(Target).where(Target.service == service_name).limit(100)
    target_objs = (await session.execute(get_targets)).scalars()
    targets = [x.to_dict() for x in target_objs]

    return targets


@app.get("/api/targets/ip/{ip_addr}")
async def targets_by_ip(ip_addr, session: Session = Depends(get_session)):
    get_targets = select(Target).where(Target.ip == ip_addr).limit(100)
    target_objs = (await session.execute(get_targets)).scalars()
    targets = [x.to_dict() for x in target_objs]

    return targets


@app.get("/api/jobs")
async def all_jobs(session: Session = Depends(get_session)):
    get_jobs = select(Job)
    job_objs = (await session.execute(get_jobs)).scalars()
    jobs = [x.to_dict() for x in job_objs]

    return jobs


@app.get("/api/job/{job_id}/status")
async def get_job(job_id, session: Session = Depends(get_session)):
    get_jobs = select(Job).where(Job.id == job_id).limit(1)
    job_obj = (await session.execute(get_jobs)).scalars().first()

    return job_obj.to_dict()


@app.get("/api/flags")
async def all_flags(session: Session = Depends(get_session)):
    return []


@app.post("/api/flag/submit")
async def submit_flag(submission: FlagSubmission, session: Session = Depends(get_session)):
    return [{"flag": flag, "success": True, "status": "valid"} for flag in submission.flags.split("\n") if len(flag) > 0]


@app.websocket("/queue")
async def websocket_endpoint(websocket: WebSocket, channel=Depends(get_channel)):
    await websocket.accept()

    try:
        control_queue = await ControlQueue.get(channel)

        async for message in control_queue.wait_for_messages():
            await websocket.send_text(message.to_bytes().decode())
    except WebSocketDisconnect:
        print("disconnected")
