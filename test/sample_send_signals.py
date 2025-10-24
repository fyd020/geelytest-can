import time
import logging
from pathlib import Path
from geelytest_can import CanController


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


# 信号发送示例 (仅供参考)
def send_can_signals_once():
    
    # 实例化一个控制器去发送信号
    # "BodyCAN"：控制器名字
    # "pcan"： 控制器采用的硬件设备类型（如PEAK公司的pcan）
    # 1: 控制器使用的硬件设备通道号（1, 2, ... , 16）
    # "v0.6.5/SDB22R04_BGM_BodyCAN_220923_Release.dbc"：dbc文件路径
    sender = CanController(
        "BodyExposedCAN", 
        "pcan", # "vector" "pcan"
        "PCAN_USBBUS1", # "1" "PCAN_USBBUS1"
        Path(__file__).parent / "resources" / "SDB22436_L946_ADCU9_ZCUDM_BodyExposedCAN_250124_PNC.dbc"
    )
    
    # 连接硬件
    sender.connect()
    
    # 启动线程，开始发送周期性信号
    # "ActnOfLedCornrgLampLe"： 来自于dbc文件的信号名； 3：信号值
    # "ActnOfLedDaytiRunngLamp"： 来自于dbc文件的信号名； 2：信号值
    sender.send_signals_once({"ActnOfLedCornrgLampLe": 1}, {"ActnOfLedDaytiRunngLamp": 1})
    
    # 等待60秒
    time.sleep(3)
    
    # 停止发送信号
    sender.stop_sending()
    
    # 断开硬件
    sender.disconnect()
    

def send_can_signals():
    
    # 实例化一个控制器去发送信号
    # "BodyCAN"：控制器名字
    # "pcan"： 控制器采用的硬件设备类型（如PEAK公司的pcan）
    # 1: 控制器使用的硬件设备通道号（1, 2, ... , 16）
    # "v0.6.5/SDB22R04_BGM_BodyCAN_220923_Release.dbc"：dbc文件路径
    sender = CanController(
        "BodyExposedCAN", 
        "vector", # "vector" "pcan"
        "1", # "1" "PCAN_USBBUS1"
        Path(__file__).parent / "resources" / "SDB22436_L946_ADCU9_ZCUDM_BodyExposedCAN_250124_PNC.dbc"
    )
    
    # 连接硬件
    sender.connect()
    
    # 启动线程，开始发送周期性信号
    # "ActnOfLedCornrgLampLe"： 来自于dbc文件的信号名； 3：信号值
    # "ActnOfLedDaytiRunngLamp"： 来自于dbc文件的信号名； 2：信号值
    sender.send_signals({"ActnOfLedCornrgLampLe": 1}, {"ActnOfLedDaytiRunngLamp": 1})
    
    # 等待60秒
    time.sleep(60)
    
    # 停止发送信号
    sender.stop_sending()
    
    # 断开硬件
    sender.disconnect()
    
    
if __name__ == "__main__":
    send_can_signals_once()
    # send_can_signals()
