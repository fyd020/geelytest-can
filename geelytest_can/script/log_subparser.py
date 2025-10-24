import sys
import time
import signal
import logging
import argparse
from jidutest_can.script.__main__ import MainParser
from jidutest_can.canapp import CanLogManager
from jidutest_can.script.tools import set_log
from jidutest_can.script.tools import is_valid_can_id
from jidutest_can.can import PCANFD_500000_2000000
from jidutest_can.script.tools import convert_frame_id_or_name
from jidutest_can.script.tools import create_bus


logger = logging.getLogger(__name__)


@MainParser.RegisterSubparser("log-data", [
    {"arg_name": "interface", "type": str, "help": "CAN device vendor id, eg: pcan", "choices": ["pcan", "tosun", "smartvci"]},
    {"arg_name": "channel", "type": int, "help": "CAN device channel, eg: 1"},
    {"arg_name": "filename", "type": str, "help": "The name/path of file to log data"},
    {"arg_name": "id_list", "type": str, "help": "CAN id list, eg: 0x123 0x234", "nargs": "*"},
    {"arg_name": "--multi", "type": str, "help":
        "Info for simultaneous logging of multi channel messages, "
        "eg: interface1:channel1:fd1:id1:id2:id3... interface2:channel2:fd2:id1:id2:id3... ",
     "nargs": "*", "default": []},
    {"arg_name": "--size", "type": int, "help": "Logging file size, unit:kb", "default": 0},
    {"arg_name": "--fd", "type": int, "help": "CAN channel type, 0: CAN, 1: CANFD", "default": 0, "choices": [0, 1]},
    {"arg_name": "--bitrate", "type": int, "help": "CAN bitrate, unit: kbps", "default": 500},
    {"arg_name": "--duration", "type": int, "help": "Stop logging until duration, unit: s", "default": None},
    {"arg_name": "--debug", "type": int, "help": "Enable or disable debug level", "default": 0, "choices": [0, 1]},
],
    "Logging CAN messages to a file")
def start_logging(args: argparse.Namespace) -> None:
    set_log(args.debug)
    multi = args.multi
    buses = set()

    def _process_sub_args(interface, channel, fd=0, ids=None):
        id_set = set(ids.split(",") if ids and isinstance(ids, str) else ids or [])
        for arg_id in id_set:
            if not is_valid_can_id(int(arg_id, 16), True):
                logger.warning(f"{id_set.remove(arg_id)} is not valid can standard/extended id \n")

        filters = list()
        for frame_id in id_set:
            frame_id = convert_frame_id_or_name(frame_id)
            can_filter = {"can_id": frame_id,
                          "can_mask": 0x1fffffff,
                          "extended": False if frame_id <= 0x7ff else True}
            filters.append(can_filter)

        bus_params = dict()
        if fd:
            bus_params.update({"fd": True})
            bus_params.update(PCANFD_500000_2000000)
        else:
            bus_params.update({"bitrate": args.bitrate * 1000})
        bus = create_bus(interface=interface, channel=channel, **bus_params)
        bus.filters = filters
        buses.add(bus)

    for _ in multi:
        _process_sub_args(*_.split(":", maxsplit=3))
    _process_sub_args(args.interface, args.channel, args.fd, args.id_list)
    manager = CanLogManager(buses)
    if args.filename.endswith(".blf"):
        # 由于blf文件在切片时获取的文件大小和实际有偏差，在此做简单的倍数放大
        size = args.size * 1024 * 12.8
    else:
        size = args.size * 1024
    manager.start_logging(args.filename, size)

    def stop_logging(signum, frame) -> None:
        manager.stop_logging()
        for bus in buses:
            bus.shutdown()
        logger.warning(f"Receive signal 'Ctrl + C', end the application\n")
        sys.exit(1)

    signal.signal(signal.SIGINT, stop_logging)

    duration = args.duration
    if duration is None:
        duration = 2 ** 20
    time.sleep(duration)
    manager.stop_logging()
    for _bus in buses:
        _bus.shutdown()


