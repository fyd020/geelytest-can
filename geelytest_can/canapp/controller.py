import copy
import logging
import queue
import typing
import time
import pathlib
import bitstruct
from typing import List
from typing import Union
from typing import Any
from can import BusABC
from can import Bus as CanBus
from can import CanOperationError
from can import CanInitializationError
from can import CanInterfaceNotImplementedError
from can import CanFDBitTiming
from can import Message as RawMessage
from can import BufferedReader
from can import Notifier
from geelytest_can.e2e import e2e_crc_data
from geelytest_can.cantools import load_file
from geelytest_can.cantools import BusConfig
from geelytest_can.cantools import Database
from geelytest_can.cantools import Message
from geelytest_can.cantools.database.signal import NamedSignalValue


logger = logging.getLogger(__name__)


class CanController(object):
    
    # INTERFACES = ["pcan", "tosun", "smartvci"]

    def __init__(self,
                 name: str,
                 interface: str,
                 channel: int,
                 db_path: Union[pathlib.Path, str] = None,
                 bus: Union[BusABC, CanBus] = None
                 ) -> None:
        """
        功能说明：初始化对象
        参数说明：
            :param name: 控制器名字，用于从db中获取对应can bus,如果名字不符，默认获取第一个，并给出警告，不影响程序正常运行
            :param interface: 控制器采用的硬件设备类型（如PEAK公司的pcan）,目前只支持PCAN
            :param channel: 控制器使用的硬件设备通道号（1, 2, ... , max）
            :param db_path: dbc文件路径
            :param bus: bus对象，当db_path有值时，忽略此参数
            db_path和bus参数必传其一
        异常说明：无
        返回值：None
        """
        if not db_path and not bus:
            raise ValueError(f"Arguments 'db_path' or 'bus' can't' all be None.")
        self.__sent_signals = set()
        self.__modified_data = dict()
        self.sending_dict_datas = dict()
        self.__sending_raw_datas = list()
        self.__sending_messages = list()
        self.__name = name.lower()
        self.__interface = interface.lower()
        self.__channel = channel
        self.__db_path = db_path
        if db_path:
            self.__db = load_file(self.__db_path)
            # if self.__interface not in self.INTERFACES:
            #     raise AttributeError(f"Argument 'interface' choice can only in {self.INTERFACES} . "
            #                          f"Please check if the input parameters are incorrect.")
        else:
            self.__db = Database()
        self.__bus_config = None
        self.__bus = bus
        self.__notifier = None
        self.__connected = False
        self.__listener: BufferedReader = None
        self.init_counter = True

    @property
    def name(self) -> str:
        return self.__name

    @property
    def interface(self) -> str:
        return self.__interface

    @property
    def channel(self) -> int:
        return self.__channel

    @property
    def db_path(self) -> str:
        return self.__db_path

    @property
    def db(self) -> Database:
        return self.__db

    @property
    def bus_config(self) -> BusConfig:
        return self.__bus_config

    @property
    def bus(self) -> Union[BusABC, CanBus]:
        return self.__bus

    @property
    def notifier(self) -> Notifier:
        return self.__notifier

    def connect(self) -> bool:
        """
        功能说明：连接控制器
        参数说明: 无
        异常说明：
            :exception CanInterfaceNotImplementedError: 硬件设备类型不支持
            :exception ValueError: 获取到的值错误
            :exception CanInitializationError: CAN通道初始化错误，可能是没有连接或者被占用
        返回值：True/False
        """
        if self.__connected:
            return True
        for bus_config in self.__db.buses:
            if bus_config.name.lower().replace(
                    "_", "").split("can")[:1] == self.name.replace("_", "").split("can")[:1]:
                self.__bus_config = bus_config
                break
        if not self.__bus_config:
            if self.__db.buses:
                self.__bus_config = self.__db.buses[0]
            elif not self.__bus:
                raise AttributeError(f"Can't find the bus name {self.name} from {self.db_path}")
        if self.__bus_config:
            if self.__bus_config.name.lower() != self.name:
                logger.warning(f"Found bus name {self.__bus_config.name.lower()} "
                               f"from {self.db_path}, not expected {self.name}")
            bus_type = self.__bus_config.bus_type
            baudrate = self.__bus_config.baudrate
            fd_baudrate = self.__bus_config.fd_baudrate
            logger.debug(f"CAN Controller: bus_name = {self.name}")
            logger.debug(f"CAN Controller: bus_type = {bus_type}")
            logger.debug(f"CAN Controller: bus_baudrate = {str(baudrate)}")
            logger.debug(f"CAN Controller: bus_fd_baudrate = {str(fd_baudrate)}")

            try:
                if bus_type == "CAN":
                    self.__bus = CanBus(interface=self.__interface, channel=self.__channel, bitrate=baudrate)
                else:
                    self.__bus = CanBus(interface=self.__interface, channel=self.__channel, timing=CanFDBitTiming.FD_500000_5000000 \
                        if baudrate == 5*10**5 and fd_baudrate == 5*10**6 else CanFDBitTiming.FD_500000_2000000)
                    
            except CanInterfaceNotImplementedError as ex:
                raise CanInterfaceNotImplementedError(f"Vendor product ID {self.__interface} is not supported."
                                                      f"Because {ex}")
            except ValueError:
                raise ValueError(f"Hardware channel {self.__channel} is not recognized.")
            
            except CanInitializationError as ex:
                raise CanInitializationError(f"Hardware {self.__channel} is not attached"
                                             f"or is occupied by another application."
                                             f"Because {ex}")
                
        self.__connected = True
        logger.info(f"{self.__bus} is connected")
        self.start_receiving()
        return True

    def disconnect(self) -> None:
        """
        功能说明：断开控制器
        参数说明：无
        异常说明：无
        返回值：None
        """
        if self.__bus and self.__connected:
            logger.debug(f"In time:{time.time()}, {self.bus.channel_info} Disconnecting ......")
            if self.__notifier:
                self.stop_receiving()
            self.__bus.shutdown()
            self.__connected = False
            logger.info(f"Successfully disconnected  {self.bus.channel_info} from device.")
            if self.__listener:
                self.__listener.buffer.queue.clear()

    def send_signals_once(self, *signals: dict, **kwargs: Any) -> None:
        """
        功能说明： 发送一帧。可以同时发多个信号，但是每个信号只会发送一帧
        参数说明：
            :param signals: 需要发送的信号和对应值组成的字典， 例如： {signal_name: signal_value}
            :param kwargs: 关键字参数，例如：signal_name=signal_value
        异常说明：发送失败
        返回值：None
        """
        if not self.__bus:
            raise CanOperationError(f"The BUS is not instantiated.Please call the 'connect' method "
                                    f"to instantiate the BUS and try again")
        signals = signals + (kwargs,)
        if not signals:
            raise ValueError("At least one signal name-value pair should be passed in.")
        msg_sgn_dict = self._divide_signal_names_values_into_groups(signals)
        for msg_name, sgn_dict in msg_sgn_dict.items():
            message = self.__db.get_message_by_name(msg_name)
            sgn_dict = self.__update_signals_without_e2e(message, sgn_dict)
            sgn_dict = self.__update_signals_with_e2e(message, sgn_dict)
            raw_message = RawMessage(arbitration_id=message.frame_id,
                                     is_rx=False,
                                     channel=self.bus.channel_info,
                                     is_remote_frame=False,
                                     is_fd=message.is_fd,
                                     is_extended_id=message.is_extended_frame,
                                     data=message.encode(data=sgn_dict))
            logger.info(f"Sending raw message: {raw_message}")
            try:
                self.bus.send(raw_message)
                logger.info(f"Sending raw message: {raw_message}")
            except Exception as e:
                logger.error(e)

    def send_signals(self, *signals: dict, **kwargs: Any) -> None:
        """
        功能说明：开始周期性发送信号，可发送一个或多个信号
        参数说明：
            :param signals: 需要发送的信号和对应值组成的字典， 例如： {signal_name: signal_value}
            :param kwargs: 关键字参数，例如：signal_name=signal_value
        异常说明：无
        返回值：None
        """
        if not self.__bus:
            raise CanOperationError(f"The BUS is not instantiated.Please call the 'connect' method "
                                    f"to instantiate the BUS and try again")
        signals = signals + (kwargs,)
        if not signals:
            raise ValueError("At least one signal name-value pair should be passed in.")
        msg_sgn_dict = self._divide_signal_names_values_into_groups(signals)
        for msg_name, sgn_dict in msg_sgn_dict.items():
            message = self.__db.get_message_by_name(msg_name)
            cycle_time = message.cycle_time / 1000 if message.send_type == "cyclic" else 0.1
            sgn_dict = self.__update_signals_without_e2e(message, sgn_dict)
            raw_messages = list()
            self.init_counter = True
            for i in range(15):
                sgn_dict = self.__update_signals_with_e2e(message, sgn_dict)
                self.init_counter = False
                raw_message = RawMessage(arbitration_id=message.frame_id,
                                         is_rx=False,
                                         channel=self.bus.channel_info,
                                         is_remote_frame=False,
                                         is_fd=message.is_fd,
                                         is_extended_id=message.is_extended_frame,
                                         data=message.encode(data=sgn_dict))
                logger.info(f"Sending raw message: {raw_message}")
                raw_messages.append(raw_message)
            try:
                self.__bus.send_periodic(msgs=raw_messages, period=cycle_time)
            except Exception as ex:
                logger.error(f"Because {ex}, send message failed,please try again.")

    def send_messages_once(self,
                           *messages: dict,
                           is_fd: bool = False,
                           is_extended_frame: bool = False,
                           is_remote_frame: bool = False,
                           **kwargs: Any
                           ) -> None:
        """
        功能说明：发送一帧。可以同时发多个报文，但是每个报文只会发送一帧
        参数说明：
            :param messages: 需要发送的报文id和对应data组成的字典，格式为{can_id: data}
            :param is_fd: 发送的报文是否是canfd，True则是canfd，False则是can
            :param is_extended_frame: 发送的报文是否是扩展帧，默认为False，即为标准帧
            :param kwargs: 关键字参数，例如can_id=data
        异常说明：无
        返回值：None
        """
        if not self.__bus:
            raise CanOperationError(f"The BUS is not instantiated.Please call the 'connect' method "
                                    f"to instantiate the BUS and try again")
        if not messages and not kwargs:
            raise ValueError("At least one msg can_id-data pair should be passed in.")
        full_can_id_data_tuple = messages + (kwargs,)
        for full_can_id_data in full_can_id_data_tuple:
            for can_id, data in full_can_id_data.items():
                try:
                    can_id = int(can_id, 16)
                except:
                    can_id = can_id

                data = [int(i, 16) for i in data.split(":")]
                raw_message = RawMessage(arbitration_id=can_id,
                                         is_rx=False,
                                         channel=self.bus.channel_info,
                                         is_remote_frame=is_remote_frame,
                                         is_fd=self.__bus.fd and is_fd,
                                         is_extended_id=is_extended_frame,
                                         data=data)
                logger.info(f"Sending raw message: {raw_message}")
                self.__bus.send(raw_message)

    def send_messages(self,
                      *messages: dict,
                      is_fd: bool = False,
                      is_extended_frame: bool = False,
                      is_remote_frame: bool = False,
                      cycle_time: float = None,
                      **kwargs: Any
                      ) -> None:
        """
        功能说明：周期性发送一个或多个报文
        参数说明：
            :param messages: 需要发送的报文id和对应data组成的字典，格式为{can_id: data}
            :param is_fd: 发送的报文是否是canfd，True则是canfd，False则是can
            :param is_extended_frame: 发送的报文是否是扩展帧，默认为False，即为标准帧
            :param cycle_time: 报文的发送周期
            :param kwargs: 关键字参数，例如can_id=data
        异常说明：无
        返回值：None
        """
        if not self.__bus:
            raise CanOperationError(f"The BUS is not instantiated.Please call the 'connect' method "
                                    f"to instantiate the BUS and try again")
        if not messages and not kwargs:
            raise ValueError("At least one msg can_id-data pair should be passed in.")
        full_can_id_data_tuple = messages + (kwargs,)
        for full_can_id_data in full_can_id_data_tuple:
            for can_id, data in full_can_id_data.items():

                try:
                    can_id = int(can_id, 16)
                except:
                    can_id = can_id

                data = [int(i, 16) for i in data.split(":")]
                old_cycle_time = cycle_time
                if self.db and not cycle_time:   
                    try:
                        frame = self.db.get_message_by_frame_id(can_id)
                        cycle_time = frame.cycle_time / 1000 if frame.send_type == "cyclic" else 0.1
                    except KeyError:
                        cycle_time = 0.1
                raw_message = RawMessage(arbitration_id=can_id,
                                         is_rx=False,
                                         channel=self.bus.channel_info,
                                         is_remote_frame=is_remote_frame,
                                         is_fd=self.__bus.fd and is_fd,
                                         is_extended_id=is_extended_frame,
                                         data=data)

                logger.info(f"Sending raw message: {raw_message}")

                try:
                    self.__bus.send_periodic(msgs=raw_message, period=cycle_time)
                except CanOperationError:
                    logger.error(f"Send message failed, please try again")
                cycle_time = old_cycle_time

    def stop_sending(self) -> None:
        """
        功能说明：停止发送报文或信号
        参数说明：无
        异常说明：无
        返回值：None
        """
        if self.bus:
            self.__sending_messages.clear()
            self.__sending_raw_datas.clear()
            self.sending_dict_datas.clear()
            self.bus.stop_all_periodic_tasks()
            logger.info("Stop sending data")
        else:
            logger.error(f"CAN bus is not connected")

    def receive_signals_once(self, *signals: str, timeout: float = None) -> typing.Optional[dict]:
        """
        receive one or more signals (signals must be in the same message)
        功能说明：接收同一个报文中的一个/多个信号一次，接收到预期信号后就停止接收
        参数说明：
            :param signals: 想要接收的同一个报文中的信号名
            :param timeout: 接收信号的超时时间
        异常说明：无
        返回值：received_sgn_dict 接收到的信号字典，格式为{sgn_name, sgn_value}
        """
        if not (self.__bus and self.__notifier):
            raise CanOperationError(f"The BUS is not instantiated.Please call the 'connect' method "
                                    f"to instantiate the BUS and try again")
        sgn_set = set(signals)
        new_sgn_list = []
        message_list = []
        listener = BufferedReader()
        self.__notifier.add_listener(listener)
        for sgn in sgn_set:
            try:
                message = self.__db.get_message_by_signal(sgn)
                message_list.append(message)
            except:
                logger.error(f"Can't find the message of sgn: "
                             f"{sgn} in database {self.__db_path}, stop receiving.")
                listener.buffer.queue.clear()
                return None
            else:
                new_sgn_list.append(sgn)
        message_set = set(message_list)
        if len(message_set) != 1:
            logger.error("Signals should be in same message.")
            listener.buffer.queue.clear()
            return None
        new_message_list = list(message_set)
        logger.info(f"Expected signals: {new_sgn_list}")
        logger.info("Start receiving signals...")
        received_sgn_dict = dict()
        start_time = time.time()
        while True:
            raw_message = listener.get_message()
            if not raw_message:
                if timeout:
                    if time.time() - start_time > timeout:
                        break
                continue
            if new_message_list[0].frame_id == raw_message.arbitration_id:
                sgn_dict = new_message_list[0].decode(raw_message.data)
                logger.debug(f"Received message dict:{sgn_dict}")
                for name, value in sgn_dict.items():
                    for sgn in sgn_set:
                        if sgn == name:
                            sgn_object = self.__db.get_signal_by_name(name)
                            if sgn_object.choices:
                                value = sgn_object.choice_string_to_number(value)
                            received_sgn_dict.update({name: value})
                break
            if timeout:
                end_time = time.time()
                if end_time - start_time > timeout:
                    break
        self.__notifier.remove_listener(listener)
        logger.info(f"Received signals: {received_sgn_dict}")
        return received_sgn_dict

    def receive_signals(self, *signals: str, duration: float, **kwargs: Any) -> typing.Optional[List[dict]]:
        """
        功能说明：持续接收信号，可接收一个或多个信号
        参数说明：
            :param signals: 想要接收的信号名，格式为sgn1, sgn2, 注意必须传至少一个信号名
            :param duration: 接收信号的最长时长
            :param kwargs: 目前是可以传一个num=xx，如num=1000, 表示接收到1000条messages就停止接收，也用于后续扩展
        异常说明：无
        返回值：signal_list 接收到的信号列表，格式为[{sgn_name1: sgn_value1}, {sgn_name2: sgn_value2},...]
        """
        if not (self.__bus and self.__notifier):
            raise CanOperationError(f"The BUS is not instantiated.Please call the 'connect' method "
                                    f"to instantiate the BUS and try again")
        sgn_set = set(signals)
        listener = BufferedReader()
        self.__notifier.add_listener(listener)
        raw_message_list = []
        signal_list = []
        message_list = []
        exp_sgn_list = []
        if not sgn_set:
            logger.error(
                "No signal name has been received, please make sure you've passed in at least one siganl name.")
            listener.buffer.queue.clear()
            return None
        for sgn in sgn_set:
            try:
                message = self.__db.get_message_by_signal(sgn)
            except:
                logger.error(f"Can't find the message of sgn: "
                             f"{sgn} in database {self.__db_path}")
            else:
                message_list.append(message)
                exp_sgn_list.append(sgn)
        if not message_list:
            logger.error("None of your signal names is valid, stop receiving.")
            listener.buffer.queue.clear()
            return None
        logger.info(f"Expected signals: {exp_sgn_list}")
        logger.info("Start receiving signals...")
        start_time = time.time()
        count = 0
        try:
            while True:
                raw_message = listener.get_message()
                if not raw_message:
                    if duration:
                        if time.time() - start_time > duration:
                            break
                    continue
                count += 1
                for message in message_list:
                    received_sgn_dict = {}
                    if message.frame_id == raw_message.arbitration_id:
                        logger.debug(f"Receive RawMessage: {raw_message}")
                        if raw_message not in raw_message_list:
                            raw_message_list.append(raw_message)
                        try:
                            sgn_dict = message.decode(raw_message.data)
                        except Exception as ex:
                            logger.error(f"Unable to parse message:{raw_message} \npossible mismatch between "
                                         f"type of can channel {raw_message.channel} and dbc: {self.db_path}")
                            continue
                        logger.debug(f"Received message dict:{sgn_dict}")

                        for name, value in sgn_dict.items():

                            for sgn in exp_sgn_list:
                                if sgn == name:
                                    sgn_object = self.__db.get_signal_by_name(name)
                                    if sgn_object.choices:
                                        value = sgn_object.choice_string_to_number(value)
                                    received_sgn_dict.update({name: value})
                    if received_sgn_dict and received_sgn_dict not in signal_list:
                        signal_list.append(received_sgn_dict)
                end_time = time.time()
                if duration:
                    if end_time - start_time > duration:
                        break
                if kwargs.get("num"):
                    if count == kwargs.get("num"):
                        break
        except KeyboardInterrupt:
            self.__notifier.remove_listener(listener)
            logger.debug(f"Received raw messages: {raw_message_list}")
            logger.info(f"Received signals: {signal_list}")
            return signal_list
        self.__notifier.remove_listener(listener)
        logger.debug(f"Received raw messages: {raw_message_list}")
        logger.info(f"Received signals: {signal_list}")
        return signal_list

    def receive_message_once(self, can_id: Union[int, str] = None, timeout: float = None
                             ) -> typing.Optional[RawMessage]:
        """
        功能说明：接收一个报文，接收到预期报文后就停止接收，默认值为None，则接收到第一个报文就停止接收
        参数说明：
            :param can_id: 想要接收的报文的id
            :param timeout: 接收报文的时长
        异常说明：无
        返回值：received_raw_message 接收到的裸数据
        """
        if not (self.__bus and self.__notifier):
            raise CanOperationError(f"The BUS is not instantiated.Please call the 'connect' method "
                                    f"to instantiate the BUS and try again")
        if can_id:
            try:
                can_id = int(can_id, 16)
            except:
                can_id = can_id

        listener = BufferedReader()
        self.__notifier.add_listener(listener)
        received_raw_message = None
        start_time = time.time()
        while True:

            raw_message = listener.get_message()
            if not raw_message:
                if timeout:
                    if time.time() - start_time > timeout:
                        break
                continue
            else:
                if not can_id:
                    received_raw_message = raw_message
                    break

                if raw_message.arbitration_id == can_id:
                    received_raw_message = raw_message
                    break

            if timeout:
                if time.time() - start_time > timeout:
                    break
        self.__notifier.remove_listener(listener)
        logger.info(f"Received raw message: {received_raw_message}")
        return received_raw_message

    def receive_messages(self, *can_ids: Union[int, str], duration: float = None, **kwargs: Any
                         ) -> typing.Set[RawMessage]:
        """
        功能说明：持续接收报文，可接收一个或多个报文
        参数说明：
            :param can_ids: 想要接收报文id，格式为can_id1, can_id2, 不传入该参数则接收全部报文
            :param duration: 接收裸数据的最长时长
            :param kwargs: 目前是可以传一个num=xx，如num=1000, 表示接收到1000条messages就停止接收，也用于后续扩展
        异常说明：无
        返回值：raw_message_list 接收到的裸数据列表
        """
        if not (self.__bus and self.__notifier):
            raise CanOperationError(f"The BUS is not instantiated.Please call the 'connect' method "
                                    f"to instantiate the BUS and try again")
        can_id_list = []
        for can_id in set(can_ids):
            if str(can_id).startswith('0x'):
                can_id_list.append(int(can_id, 16))
            else:
                can_id_list.append(int(can_id))
        listener = BufferedReader()
        self.__notifier.add_listener(listener)
        count = 0
        raw_message_list = set()
        start_time = time.time()
        while True:
            raw_message = listener.get_message()
            if not raw_message:
                if duration:
                    if time.time() - start_time > duration:
                        break
                continue
            count += 1
            if can_id_list:
                for can_id in can_id_list:
                    if raw_message.arbitration_id == can_id:
                        logger.info(f"Received raw message: {raw_message}")
                        raw_message_list.add(raw_message)
            else:
                logger.info(f"Received raw message: {raw_message}")
                raw_message_list.add(raw_message)

            end_time = time.time()
            if duration:
                if end_time - start_time > duration:
                    break
            if kwargs.get("num"):
                if count == kwargs.get("num"):
                    break
        self.__notifier.remove_listener(listener)
        return raw_message_list

    def modify_sending_signals(self, *signals: dict, **kwargs: Any) -> None:
        """
        功能说明：修改周期性信号
        参数说明：
            :param signals: 需要修改的信号和对应值组成的字典， 例如： {signal_name: signal_value}，注意要修改的信号必然是先前发送的
            :param kwargs: 关键字参数，例如signal_name=signal_value
        异常说明：无
        返回值：None
        """
        if not (signals or kwargs):
            raise ValueError("At least one msg can_id-data pair should be passed in.")
        signals = signals + (kwargs,)
        msg_sgn_dict = self._divide_signal_names_values_into_groups(signals)
        for task in self.bus.periodic_tasks:
            raw_messages = list()
            for raw_message in copy.deepcopy(task.messages):
                for msg_name, sgn_dict in msg_sgn_dict.items():
                    message = self.__db.get_message_by_name(msg_name)
                    if message.frame_id == task.arbitration_id:
                        full_signal_dict = message.decode(raw_message.data)
                        full_signal_dict.update(sgn_dict)
                        raw_message.data = message.encode(data=full_signal_dict)
                        raw_messages.append(raw_message)
                        logger.info(f"Modify sending raw message: {raw_message}")
            task.modify_data(raw_messages)

    def modify_sending_signals_callback(self, *signals: dict, **kwargs: Any) -> None:
        """
        功能说明：修改周期性信号
        参数说明：
            :param signals: 需要修改的信号和对应值组成的字典， 例如： {signal_name: signal_value}，注意要修改的信号必然是先前发送的
            :param kwargs: 关键字参数，例如signal_name=signal_value
        异常说明：无
        返回值：None
        """
        if not signals and not kwargs:
            raise ValueError("At least one msg can_id-data pair should be passed in.")
        logger.info(f"Start modifying signal data......")
        signal_dict_tuple = signals + (kwargs,)
        new_sgn_dict = {}
        for sgn_dict in signal_dict_tuple:
            for sgn_name, sgn_value in sgn_dict.items():
                new_sgn_dict.update({sgn_name: sgn_value})
        self.__modified_data = self._divide_signal_names_values_into_groups(new_sgn_dict)

    def _divide_signal_names_values_into_groups(self, signals: typing.Tuple[dict]) -> dict:
        msg_sgn_dict = dict()
        for signal in signals:
            msg_name_set = set()
            self.__sent_signals.update(signal)
            for sgn_name in signal.keys():
                try:
                    message = self.__db.get_message_by_signal(sgn_name)
                    msg_name_set.add(message.name)
                except:
                    logger.error(f"Can't find the message with Signal: "
                                 f"{sgn_name} in database {self.__db_path}")

            for msg_name in msg_name_set:
                new_sgn_dict = dict()
                for sgn_name, sgn_value in signal.items():
                    message = self.__db.get_message_by_signal(sgn_name)
                    if msg_name == message.name:
                        new_sgn_dict.update({sgn_name: sgn_value})
                logger.info(f"Send message: {msg_name}, signals: {new_sgn_dict}")
                msg_sgn_dict.update({msg_name: new_sgn_dict})

        return msg_sgn_dict

    def listen_messages(self, *args: typing.Union[int, str]) -> None:
        """
        功能说明：持续监听报文/信号，可监听一个或多个
        参数说明：
            :param args: 想要接收报文id，格式为can_id1, can_id2，或者信号名, 不传入该参数则接收全部报文
        异常说明：无
        返回值：raw_message_list 接收到的裸数据列表
        """
        if not (self.__bus and self.__notifier):
            raise CanOperationError(f"The BUS is not instantiated.Please call the 'connect' method "
                                    f"to instantiate the BUS and try again")
        filters = list()
        for arg in set(args):
            if str(arg).startswith('0x'):
                can_id = int(arg, 16)
            else:
                try:
                    can_id = int(arg)
                except:
                    try:
                        message = self.__db.get_message_by_signal(arg)
                    except:
                        logger.warning(f"Can't find the message of sgn: {arg} in database {self.__db_path}")
                        continue
                    else:
                        can_id = message.frame_id

            can_filter = {"can_id": can_id,
                          "can_mask": 0x1fffffff,
                          "extended": False if can_id <= 0x7ff else True}
            filters.append(can_filter)
        self.bus.filters = filters
        self.__listener = BufferedReader()
        self.__notifier.add_listener(self.__listener)

    def get_received_raw_messages(self, num: int = 0) -> queue.SimpleQueue:
        new_received_raw_message_queue = queue.SimpleQueue()
        if self.__listener:
            size = self.__listener.buffer.qsize()
            if not num or size < num:
                logger.warning(f"Received raw messages total is {size},but expect num is {num},"
                               f"this time return num is {size}")
                num = size
            for i in range(num):
                new_received_raw_message_queue.put(self.__listener.buffer.get())
        return new_received_raw_message_queue

    def get_received_signals(self, num: int = 0) -> queue.SimpleQueue:
        new_received_signal_queue = queue.SimpleQueue()
        if self.__listener:
            size = self.__listener.buffer.qsize()
            if not num or size < num:
                logger.warning(f"Received raw messages total is {size},but expect num is {num},"
                               f"this time return num is {size}")
                num = size
            for i in range(num):
                parsed_dict = dict()
                m = self.__listener.buffer.get()
                message_dict = dict()
                try:
                    frame = self.db.get_message_by_frame_id(m.arbitration_id)
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
                                     f"type of can channel {m.channel} and dbc: {self.db_path}")
                    else:
                        logger.exception(ex)
                    parsed_dict[m.timestamp] = message_dict
                new_received_signal_queue.put(parsed_dict)
        return new_received_signal_queue

    def __update_signals_without_e2e(self, message: Message, sgn_dict: dict) -> typing.Dict:
        """
        功能说明：首次更新CAN信号字典值，不带E2E
        参数说明：
            :param message: Message类型，从CAN数据库中解析到的CAN Frame对象
            :param sgn_dict: dict类型，格式为：{signal_name: signal_value}
        异常说明：无
        返回值：返回更新后的该Frame下所有信号字典，
               格式：{signal_name1: signal_value1,signal_name2: signal_value2,...}
        """
        updated_sgn_dict, ub_sgn_dict, unused_sgn_dict = dict(), dict(), dict()
        for sgn_name in sgn_dict.keys():
            if sgn_name.endswith("_UB"):
                ub_sgn = message.get_signal_by_name(sgn_name)
                ub_sgn_dict.update({ub_sgn.name: 1})

        for sgn in message.signals:
            if sgn.name not in updated_sgn_dict.keys():
                if sgn.name.endswith("_UB"):
                    ub_sgn_dict.update({sgn.name: 1})
                else:
                    import decimal
                    if sgn.name in sgn_dict.keys():
                        sgn_value = sgn_dict[sgn.name]
                        if isinstance(sgn_value, (int, float)):
                            sgn_dict[sgn.name] = (sgn_dict[sgn.name] * sgn.scale + sgn.offset)
                    else:
                        if isinstance(sgn.initial, decimal.Decimal):
                            sgn_default_value = (sgn.scale * float(sgn.initial) + sgn.offset)
                        else:
                            sgn_default_value = 0
                        unused_sgn_dict.update({sgn.name: sgn_default_value})
        updated_sgn_dict.update(ub_sgn_dict)
        updated_sgn_dict.update(unused_sgn_dict)
        updated_sgn_dict.update(sgn_dict)

        return updated_sgn_dict

    def __update_signals_with_e2e(self, message: Message, sgn_dict: dict) -> typing.Dict:
        """
        功能说明：预更新CAN信号字典值，带E2E
        参数说明：
            :param message: Message类型，从can数据库中解析到的can Frame对象
            :param sgn_dict: dict类型，格式为：{signal_name: signal_value}
        异常说明：无
        返回值：返回更新后的该Frame下所有信号字典，
               格式：{signal_name1: signal_value1,signal_name2: signal_value2,...}
        """
        for sgn_name in sgn_dict.keys():
            if sgn_name.endswith("Chks") and sgn_name not in self.__sent_signals:
                signal_group = message.get_signal_group_by_signal_name(sgn_name)
                if not signal_group:
                    logger.error(f"Signal:{sgn_name} not found signal group in {self.__db_path}.")
                signal_names = signal_group.signal_names
                chks_sgn = message.get_signal_by_name(sgn_name)
                cntr_sgn_name = sgn_name[:-4] + "Cntr"
                counter = sgn_dict.get(cntr_sgn_name)
                if counter is None:
                    logger.error(f"{sgn_dict} not have {cntr_sgn_name} signal, please check and try again.")
                    continue
                if counter == 0 and self.init_counter:
                    counter = -1
                counter += 1
                counter = int(counter % 15)
                sgn_dict[cntr_sgn_name] = counter
                data_id_hex = chks_sgn.data_id
                try:
                    data_id = int(data_id_hex, 16)
                except TypeError:
                    if set(signal_names) & self.__sent_signals:
                        logger.warning(f"The signal {chks_sgn} does not contain data id for e2e,"
                                       f"Please check whether the sdb file is correct and try again,"
                                       f"The value of this {sgn_name} signal remains unchanged here")
                    continue
                except ValueError:
                    if set(signal_names) & self.__sent_signals:
                        logger.error(f"The data id of this signal {chks_sgn} is {data_id_hex},"
                                     f"Please check whether the sdb file is correct and try again,"
                                     f"The value of this {sgn_name} signal remains unchanged here")
                    continue
                sig_value_length = list()
                signal_names.sort()
                for signal_name in signal_names:
                    sgn = message.get_signal_by_name(signal_name)
                    if signal_name.endswith("Chks") or signal_name.endswith("Cntr"):
                        continue
                    if signal_name in sgn_dict.keys():
                        value = sgn_dict[signal_name]
                        if isinstance(value, (str, NamedSignalValue)):
                            value = sgn.choice_string_to_number(value)
                        value = (value - sgn.offset) / sgn.scale
                    else:
                        value = sgn.initial
                    sig_value_length.append((int(value), sgn.length))
                checksum = e2e_crc_data(data_id=data_id, counter=counter, sig_value_length=sig_value_length)

                sgn_dict[sgn_name] = checksum
        return sgn_dict

    def modify_ecu_sending_signals(self, *signals: dict, send_bus: BusABC = None, **kwargs: Any) -> None:
        """
        功能说明：接收某ecu发送的信号，并针对指定的信号值做修改，然后再发送修改后的和未修改的全部信号
        参数说明：
            :param signals: 需要修改的信号和对应值组成的字典， 例如： {signal_name: signal_value}，
                            注意要修改的信号必须是ecu正在发送的
            :param send_bus: 修改后的信号发送总线, 若为None或者不是BusABC(子类)实例，默认使用接收总线作为发送总线
            :param kwargs: 关键字参数，例如signal_name=signal_value
        异常说明：无
        返回值：None
        """
        import threading
        if not (signals or kwargs):
            raise ValueError("At least one msg 'can_id:data' pair should be passed in.")
        signals = signals + (kwargs,)
        msg_sgn_dict = self._divide_signal_names_values_into_groups(signals)
        listener = BufferedReader()
        self.__notifier.add_listener(listener)
        bus = send_bus if send_bus and isinstance(send_bus, BusABC) else self.bus

        def send_handler():
            while True:

                raw_message = listener.get_message()
                if not raw_message or raw_message.arbitration_id == 1:
                    continue

                try:
                    raw_message.channel = bus.channel_info
                    frame = self.db.get_message_by_frame_id(raw_message.arbitration_id)
                    sgn_dict = msg_sgn_dict.get(frame.name)
                    if sgn_dict:
                        full_signal_dict = frame.decode(raw_message.data)
                        full_signal_dict.update(sgn_dict)
                        raw_message.data = frame.encode(data=full_signal_dict)
                        logger.info(f"Modify ecu sending raw message: {raw_message}")
                except Exception as ex:
                    if raw_message.arbitration_id == 1:
                        logger.warning(f"Unable to parse message:{raw_message}")
                    elif isinstance(ex, (KeyError, bitstruct.Error)):
                        logger.error(f"Unable to parse message:{raw_message} \npossible mismatch between "
                                     f"type of can channel {raw_message.channel} and dbc: {self.db_path}")

                bus.send(raw_message)
        threading.Thread(name=f"canapp.controller.modify_ecu_sending for bus '{bus.channel_info}'", target=send_handler, daemon=True).start()

    def start_receiving(self) -> bool:
        self.__notifier = Notifier(self.__bus, [])
        return True

    def stop_receiving(self) -> bool:
        self.__notifier.stop()
        self.__notifier = None
        return True
