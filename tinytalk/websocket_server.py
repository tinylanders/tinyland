import asyncio
import json
import os
import parsimonious
import queue
import socket
import sys
import websockets

from grammar import grammar, TinyTalkVisitor
import interpreter

BUFFER_SIZE = 1024
IP_ADDRESS = "127.0.0.1"
UDP_PORT = 8766
WEBSOCKET_PORT = 8765
APP_FILE = "app.txt"
last_upload = -sys.maxsize

visitor = TinyTalkVisitor()
scene = {}
q = queue.Queue(64)


def format_scene(scene):
    formatted_scene = {
        "appMarkers": {},
        "virtualObjects": {},
    }
    for key, val in scene.items():
        if "marker" in val["tags"]:
            formatted_scene["appMarkers"][key] = val
        else:
            formatted_scene["virtualObjects"][key] = val
    return formatted_scene


async def tinyland_loop(websocket, path):
    # global sock
    data = q.get(True)
    new_object = json.loads(data.decode("utf-8"))
    
    global last_upload
    global scene
    if os.path.getmtime(APP_FILE) > last_upload:
        with open(APP_FILE, "r") as f:
            apps = f.read().split("\n\n")
            for app in apps:
                try:
                    app_json = visitor.visit(grammar.parse(app))
                except parsimonious.exceptions.ParseError as e:
                    #TODO: add bad app error handling
                    pass
                else:
                    print(f"Loading app {app_json}")
                    interpreter.load_app(app_json)

        last_upload = os.path.getmtime(APP_FILE)

    if new_object["id"] in scene:
        interpreter.update(new_object["id"], new_object, scene)
    else:
        interpreter.create(new_object["id"], new_object, scene)

    await websocket.send(json.dumps(format_scene(scene)))


async def udp_listener():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((IP_ADDRESS, UDP_PORT))
    while True:
        data, _addr = sock.recvfrom(1024)
        print(data)
        q.put(data, True)
        await asyncio.sleep(0.5)


start_server = websockets.serve(tinyland_loop, IP_ADDRESS, WEBSOCKET_PORT)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().create_task(udp_listener())
asyncio.get_event_loop().run_forever()