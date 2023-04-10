import asyncio
import collections
import itertools
import ipaddress

import networkx as nx

import network
from net_io_helpers import IOHelper
from constants_and_variables import main_logger


async def main_loop(graph: nx.Graph, id_to_ips: dict[int, dict[str, list[str]]], id_to_client: dict[int, IOHelper],
                    save_file: bool = False):
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
        node_deque = collections.deque()
        node_deque.append(n1)
        while len(node_deque) != 0:
            prev_node = node_deque.popleft()
            for next_node in graph.neighbors(prev_node):
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

    l_nodes = dict(filter(lambda x: x[1].get("type", "") == "link", graph.nodes(data=True)))
    m_nodes = dict(filter(lambda x: x[1].get("type", "") == "machine", graph.nodes(data=True)))

    m_only_edges = []
    other_edges = []
    for edge in graph.edges():
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
        node_deque = collections.deque()
        node_deque.extend(graph.neighbors(cur_team_links[0]))
        while len(node_deque) != 0:
            node = node_deque.popleft()
            if node in l_nodes:  # this is net link
                if node not in cur_team_links:
                    cur_team_links.append(node)
                    node_deque.extend(graph.neighbors(node))
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
        nx.write_gml(graph, "measured.gml")
