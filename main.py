import argparse
import asyncio
import pathlib

import psutil

import network
from constants_and_variables import set_up_logger

arg_parser = argparse.ArgumentParser(prog="Net-tester", description="Test network performance for multiple hosts")

arg_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

arg_parser.add_argument("type", choices=["client", "server"], default="client", help="Type of this node")

# client
arg_parser.add_argument("--hostname", nargs="?", help="Name of this node")
arg_parser.add_argument("--host", nargs="?", help="Server ip")
# server
arg_parser.add_argument("--phys_graph", nargs="?", type=pathlib.Path, help="Physical topology file")
arg_parser.add_argument("--vm_graph", nargs="?", type=pathlib.Path, help="Virtual topology and mapping file")

args = arg_parser.parse_args()

set_up_logger()

try:
    if args.type == "client":
        if args.hostname is None:
            print("Missing hostname")
            exit(1)

        if args.host is None:
            print("Missing host ip")
            exit(1)

        asyncio.run(network.main_client(args.hostname, args.host))

    elif args.type == "server":
        if args.phys_graph is None:
            print("Missing physical topology file")
            exit(1)

        if args.vm_graph is None:
            print("Missing virtual topology and mapping file")
            exit(1)

        asyncio.run(network.main_server(args.phys_graph, args.vm_graph))

except KeyboardInterrupt:
    for proc in psutil.Process().children():
        proc.kill()
        proc.wait()
    print("Interrupt by keyboard")
