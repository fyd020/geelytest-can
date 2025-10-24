import logging
from pathlib import Path
from geelytest_can import CanController


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
 

# 接受CAN裸数据（仅供参考）
def receive_can_messages_once():  
    
    # 实例化一个控制器去接收裸数据
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
    
    # 获取接收到的裸数据, 0xb8, 0xb4是想要接收的信号，num为最大接收的裸数据数, duration是最大接收时长
    result = receiver.receive_message_once(0x20A)
    
    # 打印接收到的裸数据列表
    print(result)
    
    # 断开硬件
    receiver.disconnect()
    
def receive_can_messages():  
    
    # 实例化一个控制器去接收裸数据
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
    
    # 获取接收到的裸数据, 0xb8, 0xb4是想要接收的信号，num为最大接收的裸数据数, duration是最大接收时长
    result = receiver.receive_messages(0x20A, 0x21A)
    
    # 打印接收到的裸数据列表
    print(result)
    
    # 断开硬件
    receiver.disconnect()
    
    
if __name__ == "__main__":
    receive_can_messages_once()
    # receive_can_messages()
        