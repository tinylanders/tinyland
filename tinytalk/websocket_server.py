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

from grammar import grammar, TinyTalkVisitor
from scene import TinylandScene


IP_ADDRESS = "127.0.0.1"
UDP_PORT = 8766
WEBSOCKET_PORT = 1234
APP_FILE = "app.txt"
last_upload = -sys.maxsize

visitor = TinyTalkVisitor()
udp_q = queue.Queue(64)


def format_scene(scene):
    return {"type": "render", "payload": scene}


class Server:
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

            # See if we've gotten an update over UDP
            if not udp_q.empty():
                data = udp_q.get(True)
                new_object = json.loads(data.decode("utf-8"))
                if new_object["id"] in self.scene.scene:
                    self.scene.update(new_object["id"], new_object)
                else:
                    self.scene.create(new_object["id"], new_object)

            if os.path.getmtime(APP_FILE) > last_upload:
                self.reload_apps(APP_FILE)
                last_upload = os.path.getmtime(APP_FILE)

            if self.scene.execute_loop():
                logging.debug(f"Scene: {self.scene.scene}")
                await websocket.send(json.dumps(format_scene(self.scene.scene)))
            await asyncio.sleep(0.01)


async def udp_listener(ip_address, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    logging.info(f"Started UDP listener on {ip_address}:{port}")
    sock.settimeout(0.01)
    sock.bind((ip_address, port))
    while True:
        try:
            data, _addr = sock.recvfrom(1024)
        except socket.timeout:
            await asyncio.sleep(0.01)
        else:
            logging.debug(f"UDP received: {data}")
            udp_q.put(data, True)
            await asyncio.sleep(0.01)


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

    ws = Server(args.ip_address, args.websocket_port)
    asyncio.get_event_loop().run_until_complete(ws.start())
    asyncio.get_event_loop().create_task(udp_listener(args.ip_address, args.udp_port))
    asyncio.get_event_loop().run_forever()
