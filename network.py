import asyncio
import json
import pathlib
import socket

import networkx as nx
import psutil

import cmd_utility
import main_calculations
from constants_and_variables import *
from net_io_helpers import *

id_to_client: dict[int, IOHelper] = dict()
id_to_ips: dict[int, dict[str, list[str]]] = dict()

hostname_to_id: dict[str, int] = dict()
id_to_hostname: dict[int, str] = dict()

action: str
phys_graph: nx.Graph
vm_mapping_graph: nx.Graph


def parse_message_to_dict(message: str) -> dict:
    if len(message) > MESSAGE_MAX_LEN:
        main_logger.error(f"Received {len(message)} bytes, that is bigger that limit {MESSAGE_MAX_LEN}")
        message = message[:MESSAGE_MAX_LEN]
    return json.loads(message)


def get_str_from_dict(message_fields: dict) -> str:
    return json.dumps(message_fields)


async def send_dict(io_helper: IOHelper, my_dict: dict):
    await io_helper.send(get_str_from_dict(my_dict))


async def send_text_message(io_helper: IOHelper, message: str):
    message_fields = {"message_type": "info",
                      "text": message,
                      }
    await send_dict(io_helper, message_fields)


async def send_hello(io_helper: IOHelper, hostname: str):
    data: dict[str, tuple] = {}

    for NIC_name, value in psutil.net_if_addrs().items():
        for cur_add_info in value:
            if (cur_add_info.family != socket.AF_INET) or cur_add_info.address == "127.0.0.1":
                continue
            data[NIC_name] = (cur_add_info.address, cur_add_info.netmask)

    message_fields = {"message_type": "hello",
                      "hostname": hostname,
                      "ips": data,
                      }
    await send_dict(io_helper, message_fields)


async def send_measure(io_helper: IOHelper, target: str, nodes: list[int]):
    message_fields = {"message_type": "measure",
                      "target": target,
                      "nodes": nodes,
                      }
    await send_dict(io_helper, message_fields)


async def send_measure_answer(io_helper: IOHelper, nodes: list[int], speed: str, rtt: str):
    message_fields = {"message_type": "measure_answer",
                      "nodes": nodes,
                      "speed": speed,
                      "rtt": rtt,
                      }
    await send_dict(io_helper, message_fields)


async def send_start_vms(io_helper: IOHelper, hostnames: list[int], nets: list[list[tuple]]):
    message_fields = {"message_type": "start_vms",
                      "hostnames": hostnames,
                      "nets": nets,
                      }
    await send_dict(io_helper, message_fields)


async def try_to_run_main_loop():
    machine_nodes = list(filter(lambda x: x[1].get("type", "") == "machine", phys_graph.nodes(data=True)))
    if len(id_to_ips) == len(machine_nodes):
        asyncio.create_task(main_calculations.main_loop(
            phys_graph=phys_graph,
            vm_mapping_graph=vm_mapping_graph,
            id_to_ips=id_to_ips,
            id_to_client=id_to_client,
            hostname_to_id=hostname_to_id,
            action=action,
            save_file=True,
        ))


