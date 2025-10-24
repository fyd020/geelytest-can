from jidutest_can.canapp import CanController
from jidutest_can.canapp import CanLogManager
import logging


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


# 回放数据
def replay_can_data():
    
    # 实例化一个控制器去回放数据
    # "BodyCAN"：控制器名字
    # "pcan"： 控制器采用的硬件设备类型（如PEAK公司的pcan）
    # 1: 控制器使用的硬件设备通道号（1, 2, ... , 16）
    # "v0.6.5/SDB22R04_BGM_BodyCAN_220923_Release.dbc"：dbc文件路径
    player = CanController(
        "BodyCAN", 
        "pcan", 
        1,
        r"/test/resource/v1.0/v1.0/SDB23R01_BodyCAN_230316_Release.dbc"
    )
    
    # 实例化一个CAN日志管理器, 传入的参数为上面实例化的BUS对象
    manager = CanLogManager(player.bus)
    
    # 回放数据, "C:\demo.blf"为需要回放的文件名
    manager.replay_data(r"C:\demo.blf")
    

if __name__ == "__main__":
    replay_can_data()
    