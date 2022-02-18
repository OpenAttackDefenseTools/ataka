import asyncio
import random
import re
from asyncio import CancelledError

from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.future import select
from sqlalchemy.orm import Session
from websockets.exceptions import ConnectionClosedOK

from ataka.common import queue, database
from ataka.common.database.models import Job, Target, Flag
from ataka.common.queue.output import OutputMessage, OutputQueue
from ataka.web.schemas import FlagSubmission
from ataka.web.state import GlobalState
from ataka.web.websocket_handlers import handle_incoming, handle_websocket_connection

app = FastAPI()
state: GlobalState


@app.on_event("startup")
async def startup_event():
    global state
    await queue.connect()
    await database.connect()

    state = await GlobalState.get()


@app.on_event("shutdown")
async def shutdown_event():
    await state.close()

    await queue.disconnect()
    await database.disconnect()


async def get_session():
    async with database.get_session() as session:
        yield session


def get_channel():
    return state.global_channel


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
async def all_flags():
    # TODO
    return []


@app.get("/api/services")
async def all_flags():
    if state.ctf_config is None:
        return []
    return state.ctf_config["services"]


@app.get("/api/init")
async def get_init_data():
    return {
        "ctf_config": state.ctf_config,
        "exploits": state.exploits,
    }


@app.post("/api/flag/submit")
async def submit_flag(submission: FlagSubmission, session: Session = Depends(get_session),
                      channel=Depends(get_channel)):
    expected_flags = len(re.findall(state.ctf_config["flag_regex"], submission.flags))

    manual_id = random.randint(0, 2 ** 31)

    results = []

    async def listen_for_responses():
        try:
            async for message in state.flag_notify_queue.wait_for_messages():
                if message.manual_id == manual_id:
                    results.append(message.flag_id)

                    if len(results) == expected_flags:
                        break
        except CancelledError:
            pass

    task = asyncio.create_task(listen_for_responses())

    output_message = OutputMessage(manual_id=manual_id, execution_id=None, stdout=True, output=submission.flags)
    output_queue = await OutputQueue.get(channel)
    await output_queue.send_message(output_message)

    try:
        await asyncio.wait_for(task, 3)
    except TimeoutError:
        pass

    if len(results) == 0:
        return []

    get_result_flags = select(Flag).where(Flag.id.in_(results))
    flags = (await session.execute(get_result_flags)).scalars()

    return [x.to_dict() for x in flags]


@app.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket, channel=Depends(get_channel)):
    await websocket.accept()

    try:
        await handle_websocket_connection(websocket, channel)
    except WebSocketDisconnect:
        pass
    except ConnectionClosedOK:
        pass
