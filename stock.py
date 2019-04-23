# -*- coding: utf-8 -*-
"""
Created on Wed Mar 13 10:32:14 2019

@author: YIJU.TING
"""

import requests
from io import StringIO
import pandas as pd
import numpy as np
from datetime import datetime
from matplotlib import pyplot as plt

from talib import abstract
import twstock
#from finlab.plot_candles import plot_candles

from apscheduler.schedulers.blocking import BlockingScheduler
from plot_candles import *


def stock_warning(stockno,selec_month = False,year = 2019, month =1):
    token = "Z5Cg6UUou2ipMn2orBmEm4rZ6b7nbBBhbctzff9Ch2u"
    
    stock_data = twstock.Stock(str(stockno))
    if selec_month:
        data = stock_data.fetch_from(year, month)
    else:
        data = stock_data.fetch_31()
    data = pd.DataFrame(data)
    
    stock = data[['open','close','high','low','capacity']]
    
    #stock['open'] = data.open
    #stock['high'] = data.high
    #stock['low'] = data.low
    #stock['volume'] = data.transaction
    
    stock.columns = ['open', 'close', 'high', 'low', 'volume']
    stock['volume'] = stock['volume'].apply(lambda x:float(x)/1000)
    #stock['close'].plot()
    stock.index = data.date
    
    
    
    real_price = twstock.realtime.get(str(stockno))
    time_now = datetime.now()
    if not (time_now.hour >= 14) or (time_now.hour==13 & time_now.minute>30):
        real_time = real_price['info']['time']
        real_time = datetime.strptime(real_time, '%Y-%m-%d %H:%M:%S')
        real_time = pd.Timestamp(real_time.year,real_time.month,real_time.day)
        
        n = len(stock)
        
        if real_price['success']:
            price_now = pd.Series([float(real_price['realtime']['latest_trade_price'])]*n)
            price_now.index = data.date
            real_stock = pd.DataFrame({'open':[real_price['realtime']['open']],
                                  'close':[real_price['realtime']['latest_trade_price']],
                                  'high':[real_price['realtime']['high']],
                                  'low':[real_price['realtime']['low']],
                                  'volume':[real_price['realtime']['accumulate_trade_volume']]},
                index = [real_time])
            
            
            stock = stock.append(real_stock)
        
        else:
            price_now = pd.Series([np.nan] * n)
    
    
    
    
    
    
    SMA = abstract.SMA(stock)
    RSI = abstract.RSI(stock)
    STOCH = abstract.STOCH(stock) 
    BIAS = [np.nan]*9+stock_data.ma_bias_ratio(5, 10)
    BIAS = pd.Series(BIAS)
    BIAS.index = data.date
    
    #STOCH.plot()
    #stock['close'].plot(secondary_y=True)
    
    #RSI.plot()
    #stock['close'].plot(secondary_y=True)
    
    
    
    k = STOCH.slowk[-1]
    d = STOCH.slowd[-1]
    rsi = RSI[-1] 
    
    msg = '\n' + real_price['info']['time']+'\n'
    msg += real_price['info']['name']+'的股價: ' +'\n'
    msg += real_price['realtime']['latest_trade_price'] +'\n'
    
    KD1 = (max(k,d)<20) & (k>d)
    if KD1:
        msg +='KD低於20且K大於D' +'\n'
        
    KD2 = (min(k,d)>20) & (k<d)
    if KD2:
        msg +='KD低於20且K大於D' +'\n'
    
    RSI1 = rsi<20
    if RSI1:
        msg += 'RSI低於20' +'\n'
    
    RSI2 = rsi>80
    if RSI2:
        msg += 'RSI高於80' +'\n'
    
    
    
    msg += 'K = ' + str(round(k,0)) +'\n'
    msg += 'D = ' + str(round(d,0)) +'\n'
    msg += 'RSI = ' + str(round(rsi,0)) 
    #msg += '\n'
    #msg += str(real_price['realtime'])
    
    if KD1 or KD2 or RSI1 or RSI2:
        pic = plot_candles(
                         start_time='2019-01-01',      ## 開始時間
                         end_time='2019-03-13',       ## 結束時間
                         pricing=stock,                            ## dataframe 只吃 ['open_price', 'close_price', 'high', 'low', 'volume']
                         title=real_price['info']['code'],                      ## 名稱而已
                         volume_bars=True,               ## 畫不畫 量圖
                         overlays=[SMA,price_now],                    ##  跟股價圖 疊起來的是什麼指標
                         technicals = [RSI, STOCH,BIAS],    ## 其他圖要畫甚麼
                         technicals_titles=['RSI', 'KD','BIAS'] ## 其他圖的名稱
                       )
        image_path = 'plot_stock.jpg'
        plt.savefig(image_path)
        lineNotify(token, msg, image_path)
    print(msg)




stock_list = ['2484','3036','00632R']
stockno = stock_list[1]

stock_warning(stockno)

#scheduler = BlockingScheduler()

#scheduler.add_job(stock_warning,trigger = 'interval',minutes = 1,args=(stock_list[0],))
#scheduler.add_job(stock_warning(stock_list[1]),trigger = 'interval',minutes = 20)

#scheduler.start()


#selec_month = False
#year = 2019
#month = 1
#5日RSI、KD值和乖離率