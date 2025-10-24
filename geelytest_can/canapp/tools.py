import os
import time
import toml
import logging
import threading 
import multiprocessing
from typing import List
from typing import Dict
from typing import Union
from can import Bus as CanBus
from can import BusABC
from geelytest_can.canapp import CanController
from geelytest_can.canapp import CanLogManager
from can import CanFDBitTiming
'''
概述: 主要用于管理多路PCAN设备的录制总线报文使用和提供CanController对象.
目的: 由于使用设备时想要监听所有总线,同时又想要模拟仿真发送或者接收数据,进行统一接口暴露使用
使用方式：
1)主进程启动多个线程去录制数据(一个pcan通道一个线程),建议不超过5个,线程通道容易奔溃
2)启动多个进程进行录制can总线(缺点多进程是无法共享CanController对象,导致无法调用通道进行数据的收发)
3)实例化两个CanTools对象,需要收发的通道一组，只需要录制报文的另外一组
优点: 
1)通过配置一个总线字典,通过暴露CanController对象,进行接收发送函数等等一些操作
注意事项: 如果总线配置字典没有DB文件, 对于CanController对象来说带有signals信号函数操作是不能使用,只能使用带有message函数,切记切记！！！
缺点:
1)总线形式比较复杂的,需要实例化多个CanTools对象组合进行使用.
2)录制报文,中间如果总线断开异常1s后自动连接,数据中间会丢失1s的节点
3)使用起来相对于复杂,需要看sample理解
'''

logger = logging.getLogger(__name__)


