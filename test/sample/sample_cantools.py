import time
import logging
from jidutest_can import CanTools


logger = logging.getLogger(__name__)

logging.basicConfig(
    format = "%(asctime)s - %(name)s - %(levelname)s - ProcessID : %(process)d - %(threadName)s:%(thread)d >>> %(message)s",
    level=logging.INFO
    )

# venus台架总线配置
venus_bench__cfigdict = {
    "INFO":
        {"name": "INFO",
         "interface": "pcan",
         "channel": 1,
         "db_path": "/root/chenlong/jidutest-vmm/test/dbc/SDB23R01_InfoCANFD_230309_Release.dbc",
         "is_fd": None
         },
    "Connectivity":
        {"name": "Connectivity",
         "interface": "pcan",
         "channel": 2,
         "db_path": "/root/chenlong/jidutest-vmm/test/dbc/SDB23R01_ConnectivityCANFD_230116_Release.dbc",
         "is_fd": None
         },
    "AD":
        {"name": "AD",
         "interface": "pcan",
         "channel": 3,
         "db_path": "/root/chenlong/jidutest-vmm/test/dbc/SDB23R01_ADCANFD_230309_Release.dbc",
         "is_fd": None
         },
    "Body":
        {"name": "Body",
         "interface": "pcan",
         "channel": 4,
         "db_path": "/root/chenlong/jidutest-vmm/test/dbc/SDB23R01_BodyCAN_230316_Release.dbc",
         "is_fd": None
         },
    # "Propulsion":
    #     {"name": "Propulsion",
    #      "interface": "pcan",
    #      "channel": 5,
    #      "db_path": "/root/chenlong/jidutest-vmm/test/dbc/SDB23R01_PropulsionCAN_230116_Release.dbc",
    #      "is_fd": None
    #      },
    "Chassis1":
        {"name": "Chassis1",
        "interface": "pcan",
        "channel": 6,
        "db_path": "/root/chenlong/jidutest-vmm/test/dbc/SDB23R01_ChassisCAN1_230203_Release.dbc",
        "is_fd": None
        },

    "Chassis2":
        {"name": "Chassis2",
        "interface": "pcan",
        "channel": 7,
        "db_path": "/root/chenlong/jidutest-vmm/test/dbc/SDB23R01_ChassisCAN2_230116_Release.dbc",
        "is_fd": None
        },

    "PassiveSafety":
        {"name": "PassiveSafety",
        "interface": "pcan",
        "channel": 8,
        "db_path": "/root/chenlong/jidutest-vmm/test/dbc/SDB23R01_PassiveSafetyCAN_230116_Release.dbc",
        "is_fd": None
        },

    "BodyExposed":
        {"name": "BodyExposed",
        "interface": "pcan",
        "channel": 9,
        "db_path": "/root/chenlong/jidutest-vmm/test/dbc/SDB23R01_BodyExposedCANFD_230116_Release.dbc",
        "is_fd": None
        },

    # #没有收到报文
    # "BodyALM1":
    #     {"name": "BodyALM1",
    #     "interface": "pcan",
    #     "channel": 10,
    #     "db_path": "/root/chenlong/jidutest-vmm/test/dbc/SDB23R01_BodyALMCANFD1_230116_Release.dbc",
    #     "is_fd": None
    #     },

    
    # #没有收到报文
    # "BodyALM2":
    #     {"name": "BodyALM2",
    #     "interface": "pcan",
    #     "channel": 11,
    #     "db_path": "/root/chenlong/jidutest-vmm/test/dbc/SDB23R01_BodyALMCANFD2_230116_Release.dbc",
    #     "is_fd": None
    #     },

    "INFOPrivate":
        {"name": "INFOPrivate",
        "interface": "pcan",
        "channel": 12,
        "db_path": None,
        "is_fd": True
        },

    "FLR":
        {"name": "FLR",
        "interface": "pcan",
        "channel": 13,
        "db_path": "/root/chenlong/jidutest-vmm/test/dbc/SDB23R01_FLRCANFD_230116_Release.dbc",
        "is_fd": None
        },

    "BNCMPrivate":
        {"name": "BNCMPrivate",
        "interface": "pcan",
        "channel": 14,
        "db_path": None,
        "is_fd": True
        },

    "ADPrivate1":
        {"name": "ADPrivate1",
        "interface": "pcan",
        "channel": 15,
        "db_path": "/root/chenlong/jidutest-vmm/test/dbc/SDB23R01_ADPrivateCANFD1_230116_Release.dbc",
        "is_fd": None
        },

    "ADPrivate2":
        {"name": "ADPrivate2",
        "interface": "pcan",
        "channel": 16,
        "db_path": "/root/chenlong/jidutest-vmm/test/dbc/SDB23R01_ADPrivateCANFD2_230116_Release.dbc",
        "is_fd": None
        },

    # "Diagnostic":
    #     {"name": "Diagnostic",
    #     "interface": "pcan",
    #     "channel": 17,
    #     "db_path": None,
    #     "is_fd": None
    #     },

    # "ADRedundancy":
    #     {"name": "ADRedundancy",
    #     "interface": "pcan",
    #     "channel": 18,
    #     "db_path": "/root/chenlong/jidutest-vmm/test/dbc/SDB23R01_ADRedundancyCAN_230116_Release.dbc",
    #     "is_fd": None
    #     },
    }

