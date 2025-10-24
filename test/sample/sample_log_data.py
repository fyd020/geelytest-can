import time
import logging
from jidutest_can import CanBus
from jidutest_can.can import PCANFD_500000_2000000
from jidutest_can.canapp import CanLogManager


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


# 录制数据
def log_can_data():
    # 实例化一个控制器去录制数据
    # "BodyCAN"：控制器名字
    # "pcan"： 控制器采用的硬件设备类型（如PEAK公司的pcan）
    # 1: 控制器使用的硬件设备通道号（1, 2, ... , 16）
    # "v0.6.5/SDB22R04_BGM_BodyCAN_220923_Release.dbc"：dbc文件路径
    bus = CanBus(interface="pcan", channel=1, fd=True, **PCANFD_500000_2000000)

    # 实例化一个CAN日志管理器, 传入的参数为上面实例化的控制器
    manager = CanLogManager(bus)
    # 开始记录数据, 
    # "C:\demo.blf"为需要记录数据的文件路径
    # 50000000为单个文件的大小，单位为byte，当超过这个大小后会自动生成一个新文件
    manager.start_logging(f"demo{int(time.time() * 1000)}.asc")
    # 记录4s
    time.sleep(5)
    # 停止记录数据
    manager.stop_logging()
    bus.shutdown()


if __name__ == "__main__":
    log_can_data()
