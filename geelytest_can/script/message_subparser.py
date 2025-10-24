import logging
import sys
import time
import signal
import argparse
from jidutest_can.can import CanOperationError
from jidutest_can.can import RawMessage
from jidutest_can.can import BufferedReader
from jidutest_can.can import Notifier
from jidutest_can.script.__main__ import MainParser
from jidutest_can.script.tools import set_log
from jidutest_can.script.tools import is_int_value
from jidutest_can.can import PCANFD_500000_2000000
from jidutest_can.script.tools import is_valid_data_frame
from jidutest_can.script.tools import is_valid_remote_frame
from jidutest_can.script.tools import is_valid_can_payload
from jidutest_can.script.tools import is_valid_can_id
from jidutest_can.script.tools import convert_frame_id_or_name
from jidutest_can.script.tools import create_bus
from jidutest_can.script.tools import signal_handler


logger = logging.getLogger(__name__)


@MainParser.RegisterSubparser("send-msg", [
    {"arg_name": "interface", "type": str, "help": "CAN device vendor id, eg: pcan", "choices": ["pcan", "tosun", "smartvci"]},
    {"arg_name": "channel", "type": str, "help": "CAN device channel, eg: 1"},
    {"arg_name": "message_list", "type": str,
     "help": "CAN message, data frame eg: 0x123=11:22:33:44:55, remote frame eg: 0x123R", "nargs": "+"},
    {"arg_name": "--fd", "type": int, "help": "CAN channel type, 0: CAN, 1: CANFD", "default": 0, "choices": [0, 1]},
    {"arg_name": "--bitrate", "type": int, "help": "CAN bitrate, unit: kbps", "default": 500},
    {"arg_name": "--interval", "type": int, "help": "Send every interval time, unit: ms", "default": 100},
    {"arg_name": "--duration", "type": int, "help": "Stop sending until duration, unit: s", "default": None},
    {"arg_name": "--catch_exc", "type": int, "help": "Disconnect and reconnect after catching an send exception",
     "default": None},
    {"arg_name": "--debug", "type": int, "help": "Enable or disable debug level", "default": 0, "choices": [0, 1]},
], "Send can or canfd message in CAN or CANFD bus")
def send_msg(args: argparse.Namespace) -> None:
    set_log(args.debug)
    message_set = set(args.message_list)
    msg_list = []
    for message in message_set:
        if is_valid_data_frame(message):
            s_msg, s_value = message.split("=")
            if args.fd and not is_valid_can_payload(s_value, True):
                logger.error(f"{s_value} is not valid CAN-FD message payload \n")
                sys.exit(1)
            if not args.fd and not is_valid_can_payload(s_value, False):
                logger.error(f"{s_value} is not valid CAN message payload \n")
                sys.exit(1)
            lst = [int("0x" + i, 16) for i in s_value.split(":")]
            msg = RawMessage(arbitration_id=int(s_msg, 16),
                             data=lst,
                             channel=args.channel,
                             is_fd=True if args.fd else False,
                             bitrate_switch=True if args.fd else False,
                             is_extended_id=False if int(s_msg, 16) <= 0x7ff else True,
                             is_remote_frame=False
                             )
        elif is_valid_remote_frame(message):
            if args.fd == 1:
                logger.error("CAN-FD not support remote frame")
                sys.exit(1)

            s_msg = message.split("R")[0]
            msg = RawMessage(arbitration_id=int(s_msg, 16),
                             is_fd=True if args.fd else False,
                             channel=args.channel,
                             bitrate_switch=True if args.fd else False,
                             is_extended_id=False if int(s_msg, 16) <= 0x7ff else True,
                             is_remote_frame=True
                             )
        else:
            logger.error("message parser is Erorr should use msg_id=11:22:...ff or 0x7ffR \n")
            sys.exit(1)
        msg_list.append(msg)

    def stop_sending_can_message(signum, frame) -> None:
        bus.stop_all_periodic_tasks()
        logger.error(f"Receive signal 'Ctrl + C', end the application\n")
        sys.exit(1)

    signal.signal(signal.SIGINT, stop_sending_can_message)

    bus_params = dict()
    if args.fd:
        bus_params.update({"fd": True})
        if args.interface == "tosun":
            from jidutest_can.can.interfaces.tosun.constants import TOSUNCANFD_500000_2000000
            bus_params.update(TOSUNCANFD_500000_2000000)
        else:
            bus_params.update(PCANFD_500000_2000000)
    else:
        bus_params.update({"bitrate": args.bitrate * 1000})

    def _send_msg(msgs):
        _bus = create_bus(interface=args.interface, channel=args.channel, **bus_params)
        for _msg in msgs:
            try:
                _msg.channel = _bus.channel_info
                _bus.send_periodic(_msg, period=args.interval / 1000)
                logger.info(f"Sending message ==> {_msg}")
            except CanOperationError:
                logger.warning("Send message failed \n")
        return _bus

    bus = _send_msg(msg_list)

    if not args.duration:
        while True:
            if args.catch_exc:
                for task in bus.periodic_tasks:
                    if task.exception:
                        bus.shutdown()
                        bus = _send_msg(msg_list)
                        break
    else:
        time.sleep(args.duration)


