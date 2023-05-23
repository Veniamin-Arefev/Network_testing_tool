# <center> **Network testing tool** </center>

#### Network testing tool is a tool for testing the performance of a physical network, as well as creating a virtual network from virtual machines.

This tool is designed to work on LAN topology with physical machines and switches. The physical network must be able to handle IP traffic and route it between nodes. All network routes must be symmetric, which means that the nodes through which the data packets pass must match. After measurements, you receive available bandwidth and one way delay for every edge in physical topology. With this data and your needs, you can distribute virtual machines between physical ones and combine them into a virtual topology. And then use this tool to launch virtual machines and combine them into a virtual topology in automatic mode.  

## **Use cases:**

1. You want to measure available bandwidth and delay on physical topology.
2. You want to start virtual topology on physical one. And you have already measured physical topology.

## **Usage example:**

#### **Measuring physical topology:**

First of all you need to create physical topology graph in gml format. Example you can find in `examples/`.

Then you need to start client side app on every physical node. You can do it by next command, where `NODE_HOSTNAME`
is name of this node in physical topology graph file and `HOST_IP_ADDRESS` is ip address of server side app.

```shell
python3 main.py client --hostname NODE_HOSTNAME --host HOST_IP_ADDRESS
```

Also, you need to start server side app on any node. You can do it by next command, where `PHYSICAL_GRAPH` is path to
the physical topology graph file.

```shell
python3 main.py server --action measure --phys_graph PHYSICAL_GRAPH
```

After performing measurement server side will create file named `measured.gml`. it will contain a graph of the
physical topology and measured values for bandwidth and delay.

#### **Starting virtual machines and creating virtual topology:**

First of all, you must have a graph file of measured physical topology.

You also need to create a virtual topology file in gml format. This graph also must include mapping of every virtual
edge to set of physical edges. Example you can find in `examples/`

Then you need to start client side app on every physical node. You can do it by next command, where `NODE_HOSTNAME`
is name of this node in physical topology graph file and `HOST_IP_ADDRESS` is ip address of server side app.

```shell
python3 main.py client --hostname NODE_HOSTNAME --host HOST_IP_ADDRESS
```

Also, you need to start server side app on any node. You can do it by next command, where `PHYSICAL_GRAPH` is path to
the physical topology graph file and `VIRTUAL_GRAPH` is path to the virtual topology graph file.

```shell
python3 main.py server --action run_vms --phys_graph PHYSICAL_GRAPH --vm_graph VIRTUAL_GRAPH
```

## **Preparation for usage:**

If you want to create virtual topology from virtual machines on different hosts you should first check `cmd_utility.py` file.
And more precisely next functions:
* `prepare_for_vms()` - this functions calls once on each host and create base image for machines
* `start_specific_vm()` - this functions calls every on every virtual machine creation

You may want to replace my hardcoded commands with yours according to your specific environment.

## **Dependencies:**

Linux Utilities:

- `iperf2` - measure bandwidth
- `ping` - measure delay 
- `libvirt`, `qemu` - for creating and managing virtual machines 

Main program:
- `python3` >= 3.9
- python libraries: `psutil`, `networkx`

## **Author:**

- [Veniamin Arefev](https://github.com/Veniamin-Arefev)