@MainParser.RegisterSubparser("replay-data", [
    {"arg_name": "interface", "type": str, "help": "CAN device vendor id, eg: pcan", "choices": ["pcan", "tosun"]},
    {"arg_name": "channel", "type": int, "help": "CAN device channel, eg: 1"},
    {"arg_name": "filename", "type": str, "help": "The name/path of file to log data."},
    {"arg_name": "--fd", "type": int, "help": "CAN channel type, 0: CAN, 1: CANFD", "default": 0, "choices": [0, 1]},
    {"arg_name": "--bitrate", "type": int, "help": "CAN bitrate, unit: kbps", "default": 500},
    {"arg_name": "--debug", "type": int, "help": "Enable or disable debug level", "default": 0, "choices": [0, 1]},
], "Replay CAN messages from a file")
def replay_data(args: argparse.Namespace) -> None:
    set_log(args.debug)
    bus_params = dict()
    if args.fd:
        bus_params.update({"fd": True})
        bus_params.update(PCANFD_500000_2000000)
    else:
        bus_params.update({"bitrate": args.bitrate * 1000})
    bus = create_bus(interface=args.interface, channel=args.channel, **bus_params)
    manager = CanLogManager(bus)
    manager.replay_data(args.filename)

    def stop_replaying(signum, frame) -> None:
        logger.warning(f"Receive signal 'Ctrl + C', end the application\n")
        sys.exit(1)

    signal.signal(signal.SIGINT, stop_replaying)


@MainParser.RegisterSubparser("log-convert", [
    {"arg_name": "source_file", "type": str, "help": "Source file path that need to be converted, eg: xxx.blf"},
    {"arg_name": "dest_file", "type": str, "help": "Destination file path after conversion, eg: xxx.asc"},
    {"arg_name": "--size", "type": int, "help": "Destination file slice size after conversion, unit:KB", "default": 0},
    {"arg_name": "--debug", "type": int, "help": "Enable or disable debug level", "default": 0, "choices": [0, 1]},
], "Convert log file format to another file format")
def log_convert(args: argparse.Namespace) -> None:
    set_log(args.debug)
    if args.dest_file.endswith(".blf"):
        # 由于blf文件在切片时获取的文件大小和实际有偏差，在此做简单的倍数放大
        size = args.size * 1024 * 12.8
    else:
        size = args.size * 1024
    try:
        CanLogManager.log_convert(args.source_file, args.dest_file, size)
    except KeyboardInterrupt:
        logger.warning(f"Receive signal 'Ctrl + C', end the application\n")
        sys.exit(1)
    logger.info(f"Conversion completion.")


@MainParser.RegisterSubparser("read-log", [
    {"arg_name": "log_file", "type": str, "help": "Log file path that need to be read, eg: xxx.blf"},
    {"arg_name": "--debug", "type": int, "help": "Enable or disable debug level", "default": 0, "choices": [0, 1]},
], "Read and display log file.")
def read_log(args: argparse.Namespace) -> None:
    set_log(args.debug)
    try:
        CanLogManager.read_log(args.log_file)
    except KeyboardInterrupt:
        logger.warning(f"Receive signal 'Ctrl + C', end the application\n")
        sys.exit(1)
    logger.info(f"Read completion.")


@MainParser.RegisterSubparser("log-parse", [
    {"arg_name": "log_file", "type": str, "help": "Log file path that need to be parse, eg: xxx.blf"},
    {"arg_name": "db_path", "type": str, "help": "CAN database file path, eg: XXX.dbc"},
    {"arg_name": "--dest_file", "type": str, "help": "Destination file path after parsed, eg: xxx.json", "default": None},
    {"arg_name": "--debug", "type": int, "help": "Enable or disable debug level", "default": 0, "choices": [0, 1]},
], "Log file parsed by dbc.")
def log_parse(args: argparse.Namespace) -> None:
    set_log(args.debug)
    try:
        dest_file = args.dest_file or args.log_file.split(".")[0] + ".json"
        CanLogManager.log_parse(args.log_file, args.db_path, dest_file)
    except KeyboardInterrupt:
        logger.warning(f"Receive signal 'Ctrl + C', end the application\n")
        sys.exit(1)
    logger.info(f"Read completion.")
