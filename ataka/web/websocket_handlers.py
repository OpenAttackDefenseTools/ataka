import asyncio

from fastapi import WebSocket
from ataka.common.queue import ControlQueue, FlagNotifyQueue, ControlAction


def handle_websocket_connection(websocket: WebSocket, channel):
    return asyncio.gather(
        listen_flags(websocket, channel),
        listen_control_messages(websocket, channel),
        provide_heartbeat(websocket),
        handle_incoming(websocket),
    )


async def listen_flags(websocket: WebSocket, channel):
    # TODO: not necessary
    flag_notify = await FlagNotifyQueue.get(channel)

    async for message in flag_notify.wait_for_messages():
        await websocket.send_json({"type": "flag", "body": message.to_bytes().decode()})


async def listen_control_messages(websocket: WebSocket, channel):
    control_queue = await ControlQueue.get(channel)

    async for message in control_queue.wait_for_messages():
        if message.action in (ControlAction.CTF_CONFIG_UPDATE,):
            await websocket.send_json({"type": "control", "body": message.to_dict()})


async def provide_heartbeat(websocket: WebSocket):
    while True:
        await asyncio.sleep(5)
        await websocket.send_json({"type": "heartbeat", "body": {}})


async def handle_incoming(websocket: WebSocket):
    async for message in websocket.iter_json():
        if "type" not in message or message["type"] not in handlers:
            print("got invalid websocket message", message)
            continue

        handlers[message["type"]](message)


handlers = dict()


def websocket_handler(func):
    if func.__name__ in handlers:
        raise ValueError("multiple websocket handlers with the name '" + func.__name__ + "'")
    handlers[func.__name__] = func

    return func


@websocket_handler
def heartbeat(_):
    print("gotten heartbeat")
    pass