class CanTools():

    def __init__(self,cfgdict:dict) -> None: 
        """
        功能说明：初始化对象
        参数说明：
            :param can_manage_data: 传入配置字典
            {总线名称:
                {"name": 总线名称
                 "interface": 设备名称(支持pcan、tosun)
                 "channel": 设备通道
                 "db_path": db的文件路径,默认为None,如果没有DB,需要设置参数"is_fd"值
                 "is_fd": 默认为None,如果没有DB文件需要填写True/Flase,对应CanFD/Can
                }
            }
        异常说明：无
        返回值: None
        """    
        self.cfgdict = cfgdict
        self.__canlog_manager: Dict[str, CanLogManager] = {} 
        self.__new_cancontrolles: Dict[str, CanController] = {}
        self.__controller_connects: Dict[str, CanController] = {}  
        self.__controller_interfaces:Dict[str, Dict[int, CanController]] = {} 
        self.__recording_can_bus: Dict[str, BusABC] = {}  

        self.__process_list: List[multiprocessing.Process] = []
        self.__pcan_status_threading: threading.Thread = None
        self.process_count = multiprocessing.RawValue('i',0) 
        self.process_flag = multiprocessing.RawValue('i',0)
        self.thread_flag = None
        self.__recording_cfg = {"file_path":None,"flie_type":None,"max_data_M":None,"bus_dict":None}

    @property
    def controller_interface_mapping(self) ->  Dict[str, Dict[int, CanController]]: 
        return self.__controller_interfaces
    
    @property
    def controller_busname_mapping(self) ->  Dict[str, CanController]: 
        return self.__controller_connects
    
    def connect(self,new_cancontroller:Dict[str,CanController] = None) -> None:
        """
        功能说明：设备通道连接
        参数说明：
            :param new_cancontroller: Dict{总线名称:实例化CanController对象,...}, 默认为None,提取配置文件数据
        异常说明：无
        返回值：None
        """
        if not new_cancontroller:
            new_cancontroller = self.__new_cancontrolle()
     
        for bus_name in new_cancontroller:
            try:
                connect = new_cancontroller[bus_name].connect()
                add_channel = {}
                if connect:
                    self.process_count.value += 1
                    self.__recording_can_bus.update({bus_name:new_cancontroller[bus_name].bus})
                    self.__controller_connects.update({bus_name:new_cancontroller[bus_name]})
                    
                    add_channel = {self.cfgdict[bus_name]['channel']:new_cancontroller[bus_name]}
                    if self.cfgdict[bus_name]['interface'] in self.__controller_interfaces.keys():
                        self.__controller_interfaces[self.cfgdict[bus_name]['interface']].update(add_channel)
                    else:   
                        self.__controller_interfaces.update({self.cfgdict[bus_name]['interface']:add_channel})            
            except Exception as e:
                logger.error(f'连接异常：{e}')

    def recording_message(self,file_path:str = None,flie_type:str = 'blf',max_data_M:int = 100,bus_dict:Dict[str, BusABC]=None) -> None:
        """
        功能说明: 开始启动录制总线报文
        参数说明：
            :param file_path: 录制报文路径,默认:当前执行路径
            :param flie_type: 录制报文文件格式，目前支持(blf、asc、csv)
            :param max_data_M: 录制文件切片大小，单位: M
            :param max_data_M: 需要录制总线的bus, Dict[总线名称, BusABC(根据实例化CanController对象connetc连接后返回的bus属性)], 默认为None,获取的是配置文件所有的总线,进行录制
        异常说明：无
        返回值： 无
        """
        self.__recording_cfg = {"file_path":file_path,"flie_type":flie_type,"max_data_M":max_data_M,"bus_dict":bus_dict}
        if not flie_type in ['blf','asc','csv']: 
            raise ValueError(f'录制的文件目前只支持: blf、asc、csv文件')
        
        if not bus_dict:
            bus_dict = self.__recording_can_bus
        time_day =  time.strftime("%Y-%m-%d", time.localtime(time.time())) 
        time_s =  time.strftime("%Y-%m-%d_%H%M%S", time.localtime(time.time())) 
        
        try:
            for bus_name in bus_dict:             
                path = f"/can_bus_log/{time_day}/{bus_name}"         
                if file_path: 
                    path_log = file_path + path        
                else:
                    path_log = "." + path
                if not os.path.exists(path_log):  
                    os.makedirs(path_log) 
                if os.path.isfile(path_log): 
                    logger.error(f'输入录制的文件路径')
                manager_recording = CanLogManager(bus_dict[bus_name])
                manager_recording.start_logging(file = f"{path_log}/{time_s}.{flie_type}" ,max_bytes = max_data_M *1024*1024)
                self.__canlog_manager.update({bus_name:manager_recording})   
                logger.info(f'============总线: {bus_name},开始录制报文=============')
        except Exception as e:
                logger.error(f'录制失败: {e}')

    def create_process_recording_message(self,
                                         number:int = 4,
                                         file_path:str = None,
                                         flie_type:str = 'blf',
                                         max_data_M:int = 100
                                         ):
        """
        功能说明: 根据指定每个进程通道个数，创建多进程，录制总线报文; 多进程是不支持主进程去调用CanController对象,目前多进程无法同步dll对象.
        参数说明:
            :param number: 每个进程总线通道个数, 默认4个通道 ***如果每个进程通道数过多,容易导致总线异常断开,建议不超过6个.
        异常说明：无
        返回值: None
        """
        controller_data = self.__new_cancontrolle()
        process_data = self.__split_dict(controller_data,key_number = number)

        count = 0
        for data in process_data:
            count += 1      
            time.sleep(0.1)
            lock = multiprocessing.Lock()      
            process = multiprocessing.Process(target=self.__process_function_recording,args=(data,lock,file_path,flie_type,max_data_M))    
            process.start()
            self.__process_list.append(process)
            logger.info(f'进程开始第： {count}个,进程信息: {process}; :::进程中pcan通道总线数据 {data.keys()}')
        logger.info(f'总共启动进程个数:{len(self.__process_list)},进程详细信息::: {self.__process_list}')

    def close_process(self):
        """
        功能说明: 关闭进程,设置标志位self.process_flag = 1
        参数说明:
            :param : 无
        异常说明：无
        返回值: None
        """
        self.process_flag.value = 1

    def disconnect(self) -> None:
        """
        功能说明：断开设备连接
            1)如果开启了线程，退出线程.
            2)如果录制报文存在,停止报文录制.
            3)如果设备初始化,断开设备.
            3)如果开启了进程,关闭进程.
        参数说明：
            :param : 无
        异常说明：无
        返回值: None
        """
        if self.process_flag.value == 0: 
            self.process_flag.value = 1
        time.sleep(1)
        if self.__pcan_status_threading:
            self.thread_flag = 1
            self.__pcan_status_threading.join()

        if self.__canlog_manager:
            for bus_name in self.__canlog_manager:
                self.__canlog_manager[bus_name].stop_logging()           
            
        if self.__controller_connects:
            for bus_name in self.__controller_connects:
                time.sleep(0.1)
                self.__controller_connects[bus_name].disconnect()
                
        if self.__process_list:
            for process in self.__process_list:
                process.terminate()

    def loop_listen_pcan_status(self):
        """
        功能说明: 每隔1S,循环去读取总线的状态,当失败后重新连接录制报文,退出条件当self.process_flag.value = 1时退出
        参数说明:
            :param : 无
        异常说明：无
        返回值: None
        """
        while True:
            time.sleep(1)
            logger.debug(f'==========================实时检测pcan通道状态,开始分割线==========================') 
            log_time = time.strftime("%Y-%m-%d_%H:%M:%S", time.localtime(time.time())) 
    
            for bus_name in self.__controller_connects:            
                if not self.__controller_connects[bus_name].notifier: 
                        # logger.error(f'bus notifier :{self.__add_new_controller[bus_name].notifier}')
                        continue 
                    
                exceptions_data = self.__controller_connects[bus_name].notifier.exceptions
                logger.debug(f'::: bus_name:{bus_name}, channel:{self.cfgdict[bus_name]["channel"]}, interface:{self.cfgdict[bus_name]["interface"]}, bus_count = {len(self.__controller_connects)}个, error_code = {exceptions_data}.')

                if exceptions_data:
                    logger.error(f'监听总线：{bus_name} 设备：{self.cfgdict[bus_name]["interface"]} 通道: {self.cfgdict[bus_name]["channel"]},==> 连接异常.')
                    try:
                        with open('can_tools_eroor.log', 'a') as file:             
                            txt_error1 = f'::: {exceptions_data}.\n'
                            txt_comment = f'{log_time} 监听总线：{bus_name} 设备：{self.cfgdict[bus_name]["interface"]} 通道: {self.cfgdict[bus_name]["channel"]},==> 连接异常.\n'
                            file.write(txt_error1)
                            file.write(txt_comment)
                    except Exception as error: 
                        logger.error(f"write can_tools_eroor.log exception: {error}")
                        with open(f'can_tools_eroor_{log_time}.log', 'a') as file:             
                            txt_error1 = f'::: {exceptions_data}.\n'
                            txt_comment = f'{log_time} 监听总线：{bus_name} 设备：{self.cfgdict[bus_name]["interface"]} 通道: {self.cfgdict[bus_name]["channel"]},==> 连接异常.\n'
                            file.write(txt_error1)
                            file.write(txt_comment)
                    finally:     
                        pass  

                    try:
                        self.__canlog_manager[bus_name].stop_logging()
                        self.__new_cancontrolles[bus_name].disconnect()
                        self.connect({bus_name:self.__new_cancontrolles[bus_name]})
                        self.__recording_cfg.update({"bus_dict":{bus_name:self.__recording_can_bus[bus_name]}})
                        self.recording_message(**self.__recording_cfg)
                        logger.info(f'总线: {bus_name},通道:{self.cfgdict[bus_name]["channel"]},重新建立连接.')   
                    except Exception as error: 
                        logger.error(f'总线：{bus_name} 设备：{self.cfgdict[bus_name]["interface"]} 通道: {self.cfgdict[bus_name]["channel"]},重新建立连接失败 ==> {error}')
                    finally:     
                        pass 
                    
                else:
                    pass
            logger.debug(f'==========================实时检测pcan通道状态,结束分割线==========================\n')

            if self.process_flag.value != 0 or self.thread_flag:
                break

    def create_thread_listen_pcan_status(self) -> None:
        """
        功能说明: 创建一个线程去监听总线状态，失败后重新录制报文
        参数说明:
            :param : 无
        异常说明：无
        返回值: None
        """
        self.__pcan_status_threading = threading.Thread(target=self.loop_listen_pcan_status,args=())
        self.__pcan_status_threading.start()
        
    def __new_cancontrolle(self,cancontrolle_data:dict = None) ->  Dict[str, CanController]:
        """
        功能说明: 提取配置文件数据,实例化CanController对象, 由于初始化CanController中有DBC和无DBC,放在一起实例化CanController对象设备容易报错read too late,所以区分种类实例化对象
        参数说明:
            :param cancontrolle_data:
                {总线名称:
                    {"name": 总线名称
                    "interface": 设备名称(支持pcan、tosun)
                    "channel": 设备通道
                    "db_path": db的文件路径,默认为None,如果没有DB,需要设置参数"is_fd"值
                    "is_fd": 默认为None,如果没有DB文件需要填写True/Flase,对应CanFD/Can
                    }
                }    
        异常说明：无
        返回值: Dict[总线名称:实例化CanController对象]
        """
        if cancontrolle_data:
            manage_data = cancontrolle_data
        else:
            manage_data = self.cfgdict
        
        # 排序
        can_manage_data = {key: value for key, value in sorted(manage_data.items(), key=lambda x: x[1]['channel'])}

        new_canController = {}
        not_db_data = {}

        count = 0
        for bus_name in can_manage_data:
            if can_manage_data[bus_name]['db_path']:
                count += 1
                can_manage_data[bus_name].pop("is_fd")
                can = CanController(**can_manage_data[bus_name])
                new_canController.update({can_manage_data[bus_name]['name']:can})
                logger.info(f"创建第{count}个总线: {can_manage_data[bus_name]['name']} 设备：{self.cfgdict[bus_name]['interface']} 通道: {self.cfgdict[bus_name]['channel']} ==> CanController对象.")
            elif can_manage_data[bus_name]['is_fd'] == True or can_manage_data[bus_name]['is_fd'] == False:
                not_db_data.update({bus_name:can_manage_data[bus_name]})
            else:
                raise ValueError(f'db_path 和 is_fd参数必须有一个为有效值')

        if  not_db_data:
            bus_data = None
            for bus_name in not_db_data:
                if not_db_data[bus_name]['is_fd'] == True:
                    bus_data = CanBus(interface = not_db_data[bus_name]['interface'],
                        channel = not_db_data[bus_name]['channel'],
                        fd = not_db_data[bus_name]['is_fd'], 
                        timing = CanFDBitTiming.FD_500000_2000000
                    )
                elif not_db_data[bus_name]['is_fd'] == False:
                    bus_data = CanBus(interface = not_db_data[bus_name]['interface'],
                            channel = not_db_data[bus_name]['channel'],
                            fd = not_db_data[bus_name]['is_fd']
                            )
                else:
                    raise ValueError(F'is_fd 参数为True/False')
                not_db_data[bus_name].pop("is_fd")
                not_db_data[bus_name].update({'bus':bus_data})
                can = CanController(**not_db_data[bus_name])
                new_canController.update({not_db_data[bus_name]['name']:can})

                count += 1
                logger.info(f"创建第{count}个总线: {can_manage_data[bus_name]['name']} 设备：{self.cfgdict[bus_name]['interface']} 通道: {self.cfgdict[bus_name]['channel']} ==> CanController对象.")
        self.__new_cancontrolles = new_canController
        return new_canController

    def __process_function_recording(self,process_data:Dict[str,CanController],process_lock,file_path,flie_type,max_data_M) -> None:  
        """
        功能说明: 开启多个进程对象函数,录制报文启动流程
        参数说明:
            :param process_data: Dict{总线名称:CanController对象,...}
            :param lock: 进程锁
        异常说明：无
        返回值: None
        """
        try:
            process_lock.acquire()   
            self.connect(new_cancontroller = process_data) 
            self.recording_message(file_path,flie_type,max_data_M)
            time.sleep(1) 
            self.loop_listen_pcan_status() 
            process_lock.release()
        except Exception as error: 
            logger.error(f"Worker encountered an exception: {error}")
        finally:        
            self.disconnect()
   
    def __split_dict(self,data_dict:dict,key_number:int = 4) -> List[Dict[str,CanController]]:
        """
        功能说明: 根据设定每个字典的元素个数,进行字典切片,切分成多个字典
        参数说明:
            :param key_number: 需要切分的元素个数,默认4个元素为一个字典
        异常说明：无
        返回值: List[Dict{总线名称:实例化CanController对象,...}]
        """
        sorted_items = [item for item in data_dict.items()]   
        dict_parts = [dict(sorted_items[i:i+key_number]) for i in range(0, len(sorted_items), key_number)]
        return dict_parts 

    def __analysis_cancontrolle_toml(self,toml_path:str = '/root/chenlong/benchconfig.toml' )-> None:
        # 预留,需要根据toml文件定义去取值，需要新增，实际情况按照实例化对象需求去添加
        toml_CanController_data = {}    
        config = toml.load(toml_path)
        bench = config.get("pc",{}).get("bench",{})
        
        for i in bench:
            can_config = i.get('link').get('can')
            for j in can_config:
                channel_interface = {}
                channel_interface.update({'interface':can_config[j]['interface']})
                channel_interface.update({'channel':can_config[j]['channel']})
                toml_CanController_data.update({j:channel_interface})
            
        for i in toml_CanController_data:
            logger.info(f"toml文件总线bus名称 = {i} ,data = {toml_CanController_data[i]}")     


