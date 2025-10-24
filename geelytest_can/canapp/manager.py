import sys
import json
import logging
import pathlib
import typing
import bitstruct
from can import BusABC
from can import Logger
from can import Notifier
from can import Printer
from can import LogReader
from can import MessageSync
from can import SizedRotatingLogger
from can.util import channel2int
from geelytest_can.cantools import load_file
from geelytest_can.cantools.database import NamedSignalValue


logger = logging.getLogger(__name__)


class CanLogManager(object):
    """
    对trace的录制、回放等管理
    """

    def __init__(self,
                 bus: typing.Union[BusABC, typing.List[BusABC], typing.Tuple[BusABC], typing.Set[BusABC]],
                 ) -> None:
        """
        功能说明：初始化对象
        参数说明：
            :param bus: Bus对象
        异常说明：无
        返回值：None
        """
        self.notifier = Notifier(bus, [])
        self.logger_listener: SizedRotatingLogger = None
        self.printer_listener: Printer = None

    def start_logging(self, file: typing.Union[pathlib.Path, str], max_bytes: int = 0) -> None:
        """
        功能说明：开始录制数据
        参数说明：
            :param file: 需要保存录制的数据的文件名, 文件格式为*.blf, *.asc, *.csv等格式
            :param max_bytes: 保存的一个文件的最大size，超过后会新建一个文件继续保存，
                              单位为byte，默认值0则表示无穷大，保存在一个文件中
        异常说明：无
        返回值：None
        """
        logger.info("Start logging data.")
        self.logger_listener = SizedRotatingLogger(file, max_bytes)
        self.notifier.add_listener(self.logger_listener)

    def stop_logging(self) -> None:
        """
        功能说明：停止录制数据
        参数说明：无
        异常说明：无
        返回值：None
        """
        logger.info("Stop logging data.")
        if self.logger_listener:
            self.notifier.remove_listener(self.logger_listener)
            self.logger_listener.stop()
        self.notifier.stop()

    def replay_data(self, file: typing.Union[pathlib.Path, str]) -> None:
        """
        功能说明：回放数据
        参数说明：
            :param file: 需要回访数据的文件名，文件格式为*.blf, *.asc, *.csv等格式
        异常说明：
            :KeyboardInterrupt: 键盘中断时继续回放
        返回值：None
        """
        reader = LogReader(file)
        in_sync = MessageSync(reader)
        logger.info("Start replaying data.")
        try:
            for message in in_sync:
                if message.is_error_frame:
                    continue
                for bus in self.notifier.buses:
                    if channel2int(bus.channel_info) == channel2int(message.channel):
                        message.channel = bus.channel_info
                        bus.send(message)
        except KeyboardInterrupt:
            pass

    @staticmethod
    def read_log(file: typing.Union[pathlib.Path, str]) -> None:
        """
        功能说明：读文件数据
        参数说明：
            :param file: 需要读取数据的文件名，文件格式为*.blf, *.asc, *.csv等格式
        异常说明：无
        返回值：None
        """
        reader = LogReader(file, encoding="utf-8")
        logger.info("Start reading data.")
        for message in reader:
            if message.is_error_frame:
                continue
            logger.info(message)

    def start_printing(self, file: typing.Union[pathlib.Path, str] = None):
        """
        功能说明：开始打印数据
        参数说明：
            :param file: 需要保存打印的数据的文件名，文件格式为*.txt，None则直接输出到控制台
        异常说明：无
        返回值：None
        """
        logger.info("Start printing data.")
        self.printer_listener = Printer(file)
        self.notifier.add_listener(self.printer_listener)

    def stop_printing(self) -> None:
        """
        功能说明：停止打印数据
        参数说明：无
        异常说明：无
        返回值：None
        """
        logger.info("Stop printing data.")
        if self.printer_listener:
            self.notifier.remove_listener(self.printer_listener)
            self.printer_listener.stop()
        self.notifier.stop()

    @staticmethod
    def log_convert(input_file, output_file, file_size) -> None:
        """
        功能说明：转换log文件格式
        参数说明：无
        异常说明：无
        返回值：None
        """
        logger.info("Start converting log file.")
        with LogReader(input_file) as reader:

            if file_size:
                _logger = SizedRotatingLogger(
                    base_filename=output_file, max_bytes=file_size
                )
            else:
                _logger = Logger(filename=output_file)

            with _logger:
                try:
                    for m in reader:
                        _logger(m)
                except KeyboardInterrupt:
                    sys.exit(1)

    @staticmethod
    def log_parse(log_file, db_path, dest_file) -> None:
        """
        功能说明：解析log数据
        参数说明：无
        异常说明：无
        返回值：None
        """
        logger.info("Start parsing log file.")
        db = load_file(db_path)
        parsed_dict = dict()
        with LogReader(log_file) as reader, open(dest_file, mode="w", encoding="utf-8") as output:
            try:
                for m in reader:
                    message_dict = dict()
                    try:
                        frame = db.get_message_by_frame_id(m.arbitration_id)
                        signal_dict = frame.decode(m.data)
                        for name, value in signal_dict.items():
                            if isinstance(value, NamedSignalValue):
                                signal_dict[name] = str(value)
                        message_dict[hex(m.arbitration_id)] = str(m)
                        message_dict[frame.name] = signal_dict
                        parsed_dict[m.timestamp] = message_dict
                    except Exception as ex:
                        message_dict[hex(m.arbitration_id)] = str(m)
                        if m.is_error_frame:
                            message_dict["Error Frame"] = f"{m.timestamp} | can error | Error Frame"
                        elif m.arbitration_id == 1:
                            logger.warning(f"Unable to parse message:{m}")
                        elif isinstance(ex, (KeyError, bitstruct.Error)):
                            logger.error(f"Unable to parse message:{m} \npossible mismatch between "
                                         f"type of can channel {m.channel} in the log: {log_file} and dbc: {db_path}")
                        else:
                            logger.exception(ex)
                        parsed_dict[m.timestamp] = message_dict
                output.write(json.dumps(parsed_dict, indent=4, sort_keys=True, ensure_ascii=False))
            except KeyboardInterrupt:
                sys.exit(1)


class CanTools(object):
    """
    封装can对外常用的工具
    """

    pass
