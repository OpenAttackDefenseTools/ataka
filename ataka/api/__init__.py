from fastapi import FastAPI, Depends, APIRouter
from fastapi.responses import FileResponse

from ataka.api.routers import targets, exploit_history, exploit, flag, job
from ataka.api.dependencies import get_session, get_channel
from ataka.common import queue, database

app = FastAPI()

api = APIRouter(prefix="/api")
api.include_router(targets.router)
api.include_router(exploit_history.router)
api.include_router(exploit.router)
api.include_router(flag.router)
api.include_router(job.router)

@app.on_event("startup")
async def startup_event():
    await queue.connect()
    await database.connect()


@app.on_event("shutdown")
async def shutdown_event():
    await queue.disconnect()
    await database.disconnect()


@app.get("/")
async def get_playercli():
    return FileResponse(path="/data/shared/ataka-player-cli.pyz", filename="ataka-player-cli.pyz")

app.include_router(api)
