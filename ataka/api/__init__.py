import os
import base64
import binascii
from datetime import datetime

import asyncio
import random
import re
from asyncio import CancelledError

from typing import Set
from fastapi import FastAPI, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload, Session
from sqlalchemy.exc import IntegrityError, NoResultFound

from ataka.common import queue, database
from ataka.common.database.models import Job, Target, Flag, Execution, ExploitHistory, Exploit, Exclusion
from ataka.common.queue.output import OutputMessage, OutputQueue
from ataka.api.schemas import FlagSubmission
from ataka.api.state import GlobalState

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


@app.get("/")
async def get_playercli(session: Session = Depends(get_session)):
    return FileResponse(path="/data/shared/ataka-player-cli.pyz", filename="ataka-player-cli.pyz")


@app.get("/api/targets")
async def all_targets(session: Session = Depends(get_session)):
    get_max_version = select(func.max(Target.version))
    version = (await session.execute(get_max_version)).scalar_one()

    get_targets = select(Target).where(Target.version == version)
    target_objs = (await session.execute(get_targets)).scalars()
    targets = [x.to_dict() for x in target_objs]

    return targets


@app.get("/api/targets/service/{service_name}")
async def targets_by_service(service_name, session: Session = Depends(get_session)):
    get_max_version = select(func.max(Target.version))
    version = (await session.execute(get_max_version)).scalar_one()

    get_targets = select(Target).where(Target.service == service_name).where(Target.version == version)
    target_objs = (await session.execute(get_targets)).scalars()
    targets = [x.to_dict() for x in target_objs]

    return targets


@app.get("/api/targets/ip/{ip_addr}")
async def targets_by_ip(ip_addr, session: Session = Depends(get_session)):
    get_max_version = select(func.max(Target.version))
    version = (await session.execute(get_max_version)).scalar_one()

    get_targets = select(Target).where(Target.ip == ip_addr).where(Target.version == version)
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
    job_obj = (await session.execute(get_jobs)).scalar_one()

    return job_obj.to_dict()


@app.get("/api/flags")
async def all_flags(
    start: datetime | None = None,
    stop: datetime | None = None,
    session: Session = Depends(get_session),
):
    get_flags = select(Flag, Execution, Target, Job, Exploit)

    if start is not None:
        get_flags = get_flags.filter(Flag.timestamp >= start)
    if stop is not None:
        get_flags = get_flags.filter(Flag.timestamp <= stop)

    get_flags = (
        get_flags.join(Execution, Flag.execution_id == Execution.id)
        .join(Target, Execution.target_id == Target.id)
        .join(Job, Execution.job_id == Job.id)
        .join(Exploit, Job.exploit_id == Exploit.id)
    )

    flags = (await session.execute(get_flags)).all()
    flags = [
        {
            "flag": fl.to_dict(),
            "execution": ex.to_dict(),
            "target": ta.to_dict(),
            "job": jo.to_dict(),
            "exploit": exp.to_dict(),
        }
        for fl, ex, ta, jo, exp in flags
    ]

    return flags


@app.get("/api/services")
async def all_services():
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
        await asyncio.wait_for(task, 10)
    except TimeoutError:
        pass

    if len(results) == 0:
        return []

    get_result_flags = select(Flag).where(Flag.id.in_(results))
    flags = (await session.execute(get_result_flags)).scalars()

    return [x.to_dict() for x in flags]


@app.get("/api/exploit_history")
async def exploit_history_list(session: Session = Depends(get_session)):
    get_histories = select(ExploitHistory)
    histories = (await session.execute(get_histories)).scalars()
    return [x.to_dict() for x in histories]


class ExploitHistoryCreateRequest(BaseModel):
    history_id: str
    service: str


@app.post("/api/exploit_history")
async def exploit_history_create(req: ExploitHistoryCreateRequest,
                                 session: Session = Depends(get_session)):
    if state.ctf_config is None or req.service not in state.ctf_config["services"]:
        return {"success": False, "error": "Unknown service"}

    history = ExploitHistory(id=req.history_id, service=req.service)
    session.add(history)
    try:
        await session.commit()
    except IntegrityError:
        return {"success": False, "error": "History already exists"}

    return {"success": True, "error": ""}

@app.get("/api/exploit_history/{history_id}")
async def exploit_history_get(
        history_id: str,
        session: Session = Depends(get_session)
):
    get_history = select(ExploitHistory) \
        .where(ExploitHistory.id == history_id);
    try:
        history = (await session.execute(get_history)).scalar_one()
    except NoResultFound:
        return {"success": False, "error": "History does not exist"}

    return {
        "success": True,
        "error": "",
        "history": history.to_dict(),
    }


@app.get("/api/exploit_history/{history_id}/exclusions")
async def exploit_history_get_exclusions(
        history_id: str,
        session: Session = Depends(get_session)
):
    get_history = select(ExploitHistory) \
        .where(ExploitHistory.id == history_id) \
        .options(selectinload(ExploitHistory.exclusions))
    try:
        history = (await session.execute(get_history)).scalar_one()
    except NoResultFound:
        return {"success": False, "error": "History does not exist"}

    return {
        "success": True,
        "error": "",
        "target_ips": [x.target_ip for x in history.exclusions]
    }


