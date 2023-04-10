import argparse
import asyncio
import pathlib

import network
from constants_and_variables import set_up_logger

arg_parser = argparse.ArgumentParser(prog="Net-tester", description="Test network speed for multiple hosts")

arg_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

arg_parser.add_argument("type", choices=["client", "server"], default="client", help="Type of this node")

arg_parser.add_argument("hostname", help="Name of this node")

# client
arg_parser.add_argument("--host", nargs="?", help="Server ip")
# server
arg_parser.add_argument("--graph", nargs="?", type=pathlib.Path, help="Topology file")

args = arg_parser.parse_args()

set_up_logger()

try:
    if args.type == "client":
        if args.host is None:
            print("Missing host ip")
            exit(1)

        asyncio.run(network.main_client(args.hostname, args.host))

    elif args.type == "server":
        if args.graph is None:
            print("Missing topology file")
            # exit(1)

        asyncio.run(network.main_server(args.graph))

except KeyboardInterrupt:
    print("Interrupt by keyboard")
