import asyncio
import os
import sys
import websockets

from grammar import grammar, TinyTalkVisitor
import interpreter

IP_ADDRESS = "localhost"
PORT = 8765
APP_FILE = "app.txt"
last_upload = -sys.maxsize

visitor = TinyTalkVisitor()
scene = {}


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
    new_object = await websocket.recv()
    
    global last_upload
    if os.path.getmtime(APP_FILE) > last_upload:
        with open(APP_FILE, "r") as f:
            apps = f.read().split("\n\n")
            for app in apps:
                app_json = visitor.visit(grammar.parse(app))
                interpreter.load_app(app_json)

        last_upload = os.path.getmtime(APP_FILE)

    if new_object["id"] in scene:
        interpreter.update(new_object["id"], new_object, scene)
    else:
        interpreter.create(new_object["id"], new_object, scene)

    await websocket.send(format_scene(scene))


start_server = websockets.serve(tinyland_loop, IP_ADDRESS, PORT)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()