class ExclusionsPutRequest(BaseModel):
    target_ips: Set[str]


@app.put("/api/exploit_history/{history_id}/exclusions")
async def exploit_history_put_exclusions(
        history_id: str,
        req: ExclusionsPutRequest,
        session: Session = Depends(get_session)
):
    get_history = select(ExploitHistory) \
        .where(ExploitHistory.id == history_id) \
        .options(selectinload(ExploitHistory.exclusions))
    try:
        history = (await session.execute(get_history)).scalar_one()
    except NoResultFound:
        return {"success": False, "error": "History does not exist"}

    cur_ips = set(x.target_ip for x in history.exclusions)

    session.begin()
    try:
        for ip in req.target_ips:
            if ip not in cur_ips:
                excl = Exclusion(exploit_history_id=history_id, target_ip=ip)
                session.add(excl)
        for excl in history.exclusions:
            if excl.target_ip not in req.target_ips:
                await session.delete(excl)
        await session.commit()
    except:
        await session.rollback()
        raise

    return {"success": True, "error": ""}


@app.get("/api/exploit")
async def exploit_all(session: Session = Depends(get_session)):
    get_exploits = select(Exploit)
    exploits = (await session.execute(get_exploits)).scalars()
    return [x.to_dict() for x in exploits]


class ExploitCreateRequest(BaseModel):
    history_id: str
    author: str
    context: str


@app.post("/api/exploit")
async def exploit_create(req: ExploitCreateRequest,
                         session: Session = Depends(get_session)):
    try:
        context = base64.b64decode(req.context)
    except binascii.Error:
        return {"success": False, "error": "Invalid Docker context encoding"}

    get_history = select(ExploitHistory) \
        .where(ExploitHistory.id == req.history_id) \
        .options(selectinload(ExploitHistory.exploits))
    try:
        history = (await session.execute(get_history)).scalar_one()
    except NoResultFound:
        return {"success": False, "error": "History does not exist"}

    max_idx = 0
    prefix = req.history_id + '-'
    for exploit in history.exploits:
        if exploit.id.startswith(prefix):
            try:
                idx = int(exploit.id[len(prefix):])
            except ValueError:
                continue
            max_idx = max(max_idx, idx)
    exploit_id = f'{prefix}{max_idx + 1}'

    ctx_path = f"/data/exploits/{exploit_id}"
    excl_opener = lambda path, flags: os.open(path, flags | os.O_EXCL)
    try:
        with open(ctx_path, "wb", opener=excl_opener) as f:
            f.write(context)
    except FileExistsError:
        return {"success": False, "error": "Exploit already exists (file)"}

    exploit = Exploit(id=exploit_id, exploit_history_id=req.history_id,
                      active=False, author=req.author)
    session.add(exploit)
    try:
        await session.commit()
    except IntegrityError:
        return {"success": False, "error": "Exploit already exists (db)"}

    return {"success": True, "error": "", "exploit_id": exploit_id}


class ExploitPatchRequest(BaseModel):
    active: bool


@app.patch("/api/exploit/{exploit_id}")
async def exploit_patch(exploit_id: str, req: ExploitPatchRequest,
                        session: Session = Depends(get_session)):
    get_exploit = select(Exploit).where(Exploit.id == exploit_id)
    try:
        exploit = (await session.execute(get_exploit)).scalar_one()
    except NoResultFound:
        return {"success": False, "error": "Exploit does not exist"}

    exploit.active = req.active
    await session.commit()

    return {"success": True, "error": ""}


@app.get("/api/exploit/{exploit_id}/jobs")
async def exploit_jobs(exploit_id: str, limit: int = 1, start: int = 0,
                       session: Session = Depends(get_session)):
    get_jobs = select(Job) \
        .where((Job.exploit_id == exploit_id) & (Job.id >= start)) \
        .order_by(Job.timestamp.desc()) \
        .limit(limit) \
        .options(
        selectinload(Job.executions).selectinload(Execution.target))
    jobs = (await session.execute(get_jobs)).scalars()

    return [
        {
            "job": job.to_dict(),
            "executions": [x.to_dict() for x in job.executions],
            "targets": [x.target.to_dict() for x in job.executions],
        }
        for job in jobs
    ]


@app.get("/api/exploit/{exploit_id}/download")
async def exploit_download(exploit_id: str,
                           session: Session = Depends(get_session)):
    get_exploit = select(Exploit).where(Exploit.id == exploit_id)
    try:
        (await session.execute(get_exploit)).scalar_one()
    except NoResultFound:
        return {"success": False, "error": "Exploit does not exist"}

    ctx_path = f"/data/exploits/{exploit_id}"
    with open(ctx_path, "rb") as f:
        data = f.read()

    return {"success": True, "error": "", "data": base64.b64encode(data).decode()}