@MainParser.RegisterSubparser("recv-msg", [
    {"arg_name": "interface", "type": str, "help": "CAN device vendor id, eg: pcan", "choices": ["pcan", "tosun", "smartvci"]},
    {"arg_name": "channel", "type": int, "help": "CAN device channel, eg: 2"},
    {"arg_name": "id_list", "type": str, "help": "CAN id list, eg: 0x123 0x234", "nargs": "*"},
    {"arg_name": "--fd", "type": int, "help": "CAN channel type, 0: CAN, 1: CANFD", "default": 0, "choices": [0, 1]},
    {"arg_name": "--bitrate", "type": int, "help": "CAN bitrate, unit: kbps", "default": 500},
    {"arg_name": "--debug", "type": int, "help": "Enable or disable debug level", "default": 0, "choices": [0, 1]},
    {"arg_name": "--duration", "type": int, "help": "Stop sending until duration, unit: s", "default": None},
    {"arg_name": "--catch_exc", "type": int, "help": "Disconnect and reconnect after catching an recv exception",
     "default": None},
], "Receive can or canfd message in CAN or CANFD bus")
def recv_msg(args: argparse.Namespace) -> None:
    set_log(args.debug)
    signal.signal(signal.SIGINT, signal_handler)

    id_set = set(args.id_list)
    for arg_id in id_set.copy():
        if not is_int_value(arg_id) or not is_valid_can_id(int(arg_id, 16), True):
            id_set.remove(arg_id)
            logger.warning(f"{arg_id} is not valid can standard/extended id \n")

    filters = list()
    for frame_id in id_set:
        frame_id = convert_frame_id_or_name(frame_id)
        _filter = {"can_id": frame_id,
                   "can_mask": 0x1fffffff,
                   "extended": False if frame_id <= 0x7ff else True}
        filters.append(_filter)

    bus_params = dict()
    if args.fd:
        bus_params.update({"fd": True})
        if args.interface == "tosun":
            from jidutest_can.can.interfaces.tosun.constants import TOSUNCANFD_500000_2000000
            bus_params.update(TOSUNCANFD_500000_2000000)
        else:
            bus_params.update(PCANFD_500000_2000000)
    else:
        bus_params.update({"bitrate": args.bitrate * 1000})
    bus = create_bus(interface=args.interface, channel=args.channel, **bus_params)
    bus.set_filters(filters)

    listener = BufferedReader()
    notifier = Notifier(bus, [listener])

    def stop_receiving_can_message(signum, frame) -> None:
        notifier.remove_listener(listener)
        logger.error(f"Receive signal 'Ctrl + C', end the application\n")
        sys.exit(1)

    signal.signal(signal.SIGINT, stop_receiving_can_message)

    logger.info("Start receiving messages...")
    duration = args.duration
    start_time = time.time()
    while True:
        if args.catch_exc and notifier.exceptions:
            _bus, exc = notifier.exceptions.popitem()
            time.sleep(0.1)
            notifier.add_bus(_bus)
            notifier.add_listener(listener)
            _bus.reset()
        raw_message = listener.get_message()
        if raw_message:
            logger.info(f"Received Raw message: {raw_message}")
        if duration is not None and time.time() - start_time > duration:
            break
