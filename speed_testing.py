import subprocess
from multiprocessing import Process

server_proc: Process = None


def start_server():
    global server_proc
    if server_proc is not None:
        server_proc.kill()
    server_proc = Process(target=start_server_daemon)
    server_proc.start()


def start_server_daemon():
    cmd_str = "iperf -s"
    subprocess.run(cmd_str, shell=True, capture_output=True)


def test_speed(ip):
    cmd_str = "iperf -c {0}"
    proc = subprocess.run(cmd_str.format(ip), shell=True, capture_output=True)
    lines = proc.stdout.decode().split("\n")
    words = list(filter(lambda x: len(x) > 0, map(lambda x: x.split(), lines)))

    speed, units = words[-1][-2:]

    return speed, units


def test_rtt(ip):
    cmd_str = "ping {0} -c 10"
    proc = subprocess.run(cmd_str.format(ip), shell=True, capture_output=True)
    lines = proc.stdout.decode().split("\n")
    words = list(filter(lambda x: len(x) > 0, map(lambda x: x.split(), lines)))

    name, timings = words[-1][1].split('/'), words[-1][-2].split('/')

    res = dict(zip(name, timings))

    return res["avg"]