# venus台架propulsion总线配置
propulsion_cfigdict = {
    "Propulsion":
        {"name": "Propulsion",
         "interface": "pcan",
         "channel": 5,
         "db_path": "/root/chenlong/jidutest-vmm/test/dbc/SDB23R01_PropulsionCAN_230116_Release.dbc",
         "is_fd": None
         },
    }

# 多线程启动录制报文，可以进行通道的收发
def case_thread(): 
    test1 = {
        "INFO":
            {"name": "INFO",
            "interface": "pcan",
            "channel": 1,
            "db_path": None, #"/root/chenlong/jidutest-vmm/test/dbc/SDB23R01_InfoCANFD_230309_Release.dbc", 
            "is_fd": True #None
            },
        "Connectivity":
            {"name": "Connectivity",
            "interface": "pcan",
            "channel": 2,
            "db_path": "/root/chenlong/jidutest-vmm/test/dbc/SDB23R01_ConnectivityCANFD_230116_Release.dbc",
            "is_fd": None
            },
            }
    can = CanTools(test1)
    can.connect()
    can.recording_message(flie_type='asc')
    can.create_thread_listen_pcan_status()
    logger.info(f'返回通道对象:{can.controller_interface_mapping}')
    time_sleep = 3
    while True:
        time.sleep(1) 
        logger.info(f"==========================测试开始计时:{time_sleep}s=========================")
        # 无DBC收发数据
        can.controller_interface_mapping['pcan'][1].receive_messages(duration=0.1)
        message_data = {0x53f:'3f:40:ff:ff:ff:ff:ff:ff'}
        can.controller_interface_mapping['pcan'][1].send_messages(message_data,is_fd=True,cycle_time=100)
        can.controller_interface_mapping['pcan'][1].stop_sending()

        # 有DBC收发数据
        # signals = "DoorDrvrSts"
        # recv_signal =can.controller_interface_mapping['pcan'][2].receive_signals(signals,duration=0.1)
        # logger.info(f'recv_signal = {recv_signal}')
        # signals = {"DoorDrvrSts":2}
        # can.controller_interface_mapping['pcan'][2].send_signals(signals)

        if time_sleep == 0:    
            can.disconnect()
            break
        time_sleep -= 1

# 多进程启动录制报文，只做录制报文需求
def case_process():
    test1 = {
        "INFO":
            {"name": "INFO",
            "interface": "pcan",
            "channel": 1,
            "db_path": "/root/chenlong/jidutest-vmm/test/dbc/SDB23R01_InfoCANFD_230309_Release.dbc",
            "is_fd": None
            },
        "Connectivity":
            {"name": "Connectivity",
            "interface": "pcan",
            "channel": 2,
            "db_path": "/root/chenlong/jidutest-vmm/test/dbc/SDB23R01_ConnectivityCANFD_230116_Release.dbc",
            "is_fd": None
            },
            }
    can_recording = CanTools(test1)
    can_recording.create_process_recording_message(number=4)

    time_sleep = 10
    while True:
        time.sleep(1) 
        logger.info(f"==========================测试开始计时:{time_sleep}s=========================")
        if time_sleep == 0:
            can_recording.close_process()
            break
        time_sleep -= 1

# 多线程(有收发需求总线放置一起)、多进程录制组合使用
def case_thread_by_process():
    # 创建多进程录制报文CanTools对象，进行录制报文
    can_recording = CanTools(venus_bench__cfigdict)
    can_recording.create_process_recording_message(number=4)

    # 创建多线程录制报文，并且将返回CanController对象进行调用收发
    can_send = CanTools(propulsion_cfigdict)
    can_send.connect()
    can_send.recording_message()
    can_send.create_thread_listen_pcan_status()
    logger.info(f'返回通道对象:{can_send.controller_interface_mapping}')
    time_sleep = 1
    while True:
        time.sleep(1) 
        logger.info(f"==========================测试开始计时:{time_sleep}s=========================")
        if time_sleep == 0:
            can = can_send.controller_interface_mapping['pcan']
            for i in can:
                recv = can[i].receive_messages(duration=1)
                if recv:
                    logger.info(f'收取总线通道: {i},已经收取到的消息.')
                else:
                    logger.error(f'收取总线通道: {i},收取为空:{recv}')

            # 关闭录制以及通道（第1个CanTools对象）
            can_send.disconnect()
            # 关闭录制以及通道以及进程（第2个CanTools对象）
            can_recording.close_process()
            break
        time_sleep -= 1


if __name__ == "__main__":
    case_thread()
    # case_process()
    # case_thread_by_process()





