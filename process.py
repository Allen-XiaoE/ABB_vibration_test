from rws import RWS
from dataprocess import calculation
from mti import receiver, parser
import sys, time
import warnings
from threading import Thread
from queue import Queue
 
warnings.filterwarnings("ignore")
q = Queue()
rws = RWS(url='192.168.125.1')
# 运行流程:
# 1.ping rws看是否能ping通,如果不能ping通需要报错
while rws.connect_verification()!='OK':
    # show_message_box()
    print('Connect controller NOK!')
    time.sleep(5)

print('Connect controller OK!')

if rws.baseurl == 'https://192.168.125.1':
    series = rws.GETserial()
else:
    series = '1100-000001'
print(f'Serial NO.:{series}')
# 2.获取当前controller的模式,如果为手动模式需要提示:请转自动，如果点了OK，会再次检测。知道为自动为止。
while rws.GETopmode() != 'AUTO':
    # show_message_box()
    print('Controller Mode is NO-AUTO! Please set to AUTO!')
    time.sleep(5)
print('Cotroller mode is AUTO!')
# 3.写入文档到data/vibration.modx,并且载入module
file = open(r'C:\Users\CNALFEN\Desktop\IRB1100_Vibration_Test_v0.1.2_new_CFG_0528.modx','r')
content = file.read()
if rws.uploadfile('DATA/vibration.modx',content=content) != 'OK':
    raise RuntimeError('upload file failed!')
print('Upload file OK!')
time.sleep(1)
if rws.loadmodule('DATA/vibration.modx') != 'OK':
    raise RuntimeError('Load module failed!')
print('Load module OK!')
# 5.检查motor状态，如果为motor-off,改为motor-on
if rws.GETmotormode() != 'motoron':
    if rws.motor('motoron') != 'OK':
        raise RuntimeError('Can not Motor-ON!')
print('Motor ON!')
# 6.启动mti,检查时候mti连接好了。如果没有连接好，需要提示没有找到mti
# 7.sensor hold-on 1分钟
# 8.mti开始采集数据
# 9.启动vibration test程序
time.sleep(1)
if rws.pptoRoutine('VibrationTest','IRB1100_Vibration_Test') != 'OK':
    raise RuntimeError('PP to Vibration Test Failed!')

else:
    
    # t = Thread(target=receiver,args=(series,q))
    # t.start()
    # time.sleep(120)
    print('PP to Vibration Test!')
    if rws.excuseRapid() != 'OK':
        raise RuntimeError('Rapid excuse Failed!')
    print('Vibration Test start!')
    while rws.GETrapidstatus() != 'stopped':
        time.sleep(0.2)
        print('Program is running!')
if rws.unloadmodule('IRB1100_Vibration_Test') != 'OK':
    raise RuntimeError('Unload module failed!')
print('Unload module OK!')
if rws.deletefile('DATA/vibration.modx') != 'OK':
    raise RuntimeError('Delete file failed!')
print('Delete file OK!')
# q.put(1)
# t.join()
# print('Collect Data Done!')
# parser(series)
# print('Parser Data Done!')
# time.sleep(5)
# outcome = calculation(series)
# outcome.insert(0,series)
# print(outcome)
# 10.结束后数据解析
# 11.数据分析
# 12.出结果