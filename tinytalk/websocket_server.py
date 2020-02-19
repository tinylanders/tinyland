import argparse
import asyncio
import json
import logging
import os
import parsimonious
import queue
import socket
import sys
import websockets

from pythonosc import osc_server
from pythonosc import dispatcher

from grammar import grammar, TinyTalkVisitor
from scene import TinylandScene


IP_ADDRESS = "127.0.0.1"
UDP_PORT = 8766
WEBSOCKET_PORT = 1234
APP_FILE = "app.txt"
last_upload = -sys.maxsize

visitor = TinyTalkVisitor()
udp_msg = None


def format_scene(scene):
    return {"type": "render", "payload": scene}


class WebsocketServer:
    def __init__(self, ip_address, port):
        self.ip_address = ip_address
        self.port = port
        self.scene = TinylandScene()

    def reload_apps(self, filepath):
        with open(filepath, "r") as f:
            apps_string = f.read()
            try:
                apps_json = visitor.visit(grammar.parse(apps_string.strip()))
            except parsimonious.exceptions.ParseError as e:
                logging.error(f"Could not parse app {apps_string}: {e}")
            else:
                for app in apps_json:
                    logging.info(f"Loading app {app} from {filepath}")
                    self.scene.load_app(app)

    def start(self):
        logging.info(f"Starting WebSocket Server on {self.ip_address}:{self.port}")
        return websockets.serve(self.tinyland_loop, self.ip_address, self.port)

    async def tinyland_loop(self, websocket, path):
        while True:
            global last_upload
            global udp_msg

            # See if we've gotten an update over UDP
            if udp_msg is not None:
                new_object = udp_msg
                print(new_object)
                if new_object["id"] in self.scene.scene:
                    self.scene.update(new_object["id"], new_object)
                else:
                    self.scene.create(new_object["id"], new_object)
                udp_msg = None

            if os.path.getmtime(APP_FILE) > last_upload:
                self.reload_apps(APP_FILE)
                last_upload = os.path.getmtime(APP_FILE)

            if self.scene.execute_loop():
                logging.debug(f"Scene: {self.scene.scene}")
                await websocket.send(json.dumps(format_scene(self.scene.scene)))
            await asyncio.sleep(0.01)


def get_udp_server(ip_address, port):
    def unknown_handler(addr, *args):
        logging.debug("Unknown stuff: {} {}".format(addr, args))

    def marker_handler(addr, *args):
        global udp_msg
        if args[0] == "set":
            marker = {
                    "tags": ["marker"],
                    "type": "marker",
                    "id": args[2],
                    "x": args[3],
                    "y": args[4],
                    "a": args[5]
            }
            udp_msg = marker
            logging.debug(f"Marker: {marker}")

    disp = dispatcher.Dispatcher()
    disp.map('/tuio/2Dobj', marker_handler)
    disp.set_default_handler(unknown_handler)

    server = osc_server.AsyncIOOSCUDPServer(
        (args.ip_address, args.udp_port),
        disp,
        asyncio.get_event_loop())
    return server

            
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-i", "--ip_address", default=IP_ADDRESS, type=str, help="IP address to run on."
    )
    parser.add_argument(
        "-p",
        "--websocket_port",
        default=WEBSOCKET_PORT,
        type=int,
        help="Port to send websocket packets to.",
    )
    parser.add_argument(
        "-u",
        "--udp_port",
        default=UDP_PORT,
        type=int,
        help="Port to receive UDP messages from.",
    )
    parser.add_argument(
        "-v", "--verbose", action="count", default=0, help="Verbosity level."
    )

    args, unknown = parser.parse_known_args(sys.argv[1:])

    if args.verbose == 1:
        logging.getLogger().setLevel(logging.INFO)
    elif args.verbose > 1:
        logging.getLogger().setLevel(logging.DEBUG)

    ws = WebsocketServer(args.ip_address, args.websocket_port)
    udp = get_udp_server(args.ip_address, args.udp_port)

    asyncio.get_event_loop().run_until_complete(ws.start())
    asyncio.get_event_loop().create_task(udp.create_serve_endpoint())
    asyncio.get_event_loop().run_forever()

