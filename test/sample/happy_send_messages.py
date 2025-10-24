import signal
import sys
import logging
import time
from jidutest_can.canapp import CanController
from jidutest_can.canapp import CanLogManager


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
CAN_CONFIG_LIST = [
    {
        "name": "BodyCAN",
        "interface": "pcan",
        "channel": 3,
        "db_path": r"/root/pengtao/jidusdb/02-DBC/AddNmSigs/SDB22R05_BodyCAN_221125_Release.dbc",
        "signal_list": (
            {0X53F: "3F:40:FF:FF:FF:FF:FF:FF"},
        ),
        "is_fd": False
    },
    {
        "name": "info_can",
        "interface": "pcan",
        "channel": 1,
        "db_path": r"/root/pengtao/jidusdb/02-DBC/AddNmSigs/SDB22R05_InfoCANFD_221125_Release.dbc",
        "signal_list": (
            {120: "FF:00:00:00:00:00:21:00"},
        ),
        "is_fd": True
    },

    {
        "name": "ConnectCANFD",
        "interface": "pcan",
        "channel": 2,
        "db_path": r"/root/pengtao/jidusdb/02-DBC/AddNmSigs/SDB22R05_ConnectivityCANFD_221205_Release.dbc",
        "signal_list": (
            {165: "C0:00:00:00:00:00:00:00"},
        ),
        "is_fd": True
    },
]


def start_send_msgs():
    can_controllers = list()
    can_buses = list()
    for can_config in CAN_CONFIG_LIST:
        logger.info(f'start send message {can_config=}')
        can_controller = CanController(
            name=can_config["name"],
            interface=can_config["interface"],
            channel=can_config["channel"],
            db_path=can_config["db_path"]
        )
        can_controller.connect()
        can_buses.append(can_controller.bus)
        can_controller.send_messages(*can_config["signal_list"], is_fd=can_config["is_fd"])
        can_controllers.append(can_controller)

    can_log_manager = CanLogManager(can_buses)
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
        for can_controller in can_controllers:
            time.sleep(1)
            notifier = can_controller.notifier
            periodic_tasks = set(can_controller.bus.periodic_tasks.copy())
            for t in periodic_tasks:
                if t.exception:
                    can_controller.notifier.remove_listener(can_log_manager.logger_listener)
                    can_controller.disconnect()
                    try:
                        can_controller.connect()
                        can_controller.notifier.add_listener(can_log_manager.logger_listener)
                    except Exception as ex:
                        logger.warning(ex)
                        time.sleep(0.1)
                        can_controller.bus.periodic_tasks.extend(periodic_tasks)
                        continue
                    for task in periodic_tasks:
                        logger.info(f"starting {task}")
                        task.start()
                        task.exception = None
                        can_controller.bus.periodic_tasks.append(task)
            if notifier.exceptions:
                for _bus in notifier.exceptions.copy():
                    _bus.reset()
                    notifier.add_bus(_bus)
                    notifier.exceptions.pop(_bus)


if __name__ == "__main__":
    start_send_msgs()
