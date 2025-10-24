import signal
import sys
import logging
import time
from can import Bus
from geelytest_can import CanController
from geelytest_can import CanLogManager


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
# CAN_CONFIG_LIST = [
#     {
#         "name": "DTS_Tester",
#         "interface": "smartvci",
#         "channel": 1,
#         "db_path": r"/root/dading/jidutest-can/test_smartvci/resources/DTSDI_C01_B02.dbc",
#         "signal_list": (
#             {0xd013: "00:FF:00:00:FF:FF:00:00"},
#         ),
#         "is_fd": False
#     }]

def start_send_msgs():
    can_controllers = list()
    can_buses = list()
    can_bus_1 = Bus(interface="vector", channel=1, bitrate=500000)
    # can_bus_2 = Bus(interface="pcan", channel=2, bitrate=500000)
    can_buses.append(can_bus_1)
    # can_buses.append(can_bus_2)

    can_controller_1 = CanController(
        name="DTS_Tester",
        interface="smartvci",
        channel=1,
        db_path=r"/root/dading/jidutest-can/test_smartvci/resources/DTSDO_C01_B03.dbc",
        bus=can_bus_1
    )
    can_controller_2 = CanController(
        name="DTS_Tester",
        interface="smartvci",
        channel=2,
        bus=can_bus_2
    )
    can_controllers.append(can_controller_1)
    can_controllers.append(can_controller_2)
    can_controller_1.connect()
    can_controller_2.connect()
    # can_controller_1.send_messages({0xd013: "00:FF:00:00:FF:FF:00:00"}, is_fd=False)
    # 发送一帧，（可以传多个信号，但是每个信号对应的报文只发送一帧）
    # "DoorOpenerPassReqTrigSrc"： 来自于dbc文件的信号名； 3：信号值
    # "DoorOpenerLeReReqDoorOpenerReq2"： 来自于dbc文件的信号名； 2：信号值
    can_controller_1.send_signals({"DTSDO_Channel_01_Output_Enable": True, "DTSDO_Channel_01_Output": "High"})

    can_log_manager = CanLogManager(can_bus_2)
    can_log_manager.start_logging(f"test{int(time.time() * 1000)}.asc")

    def stop_logging(*args) -> None:
        can_log_manager.stop_logging()
        for controller in can_controllers:
            controller.disconnect()
            controller.bus.shutdown()
        logger.warning(f"Receive signal 'Ctrl + C', end the application\n")
        sys.exit(1)

    signal.signal(signal.SIGINT, stop_logging)

    while True:
        time.sleep(1)
        notifier = can_controller_2.notifier
        periodic_tasks = set(can_controller_2.bus.periodic_tasks.copy())
        for t in periodic_tasks:
            if t.exception:
                can_controller_2.notifier.remove_listener(can_log_manager.logger_listener)
                can_controller_2.disconnect()
                try:
                    can_controller_2.connect()
                    can_controller_2.notifier.add_listener(can_log_manager.logger_listener)
                except Exception as ex:
                    logger.warning(ex)
                    time.sleep(0.1)
                    can_controller_2.bus.periodic_tasks.extend(periodic_tasks)
                    continue
                for task in periodic_tasks:
                    logger.info(f"starting {task}")
                    task.start()
                    task.exception = None
                    can_controller_2.bus.periodic_tasks.append(task)
        if notifier.exceptions:
            for _bus in notifier.exceptions.copy():
                _bus.reset()
                notifier.add_bus(_bus)
                notifier.exceptions.pop(_bus)


if __name__ == "__main__":
    start_send_msgs()
