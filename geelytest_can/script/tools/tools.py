import re
import sys
import typing
import logging
import platform
import subprocess
from jidutest_can.can import CanBus
from jidutest_can.can.interfaces import BusABC
from jidutest_can.cantools import Database
from jidutest_can.cantools import Message
from jidutest_can.cantools import Signal
from jidutest_can.cantools import load_file
from jidutest_can.script.tools import rgb_blue
from jidutest_can.script.tools import rgb_green
from jidutest_can.script.tools import rgb_red
from jidutest_can.script.tools import log_date_format
from jidutest_can.script.tools import info_log_format
from jidutest_can.script.tools import debug_log_format
from jidutest_can.can.interfaces.tosun import ToSunBus
from jidutest_can.can import CanInitializationError
from jidutest_can.can import CanInterfaceNotImplementedError
from jidutest_can.cantools import UnsupportedDatabaseFormatError


logger = logging.getLogger(__name__)


def convert_frame_id_or_name(frame_id_or_name: str) -> typing.Union[int, str]:
    try:
        if frame_id_or_name.startswith('0x'):
            result = int(frame_id_or_name, 16)
        else:
            result = int(frame_id_or_name)
    except:
        result = frame_id_or_name
    return result


def signal_handler(signum, frame):
    sys.exit("------------------Interrupt the program----------------\n")


def convert_signal_value(signal: Signal, signal_value: str) -> int:
    try:
        if signal_value.startswith('0x'):
            result = int(signal_value, 16)
        else:
            result = float(signal_value)
    except:
        result = signal.choice_string_to_number(signal_value)
    return result


def print_db_message(dbc: Database, msg: Message or str or int) -> None:
    if isinstance(msg, str):
        msg = dbc.get_message_by_name(msg)
    if isinstance(msg, int):
        msg = dbc.get_message_by_frame_id(msg)
    sys.stdout.write(rgb_green(f"{msg.name}\n"))
    sys.stdout.write(rgb_green("frame_ID: ") + rgb_blue(f"{msg.frame_id}\n"))
    sys.stdout.write(rgb_green("Cycle_time: ") + rgb_blue(f"{msg.cycle_time}\n"))
    sys.stdout.write(rgb_green("Comment: ") + rgb_blue(f"{msg.comment}\n"))
    sys.stdout.write(rgb_green("Senders: ") + rgb_blue(f"{msg.senders}\n"))
    sys.stdout.write(rgb_green("Signals:\n"))
    for signal in msg.signals:
        sys.stdout.write(rgb_blue(f"{signal}\n"))
    sys.stdout.write("\n")


def print_db_signal(dbc: Database, sgn: Signal or str) -> None:
    if isinstance(sgn, str):
        sgn = dbc.get_signal_by_name(sgn)
    sys.stdout.write(
        rgb_green("Signal: ") + rgb_blue(sgn.name) + "\n" +

        rgb_green("Factor: ") + rgb_blue(sgn.scale) + "\t\t" +
        rgb_green("Offset: ") + rgb_blue(sgn.offset) + "\t\t" +
        rgb_green("Unit: ") + rgb_blue(sgn.unit if sgn.unit else 'no unit') + "\n" +

        rgb_green("Length(bit): ") + rgb_blue(sgn.length) + "\t\t" +
        rgb_green("Byte Order: ") + rgb_blue(sgn.byte_order) + "\t" +
        rgb_green("IsSigned: ") + rgb_blue(sgn.is_signed) + "\t\t" +
        rgb_green("IsFloat: ") + rgb_blue(sgn.is_float) + "\n" +

        rgb_green("Init Value: ") + rgb_blue(sgn.initial) + "\t" +
        rgb_green("Minimum: ") + rgb_blue(sgn.minimum) + "\t\t" +
        rgb_green("Maximum: ") + rgb_blue(sgn.maximum) + "\t\t" +
        rgb_green("Value Table: ") + rgb_blue(dict(sgn.choices) if sgn.choices else '') + "\n")

    msg = dbc.get_message_by_signal(sgn)
    sys.stdout.write(
        rgb_green("Message: ") + rgb_blue(msg.name) + "\t\t" +
        rgb_green("frame_ID: ") + rgb_blue(msg.frame_id) + "\t\t" +
        rgb_green("Cycle Time: ") + rgb_blue(msg.cycle_time) + "\n" +

        rgb_green("Receivers: ") + rgb_blue(sgn.receivers) + "\t\t\t" +
        rgb_green("Senders: ") + rgb_blue(msg.senders) + "\n")

    sys.stdout.write(
        rgb_green("Comment: ") + rgb_blue(sgn.comment if sgn.comment else '') + "\n\n")