async def handle_connection_from_client(reader, writer):
    # client only
    remote_address = writer.get_extra_info("peername")
    remote_address_str = ":".join(map(str, remote_address))

    main_logger.info(f"Client connected from {remote_address}")

    io_helper: IOHelper = PlainIOHelper(reader, writer)
    client_id: int = None
    try:
        while True:
            data = await io_helper.receive()

            if data is None or len(data) == 0:
                break
            message: str = data.decode()
            main_logger.debug(f"Received {len(message):07} bytes from {remote_address_str}")
            main_logger.debug(f"Received {message!r} from {remote_address_str}")

            try:
                message_fields = parse_message_to_dict(message)

                match message_fields["message_type"]:
                    case "hello":
                        client_id = hostname_to_id[message_fields["hostname"]]

                        id_to_client[client_id] = io_helper
                        id_to_ips[client_id] = message_fields["ips"]

                        await try_to_run_main_loop()
                    case "measure_answer":
                        nodes = message_fields["nodes"]
                        speed = int(message_fields["speed"])
                        rtt = float(message_fields["rtt"])

                        delay_average = rtt / (len(nodes) - 1) / 2

                        for i in range(len(nodes) - 1):
                            cur_speed = phys_graph[nodes[i]][nodes[i + 1]].get("speed", 0)
                            if cur_speed < speed:
                                phys_graph[nodes[i]][nodes[i + 1]]["speed"] = speed

                            cur_delay = phys_graph[nodes[i]][nodes[i + 1]].get("delay", 0)
                            if cur_delay < delay_average:
                                phys_graph[nodes[i]][nodes[i + 1]]["delay"] = delay_average

                    case _:
                        raise ValueError("Bad message")

            except (ValueError, KeyError) as e:
                await send_text_message(io_helper, "The error has occurred:" + str(e))

            except (RuntimeError,) as e:
                await send_text_message(io_helper, str(e))
                break

    except asyncio.TimeoutError:
        main_logger.warning(f"Connection from {remote_address_str} timed out")
    except (ConnectionError,):
        main_logger.warning(f"Connection error with {remote_address_str}")
    main_logger.info(f"Close the connection with {remote_address_str}")
    writer.close()


async def handle_connection_to_server(reader, writer, hostname: str):
    main_logger.info(f"Connected to server")

    io_helper: IOHelper = PlainIOHelper(reader, writer)

    await send_hello(io_helper, hostname)

    try:
        while True:
            data = await io_helper.receive()

            if data is None or len(data) == 0:
                break
            message: str = data.decode()
            main_logger.debug(f"Received {len(message):07} bytes from server")
            main_logger.debug(f"Received {message!r} from server")

            try:
                message_fields = parse_message_to_dict(message)

                match message_fields["message_type"]:
                    case "measure":
                        target_ip = message_fields["target"]
                        nodes = message_fields["nodes"]
                        speed = cmd_utility.test_speed(target_ip)
                        delay = cmd_utility.test_rtt(target_ip)

                        await send_measure_answer(io_helper, nodes, speed, delay)
                    case "start_vms":
                        cmd_utility.prepare_for_vms()

                        hostnames = message_fields["hostnames"]
                        nets = message_fields["nets"]

                        for index in range(len(hostnames)):
                            cmd_utility.start_specific_vm(hostnames[index], nets[index])

                    case _:
                        raise ValueError("Bad message")

            except (ValueError, KeyError) as e:
                main_logger.debug(e)

            except (RuntimeError,) as e:
                main_logger.debug(e)

    except asyncio.TimeoutError:
        main_logger.warning(f"Connection from server timed out")
    except (ConnectionError,):
        main_logger.warning(f"Connection error with server")
    main_logger.info(f"Close the connection with server")
    writer.close()


async def main_server(phys_graph_path: pathlib.PosixPath, vm_mapping_graph_path: pathlib.PosixPath, cur_action: str):
    global action
    action = cur_action

    global phys_graph
    phys_graph = nx.read_gml(phys_graph_path, "id")

    global vm_mapping_graph
    vm_mapping_graph = nx.read_gml(vm_mapping_graph_path, "id") if vm_mapping_graph_path is not None else None

    for node_id, node_data in phys_graph.nodes(data=True):
        hostname_to_id[node_data["hostname"]] = node_id
        id_to_hostname[node_id] = node_data["hostname"]

    server_plain = await asyncio.start_server(handle_connection_from_client, host=HOST, port=PORT,
                                              family=socket.AF_INET)

    main_logger.info(f"Server started!")

    # wait for all
    await server_plain.wait_closed()


async def main_client(hostname: str, host: str):
    cmd_utility.start_server()

    reader, writer = await asyncio.open_connection(host=host, port=PORT, family=socket.AF_INET)

    # all other work would be done by server
    await handle_connection_to_server(reader, writer, hostname)

    cmd_utility.stop_server()

    main_logger.info(f"Servers started!")
