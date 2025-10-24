import time
import logging
from pathlib import Path
from can import Bus as CanBus
from can import CanFDBitTiming
from geelytest_can import CanLogManager
from geelytest_can import CanController


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
 

# 对willow平台暴露的接口和使用方式（仅供参考）
def listen_bus_data():
    
    # 实例化一个控制器
    # "ConnectivityCANFD"：控制器名字
    # "pcan"： 控制器采用的硬件设备类型（如PEAK公司的pcan）
    # 1: 控制器使用的硬件设备通道号（1, 2, ... , 16）
    # 可以传dbc文件路径或者自己实例化好的bus，但是以传入的dbc优先级最高
    # 实例化一个bus
    # bus1 = CanBus(interface="vector", channel=1, bit_timing=CanFDBitTiming.FD_500000_2000000)
    # bus1 = CanBus(interface="pcan", channel="PCAN_USBBUS1", bit_timing=CanFDBitTiming.FD_500000_2000000)
    # receiver1 = CanController(
    #     "BodyExposedCAN",
    #     "vector", 
    #     1,
    #     Path(__file__).parent / "resources" / "SDB22436_L946_ADCU9_ZCUDM_BodyExposedCAN_250124_PNC.dbc",
    #     bus=bus1
    # )
    receiver1 = CanController(
        "ZCU_CANFD2",
        "pcan", 
        "PCAN_USBBUS1",
        Path(__file__).parent / "resources" / "SDB22436_L946_ADCU9_ZCUD_ZCU_CANFD2_250124_PNC.dbc",
        # bus=bus1
    )
    # 连接硬件，并实例化Notify对象
    receiver1.connect()

    # 实例化抓取log管理对象
    # manager = CanLogManager([bus1])
    # 开始log录制
    # manager.start_logging(f"demo{int(time.time()*1000)}.asc")
    receiver1.listen_messages()  # 可以接收裸数据/信号，接收时长全款自己后面sleep
    time.sleep(10)
    received_raw_messages1 = receiver1.get_received_signals(10)  # 获取解析后的数据
    logger.info(received_raw_messages1.qsize())
    time.sleep(1)
    received_raw_messages2 = receiver1.get_received_raw_messages(5)
    logger.info(received_raw_messages2.qsize())
    time.sleep(1)
    received_raw_messages3 = receiver1.get_received_signals()  # 获取解析后的数据
    logger.info(received_raw_messages3.qsize())
    time.sleep(1)
    received_raw_messages4 = receiver1.get_received_raw_messages(5)
    logger.info(received_raw_messages4.qsize())
    time.sleep(1)

    # 停止log录制
    # manager.stop_logging()
    # 断开硬件，并停止接收，并清空buffer
    receiver1.disconnect()
    time.sleep(5)
    received_raw_messages5 = receiver1.get_received_raw_messages()
    logger.info(received_raw_messages5.qsize())
    
    
if __name__ == "__main__":
    listen_bus_data()
        