def get_db_by_file(filepath: str) -> Database:
    try:
        db_object = load_file(filepath)
    except FileNotFoundError:
        sys.exit(rgb_red(f"Database file {filepath} is not found"))
    except UnsupportedDatabaseFormatError:
        sys.exit(rgb_red(f"Database file {filepath} format is not supported"))
    else:
        return db_object


def create_bus(interface, channel, **kwargs) -> BusABC:
    try:
        bus = CanBus(interface=interface, channel=channel, **kwargs)
    except CanInterfaceNotImplementedError as ex:
        sys.exit(rgb_red(f"Vendor product ID {interface} is not supported,Because:{ex} \n"))
    except ValueError:
        sys.exit(rgb_red(f"Hardware channel {channel} is not recognized \n"))
    except CanInitializationError as ex:
        sys.exit(rgb_red(f"Hardware {channel} is not attached "
                         f"or is occupied by another application,Because:{ex} "))
    return bus


def get_signal_by_name(db: Database, sgn_name: str) -> typing.Optional[Signal]:
    try:
        sgn_object = db.get_signal_by_name(sgn_name)
    except:
        return None
    else:
        return sgn_object


def get_value_by_str(sgn: Signal, sgn_value: str) -> int:
    try:
        sgn_value = eval(sgn_value)
    except:
        if sgn.choices:
            try:
                sgn_value = sgn.choice_string_to_number(sgn_value)
            except:
                logger.error(rgb_red(f"Signal {sgn.name} hasn't the value {sgn_value}\n"
                                     f"It must be in {list(sgn.choices.values())}\n"))
                sys.exit(1)
            else:
                return sgn_value
    else:
        if not hasattr(sgn.choices, "keys"):
            return sgn_value
        if sgn_value in sgn.choices.keys():
            return sgn_value
        if sgn.minimum <= sgn_value <= sgn.maximum:
            return sgn_value
        logger.error(rgb_red(f"Signal {sgn.name} hasn't the value {sgn_value}\n"
                             f"It must be in [{sgn.minimum}, {sgn.maximum}]\n"))
        sys.exit(1)


def get_message_by_name_id(db: Database, msg_name_id: typing.Union[str, int]) -> typing.Optional[Message]:
    msg_name_id = convert_frame_id_or_name(msg_name_id)
    try:
        if isinstance(msg_name_id, str):
            msg_object = db.get_message_by_name(msg_name_id)
        else:
            msg_object = db.get_message_by_frame_id(msg_name_id)
    except:
        return None
    return msg_object


def set_log(debug=None, log_file=None, level="INFO"):
    if debug:
        level = logging.DEBUG
        log_format = debug_log_format
    else:
        log_format = info_log_format
    logging.basicConfig(
        level=level,
        format=log_format,
        datefmt=log_date_format,
        filename=log_file
    )


def show_dev() -> typing.List:
    plat = platform.system().lower()
    can_devices = list()
    if plat == "linux":
        cmd = "lspcan -a -T"
        prog = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
        for line in prog.stdout.readlines():
            old_line = line.decode('utf-8').strip()
            pattern = re.compile(r'(?<=pcanusbfd)\d*')
            dev_id = pattern.findall(old_line)
            if dev_id:
                new_dev_id = str(int(dev_id[0]) - 31)
                new_line = re.sub("pcanusbfd", "PCAN_USBBUS", old_line)
                new_line = re.sub(r'(?<=PCAN_USBBUS)\d{2}', new_dev_id, new_line)
                new_line = re.sub(r'(?<=PCAN_USBBUS\d{1})\s', " " * 9, new_line)
            else:
                new_line = old_line
            sys.stdout.write(rgb_blue(f"{new_line}\n"))
            can_devices.append(new_line)
        prog.kill()
        prog.wait()
        print(f'can_devices:{can_devices}')
    # try:
    #     can_bus = CanBus(interface="smartvci", show=True)
    # except CanInitializationError as ex:
    #     sys.exit(ex)
    # for i in can_bus.device_info:
    #     single_device_info = (rgb_green('Manufacturer') + ': ' + rgb_blue(f'{i[0]:<30}') +
    #                           rgb_green('Product') + ': ' + rgb_blue(f'{i[1]:<30}') +
    #                           rgb_green('Serial') + ': ' + rgb_blue(f'{i[2]:<30}\n')
    #                           )
    #     for channel in i[3]:
    #         line = rgb_green('Channel') + ': ' + rgb_blue(f'{channel:<10}' + single_device_info)
    #         sys.stdout.write(line)
    #         can_devices.append(line)
    return can_devices
