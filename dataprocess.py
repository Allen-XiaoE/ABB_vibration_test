import pandas as pd
import numpy as np
from scipy.signal import butter, filtfilt
from configparser import ConfigParser
import os

def initt():
    config = ConfigParser()
# 读取.ini文件
    config.read('settings.ini')
    path = config.get('settings','path')
    cut_length = config.get('settings','cut_length')
    freq = config.get('settings','freq')
    spec = config.get('settings','spec')
    url = config.get('settings','url')
    return{
        'path':path,
        'cut_window':int(cut_length),
        'freq':int(freq),
        'spec':float(spec),
        'url':url
    }

# 1.读取txt
def calculation(fname,path):
    params = initt()
    fs = 400
    path = os.path.join(path,'DATA',f'{fname}.txt')
    df = pd.read_csv(path, sep=",")
    df["Total"] = np.sqrt(
        df["FreeAcc_E"] ** 2 + df["FreeAcc_N"] ** 2 + df["FreeAcc_U"] ** 2
    )
    # 2.数据过滤
    freq = params["freq"]
    b, a = butter(5, 2 * freq / fs, btype="low")
    y = filtfilt(b, a, df["FreeAcc_U"])
    # 3.切割数据
    # rms_ptp_list = pd.DataFrame()
    id = np.where(df["Total"] >= 2)[0][0]-100
    PASS_OR_NOT = []
    cut_length = params["cut_window"]
    spec = params["spec"]
    rms = -1
    for i in range(6):
        _Y = y[id + cut_length + 1600 * i : id + 1000 + 1600 * i - cut_length*2]
        rms = np.sqrt(np.mean(_Y**2))
        if rms <= spec:
            PASS_OR_NOT.append(0)
        else:
            PASS_OR_NOT.append(1)
    return PASS_OR_NOT

if __name__ == '__main__':
    or_not = calculation('1100-502179')
    print(or_not)