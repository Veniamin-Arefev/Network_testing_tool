import ast
import asyncio
import itertools
import ipaddress
from collections import defaultdict, deque

import networkx as nx

import network
from net_io_helpers import IOHelper
from constants_and_variables import main_logger

SPEED_RATIO = 2
DELAY_BIAS = 1.5


async def main_loop(phys_graph: nx.Graph, vm_mapping_graph: nx.Graph,
                    id_to_ips: dict[int, dict[str, list[str]]], id_to_client: dict[int, IOHelper],
                    hostname_to_id: dict[str, int], action: str, save_file: bool = False):
    def get_networks_for_nodes(nodes: list[int], excluded_nets: list = None):
        cur_networks = sum([
            [
                ipaddress.IPv4Network(f"{addr[0]}/{addr[1]}", strict=False) for NIC, addr in id_to_ips[node_id].items()
            ]
            for node_id in nodes
        ], [])
        if excluded_nets is not None:
            cur_networks = list(filter(lambda x: x not in excluded_nets, cur_networks))
        return cur_networks

    def get_node_ip_in_network(node_id: int, net: ipaddress.IPv4Network):
        ips = [ipaddress.ip_address(addr[0]) for NIC, addr in id_to_ips[node_id].items()]
        for ip in ips:
            if ip in net:
                return ip

    async def test_speed_direct(n1, n2, excluded_nets):
        cur_net = get_networks_for_nodes([n1, n2], excluded_nets)[0]
        nodes = [n1, n2]
        target = get_node_ip_in_network(n2, cur_net)

        # return n1 * 1000 + n2 + 0.0001, cur_net, nodes
        await network.send_measure(id_to_client[n1], target=str(target), nodes=nodes)
        await asyncio.sleep(35)

    async def test_speed_in_net(n1, n2, net, links):
        cur_net = net
        nodes = get_link_path_nodes(n1, n2, links)
        target = get_node_ip_in_network(n2, cur_net)
        # return n1 * 1000 + n2 + 0.0001, cur_net, nodes

        await network.send_measure(id_to_client[n1], target=str(target), nodes=nodes)
        await asyncio.sleep(35)

    def get_link_path_nodes(n1, n2, links):
        min_dist = {n1: 0}
        prev_dict = dict()
        node_deque = deque()
        node_deque.append(n1)
        while len(node_deque) != 0:
            prev_node = node_deque.popleft()
            for next_node in phys_graph.neighbors(prev_node):
                if next_node == n2 and prev_node != n1:
                    if n2 not in min_dist or min_dist[n2] > min_dist[prev_node] + 1:
                        min_dist[n2] = min_dist[prev_node] + 1
                        prev_dict[n2] = prev_node
                if next_node in links:
                    if next_node not in min_dist:
                        min_dist[next_node] = min_dist[prev_node] + 1
                        prev_dict[next_node] = prev_node
                        node_deque.append(next_node)
        path_nodes = [n2]
        while len(path_nodes) != min_dist[n2] + 1:
            path_nodes.append(prev_dict[path_nodes[-1]])
        return path_nodes

    l_nodes = dict(filter(lambda x: x[1].get("type", "") == "link", phys_graph.nodes(data=True)))
    m_nodes = dict(filter(lambda x: x[1].get("type", "") == "machine", phys_graph.nodes(data=True)))

    m_only_edges = []
    other_edges = []
    for edge in phys_graph.edges():
        n1, n2 = edge
        if n1 in m_nodes and n2 in m_nodes:
            m_only_edges.append(edge)
        else:
            other_edges.append(edge)

    # group all nested links into teams and then perform full-mesh measure to all nodes in teams
    l_nodes_to_pop = list(l_nodes.keys())
    teams: list[tuple[list, list]] = []

    while len(l_nodes_to_pop) != 0:
        cur_team_links = [l_nodes_to_pop.pop()]
        cur_team_machines = []
        node_deque = deque()
        node_deque.extend(phys_graph.neighbors(cur_team_links[0]))
        while len(node_deque) != 0:
            node = node_deque.popleft()
            if node in l_nodes:  # this is net link
                if node not in cur_team_links:
                    cur_team_links.append(node)
                    node_deque.extend(phys_graph.neighbors(node))
                if node in l_nodes_to_pop:
                    l_nodes_to_pop.remove(node)
            elif node in m_nodes:
                if node not in cur_team_machines:
                    cur_team_machines.append(node)
        teams.append((cur_team_links, cur_team_machines,))

    teams_nets = []

    for team in teams:
        cur_l_nodes, cur_m_nodes = team
        cur_networks = get_networks_for_nodes(cur_m_nodes)

        cur_team_network = None
        for net in cur_networks:
            if all([
                any(
                    [ipaddress.ip_address(addr[0]) in net for NIC, addr in id_to_ips[node_id].items()]
                ) for node_id in cur_m_nodes
            ]):
                cur_team_network = net
                break
        if cur_team_network is None:
            print("NETWORK DISCOVERY ERROR OCCURRED!")
        teams_nets.append(cur_team_network)

    if action == "measure":
        main_logger.info("Started measurement")
        # actual testing for teams
        for team_index, team in enumerate(teams):
            cur_team_links, cur_team_machines = team
            for n1, n2 in itertools.combinations(cur_team_machines, 2):
                await test_speed_in_net(n1, n2, teams_nets[team_index], cur_team_links)

        # can test m_only and write to graph
        for n1, n2 in m_only_edges:
            await test_speed_direct(n1, n2, teams_nets)

        main_logger.info("Done measurement")
        if save_file:
            nx.write_gml(phys_graph, "measured.gml")

    if action == "run_vms":
        main_logger.info("Perform mapping checks")

        phys_to_vms_id: defaultdict[int, list] = defaultdict(list)
        vm_id_to_vm_nets = defaultdict(list)

        vms_to_go = deque()
        done_vms = []
        vms_to_go.append([*vm_mapping_graph.nodes()][0])

        port_iterator = 50_000

        is_error_occurred: bool = False
        while len(vms_to_go) != 0 and not is_error_occurred:
            cur_vm = vms_to_go.popleft()
            for new_vm in vm_mapping_graph.neighbors(cur_vm):
                if new_vm in done_vms:
                    continue
                nodes = ast.literal_eval(vm_mapping_graph[cur_vm][new_vm]["phys_hosts"])
                speed = vm_mapping_graph[cur_vm][new_vm]["speed"]
                delay = vm_mapping_graph[cur_vm][new_vm]["delay"]

                if len(nodes) == 1:
                    # localhost connection
                    cur_vm_ip = "127.0.0.1"
                    new_vm_ip = "127.0.0.1"
                    speed = speed
                    delay = delay

                elif len(nodes) == 2:
                    # direct connection
                    phys_node_ids = list(map(lambda x: hostname_to_id[x], nodes))
                    # get net for current machines exclude all link nets
                    cur_net = get_networks_for_nodes(phys_node_ids, teams_nets)[0]

                    # get physical host ids
                    cur_vm_host_id = hostname_to_id[vm_mapping_graph.nodes[cur_vm]["phys_hostname"]]
                    new_vm_host_id = hostname_to_id[vm_mapping_graph.nodes[new_vm]["phys_hostname"]]

                    cur_vm_ip = get_node_ip_in_network(cur_vm_host_id, cur_net)
                    new_vm_ip = get_node_ip_in_network(new_vm_host_id, cur_net)

                    # check limits
                    max_speed = phys_graph[cur_vm_host_id][new_vm_host_id]["speed"]
                    used_speed = phys_graph[cur_vm_host_id][new_vm_host_id].get("used_speed", 0)
                    if speed * SPEED_RATIO + used_speed > max_speed:
                        is_error_occurred = True
                        main_logger.error(f"Bandwidth limit exceeded for virtual edge: {cur_vm} and {new_vm}")
                        break
                    phys_graph[cur_vm_host_id][new_vm_host_id]["used_speed"] = speed * SPEED_RATIO + used_speed

                    path_delay = phys_graph[cur_vm_host_id][new_vm_host_id]["delay"]
                    if path_delay + DELAY_BIAS > delay:
                        is_error_occurred = True
                        main_logger.error(f"The delay condition cannot be met for {cur_vm} and {new_vm}")
                        break

                    speed = speed
                    delay = delay - path_delay - DELAY_BIAS
                else:
                    # connection via links
                    # direct connection
                    phys_node_ids = list(map(lambda x: hostname_to_id[x], nodes))
                    link_ids = phys_node_ids[1:-1]

                    cur_team_index = None
                    for index, team in enumerate(teams):
                        cur_l_nodes, cur_m_nodes = team
                        if link_ids in cur_l_nodes:
                            cur_team_index = index
                            break
                    if cur_team_index is None:
                        main_logger.error(f"Network not found for nodes {phys_node_ids}")
                        is_error_occurred = True
                        break

                    # get net for current links
                    cur_net = teams_nets[cur_team_index]

                    # get physical host ids
                    cur_vm_host_id = hostname_to_id[vm_mapping_graph.nodes[cur_vm]["phys_hostname"]]
                    new_vm_host_id = hostname_to_id[vm_mapping_graph.nodes[new_vm]["phys_hostname"]]

                    cur_vm_ip = get_node_ip_in_network(cur_vm_host_id, cur_net)
                    new_vm_ip = get_node_ip_in_network(new_vm_host_id, cur_net)

                    # check limits
                    for i in range(len(phys_node_ids) - 1):
                        # phys_graph[phys_node_ids[i]][phys_node_ids[i + 1]]
                        max_speed = phys_graph[phys_node_ids[i]][phys_node_ids[i + 1]]["speed"]
                        used_speed = phys_graph[phys_node_ids[i]][phys_node_ids[i + 1]].get("used_speed", 0)
                        if speed * SPEED_RATIO + used_speed > max_speed:
                            is_error_occurred = True
                            main_logger.error(f"Bandwidth limit exceeded for virtual edge: {cur_vm} and {new_vm}")
                            break
                        phys_graph[phys_node_ids[i]][phys_node_ids[i + 1]]["used_speed"] = speed * SPEED_RATIO + used_speed


                    path_delay = sum([phys_graph[phys_node_ids[i]][phys_node_ids[i + 1]]["delay"]
                                      for i in range(len(phys_node_ids) - 1)])
                    if path_delay + DELAY_BIAS > delay:
                        is_error_occurred = True
                        main_logger.error(f"The delay condition cannot be met for {cur_vm} and {new_vm}")
                        break

                    speed = speed
                    delay = delay - path_delay - DELAY_BIAS

                port = port_iterator
                port_iterator += 1

                # source, local, port, speed, delay
                vm_id_to_vm_nets[cur_vm].append((new_vm_ip, cur_vm_ip, port, speed, delay,))
                vm_id_to_vm_nets[new_vm].append((cur_vm_ip, new_vm_ip, port, speed, delay,))

            phys_id = hostname_to_id[vm_mapping_graph.nodes[cur_vm]["phys_hostname"]]
            phys_to_vms_id[phys_id].append(cur_vm)

            done_vms.append(cur_vm)
        if not is_error_occurred:
            main_logger.info("Creating VMs")

            for phys_id, vm_ids in phys_to_vms_id.items():
                hostnames = [vm_mapping_graph.nodes[vm_id]["hostname"] for vm_id in vm_ids]
                # list of vm_net_configs
                nets = [vm_id_to_vm_nets[vm_id] for vm_id in vm_ids]

                await network.send_start_vms(id_to_client[phys_id], hostnames=hostnames, nets=nets)

            main_logger.info("VMs created.")
