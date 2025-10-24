import logging
from pathlib import Path
from geelytest_can import CanController

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
 

# 信号接收示例 (仅供参考)
def receive_can_signals_once():
    
    # 实例化一个控制器去接收信号
    # "BodyCAN"：控制器名字
    # "pcan"： 控制器采用的硬件设备类型（如PEAK公司的pcan）
    # 2: 控制器使用的硬件设备通道号（1, 2, ... , 16）
    # "v0.6.5/SDB22R04_BGM_BodyCAN_220923_Release.dbc"：dbc文件路径
    receiver = CanController(
        "BodyExposedCAN", 
        "pcan", 
        "PCAN_USBBUS1",
        Path(__file__).parent / "resources" / "SDB22436_L946_ADCU9_ZCUDM_BodyExposedCAN_250124_PNC.dbc"
    )
       
    # 连接硬件
    receiver.connect()
    
    # 获取接收到的信号, "ActnOfLedCornrgLampLe", "ActnOfLedDaytiRunngLamp"是想要接收的信号，num为最大接收的裸数据数, duration是最大接收时长
    result = receiver.receive_signals_once("ActnOfLedCornrgLampLe", "ActnOfLedDaytiRunngLamp")
    
    # 打印接收到的信号，格式为[{信号一：值},{信号二：值}]
    print(result)
    
    # 断开硬件
    receiver.disconnect()
    
def receive_can_signals():
    
    # 实例化一个控制器去接收信号
    # "BodyCAN"：控制器名字
    # "pcan"： 控制器采用的硬件设备类型（如PEAK公司的pcan）
    # 2: 控制器使用的硬件设备通道号（1, 2, ... , 16）
    # "v0.6.5/SDB22R04_BGM_BodyCAN_220923_Release.dbc"：dbc文件路径
    receiver = CanController(
        "BodyExposedCAN", 
        "vector", 
        "1",
        Path(__file__).parent / "resources" / "SDB22436_L946_ADCU9_ZCUDM_BodyExposedCAN_250124_PNC.dbc"
    )
       
    # 连接硬件
    receiver.connect()
    
    # 获取接收到的信号, "ActnOfLedCornrgLampLe", "ActnOfLedDaytiRunngLamp"是想要接收的信号，num为最大接收的裸数据数, duration是最大接收时长
    result = receiver.receive_signals("ActnOfLedCornrgLampLe", "ActnOfLedDaytiRunngLamp", duration=5)
    
    # 打印接收到的信号，格式为[{信号一：值},{信号二：值}]
    print(result)
    
    # 断开硬件
    receiver.disconnect()
    

if __name__ == "__main__":
    # receive_can_signals_once()
    receive_can_signals()
