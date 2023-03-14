import argparse
import speed_testing

arg_parser = argparse.ArgumentParser(prog="Net-tester", description="Test network speed for multiple hosts")

arg_parser.add_argument("-v", "--verbose", action="store_true")

arg_parser.add_argument("type", choices=["client", "server"], default="client")

args = arg_parser.parse_args()

if args.type == "client":
    ip = "192.168.0.101"
    speed = speed_testing.test_speed(ip)
    rtt = speed_testing.test_rtt(ip)

    print(f"Speed is {speed}")
    print(f"Rtt is {rtt}")

elif args.type == "server":
    speed_testing.start_server()
    print(123)
