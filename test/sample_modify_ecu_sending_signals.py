import time
import logging
from pathlib import Path
from geelytest_can import CanController


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


def modify_ecu_sending_signals():  
    
    # 实例化一个控制器去发送裸数据
    # "BodyCAN"：控制器名字
    # "pcan"： 控制器采用的硬件设备类型（如PEAK公司的pcan）
    # 1: 控制器使用的硬件设备通道号（1, 2, ... , 16）
    # "v0.6.5/SDB22R04_BGM_BodyCAN_220923_Release.dbc"：dbc文件路径
    sender = CanController(
        "BodyExposedCAN", 
        "pcan", 
        "PCAN_USBBUS1",
        Path(__file__).parent / "resources" / "SDB22436_L946_ADCU9_ZCUDM_BodyExposedCAN_250124_PNC.dbc"
    )
    
    # 连接硬件
    sender.connect()
    
    # 启动线程，开始发送周期性信号
    # "ActnOfLedCornrgLampLe"： 来自于dbc文件的信号名； 3：信号值
    # "ActnOfLedDaytiRunngLamp"： 来自于dbc文件的信号名； 2：信号值
    sender.send_signals_once({"ActnOfLedCornrgLampLe": 1}, {"ActnOfLedDaytiRunngLamp": 1})
    
    # 等待5秒
    time.sleep(5)
    
    # 修改发送的信号值
    sender.modify_ecu_sending_signals({"ActnOfLedCornrgLampLe": 0}, {"ActnOfLedDaytiRunngLamp": 0})
    
    # 等待5秒
    time.sleep(5)
    
    # 停止发送信号
    sender.stop_sending()
    
    # 断开硬件
    sender.disconnect()
    
    
if __name__ == "__main__":
    modify_ecu_sending_signals()
