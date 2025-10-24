import argparse
import logging
import sys
import time
import signal
from jidutest_can.canapp import CanController
from jidutest_can.script.__main__ import MainParser
from jidutest_can.script.tools import set_log
from jidutest_can.script.tools import get_db_by_file
from jidutest_can.script.tools import get_signal_by_name
from jidutest_can.script.tools import get_value_by_str
from jidutest_can.script.tools import rgb_red
from jidutest_can.script.tools import rgb_blue
from jidutest_can.script.tools import is_valid_can_sgn_name_value_format


logger = logging.getLogger(__name__)


@MainParser.RegisterSubparser("send-sgn", [
    {"arg_name": "interface", "type": str, "help": "CAN device vendor id, eg: pcan", "choices": ["pcan", "tosun", "smartvci"]},
    {"arg_name": "channel", "type": int, "help": "CAN device channel, eg: 1"},
    {"arg_name": "db_path", "type": str, "help": "CAN database file path, eg: XXX.dbc"},
    {"arg_name": "signal_list", "type": str, "help": "CAN signal list, eg: n1=v1 n2=v2", "nargs": "+"},
    {"arg_name": "--duration", "type": int, "help": "Stop sending until duration, unit: s", "default": None},
    {"arg_name": "--debug", "type": int, "help": "Enable or disable debug level", "default": 0, "choices": [0, 1]},
], "Send signal via CAN card")
def can_send_sgn(args: argparse.Namespace) -> None:
    set_log(args.debug)
    db_object = get_db_by_file(args.db_path)
    sgn_dict = dict()
    for sgn in args.signal_list:
        assert is_valid_can_sgn_name_value_format(sgn)
        sgn_name, sgn_value = sgn.split("=")
        sgn_object = get_signal_by_name(db_object, sgn_name)
        sgn_value = get_value_by_str(sgn_object, sgn_value)
        sgn_dict.update({sgn_name: sgn_value})

    bus_config = db_object.buses[0]
    bus_name = bus_config.name
    controller = CanController(bus_name, args.interface, args.channel, args.db_path)

    def stop_sending_can_signals(signum, frame) -> None:
        controller.stop_sending()
        logger.error(rgb_blue(f"Receive signal 'Ctrl + C', end the application\n"))
        sys.exit(1)

    signal.signal(signal.SIGINT, stop_sending_can_signals)

    try:
        controller.connect()
    except Exception as ex:
        logger.error(rgb_red(f"{ex}"))
        sys.exit(1)
    controller.send_signals(**sgn_dict)

    duration = args.duration
    if duration is None:
        duration = 2 ** 31
    time.sleep(duration)
    controller.stop_sending()


@MainParser.RegisterSubparser("recv-sgn", [
    {"arg_name": "interface", "type": str, "help": "CAN device vendor id, eg: pcan", "choices": ["pcan", "tosun", "smartvci"]},
    {"arg_name": "channel", "type": int, "help": "CAN device channel, eg: 2"},
    {"arg_name": "db_path", "type": str, "help": "CAN database file path, eg: XXX.dbc"},
    {"arg_name": "signal_list", "type": str, "help": "CAN signal list, eg: n1 n2", "nargs": "+"},
    {"arg_name": "--num", "type": int, "help": "Stop receiving until num", "default": None},
    {"arg_name": "--duration", "type": int, "help": "Stop receiving until duration, unit: s", "default": None},
    {"arg_name": "--debug", "type": int, "help": "Enable or disable debug level", "default": 0, "choices": [0, 1]},
], "Reveive signal via CAN card")
def can_recv_sgn(args: argparse.Namespace) -> None:
    set_log(args.debug)
    db_object = get_db_by_file(args.db_path)
    sgn_set = set()
    if args.signal_list:
        sgn_set = set(args.signal_list)
        for sgn_name in sgn_set:
            get_signal_by_name(db_object, sgn_name)

    bus_config = db_object.buses[0]
    bus_name = bus_config.name
    controller = CanController(bus_name, args.interface, args.channel, args.db_path)
    try:
        controller.connect()
    except Exception as ex:
        logger.error(rgb_red(f"{ex}"))
        sys.exit(1)
    controller.receive_signals(*sgn_set, num=args.num, duration=args.duration)
