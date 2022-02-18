from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.future import select
from sqlalchemy.orm import Session

from ataka.common import queue, database
from ataka.common.database.models import Job
from ataka.common.queue import ControlQueue

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


@app.get("/test")
async def test(session: Session = Depends(get_session)):
    get_jobs = select(Job)
    job_objs = (await session.execute(get_jobs)).scalars()
    jobs = [x.to_dict() for x in job_objs]

    return jobs


@app.websocket("/queue")
async def websocket_endpoint(websocket: WebSocket, channel=Depends(get_channel)):
    await websocket.accept()

    try:
        control_queue = await ControlQueue.get(channel)

        async for message in control_queue.wait_for_messages():
            await websocket.send_text(message.to_bytes().decode())
    except WebSocketDisconnect:
        print("disconnected")
