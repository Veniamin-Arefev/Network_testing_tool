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
arg_parser.add_argument("--action", nargs="?", choices=["measure", "run_vms"], default="client",
                        help="Type of action to perform. Measure physical topology or create virtual network from virtual machines")
arg_parser.add_argument("--phys_graph", nargs="?", type=pathlib.Path, help="Physical topology file")
arg_parser.add_argument("--vm_graph", nargs="?", type=pathlib.Path, default=None,
                        help="Virtual topology and mapping file")

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
        if args.action is None:
            print("Missing action for server. Please supply one.")
            exit(1)

        if args.phys_graph is None:
            print("Missing physical topology file")
            exit(1)

        if args.vm_graph is None and args.action == "run_vms":
            print("Missing virtual topology file with mapping")
            exit(1)

        asyncio.run(network.main_server(phys_graph_path=args.phys_graph,
                                        vm_mapping_graph_path=args.vm_graph,
                                        cur_action=args.action))

except (KeyboardInterrupt, Exception):
    for proc in psutil.Process().children():
        proc.kill()
        proc.wait()
    print("Interrupt by keyboard")
