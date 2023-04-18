import subprocess
import typing
from multiprocessing import Process
import xml.etree.ElementTree as ET

server_proc: typing.Union[Process, None] = None


def start_server():
    stop_server()
    global server_proc
    server_proc = Process(target=start_server_daemon)
    server_proc.start()


def stop_server():
    global server_proc
    if server_proc is not None:
        server_proc.kill()
        server_proc = None


def start_server_daemon():
    cmd_str = "iperf -s -u"
    subprocess.run(cmd_str, shell=True, capture_output=True)


def test_speed(ip):
    cmd_str = "iperf -u -f K -b 10G -c {0}"
    proc = subprocess.run(cmd_str.format(ip), shell=True, capture_output=True)
    lines = proc.stdout.decode().split("\n")
    words = list(filter(lambda x: len(x) > 0, map(lambda x: x.split(), lines)))

    speed = words[-1][-6]

    return speed


def test_rtt(ip):
    cmd_str = "ping {0} -c 10"
    proc = subprocess.run(cmd_str.format(ip), shell=True, capture_output=True)
    lines = proc.stdout.decode().split("\n")
    words = list(filter(lambda x: len(x) > 0, map(lambda x: x.split(), lines)))

    name, timings = words[-1][1].split('/'), words[-1][-2].split('/')

    res = dict(zip(name, timings))

    return res["avg"]


def prepare_for_vms():
    command = """
mkdir /home/s02190265/Desktop/images
virsh pool-create-as --name pool --type dir --target /home/s02190265/Desktop/images

cp /home/s02190265/Net/persistent_dir/images/base.qcow2 /home/s02190265/Desktop/images/image_base.qcow2"""


def start_specific_vm(hostname, nets):
    command = f"""
cp /home/s02190265/Desktop/images/image_base.qcow2 /home/s02190265/Desktop/images/{hostname}.qcow2
chmod _libvirt /home/s02190265/Desktop/images/{hostname}.qcow2

virt-install --name {hostname} --os-variant=alt.p10 --graphics vnc --import --disk /home/s02190265/Desktop/images/{hostname}.qcow2 --ram 2048 --vcpus=2 --network network=default --hvm --virt-type=kvm --noautoconsole --print-xml > {hostname}.xml
"""
    proc = subprocess.run(command, shell=True, capture_output=True)
    tree = ET.parse(f"{hostname}.xml")
    root = tree.getroot()
    devices = root.find("devices")

    # should be only one in default configuration
    default_interface = devices.find("interface")
    vm_isolation = ET.SubElement(default_interface, "port", attrib={"isolated": "yes"})

    # source, local, port, speed, delay = "10.16.134.2", "10.16.134.1", "11115", "100", "5"

    # nets = [['10.16.134.2', '10.16.134.1', '11115', '100', '5'], ['10.16.134.3', '10.16.134.1', '11116', '100', '1']]

    for source, local, port, speed, delay in nets:
        interface_elem = ET.SubElement(devices, "interface", attrib={"type": "udp", "delay": delay})
        source_elem = ET.SubElement(interface_elem, "source", attrib={"address": source, "port": port})
        local_elem = ET.SubElement(source_elem, "local", attrib={"address": local, "port": port})
        link_elem = ET.SubElement(interface_elem, "link ", attrib={"state": "up"})

        bandwidth_elem = ET.SubElement(interface_elem, "bandwidth")
        inbound_elem = ET.SubElement(bandwidth_elem, "inbound", attrib={"average": speed})
        outbound_elem = ET.SubElement(bandwidth_elem, "outbound", attrib={"average": speed})

    tree.write(f"{hostname}.xml")
