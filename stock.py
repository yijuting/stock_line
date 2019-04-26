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
import time
from matplotlib import pyplot as plt

from talib import abstract
import twstock

from apscheduler.schedulers.blocking import BlockingScheduler
from plot_candles import *



def moving_average(data, days):
    result = []
    data = data[:]
    for _ in range(len(data) - days + 1):
        result.append(round(sum(data[-days:]) / days, 2))
        data.pop()
    return result[::-1]

def ma_bias_ratio(price, day1, day2):
    """Calculate moving average bias ratio"""
    price = list(price)
    data1 = moving_average(price, day1)
    data2 = moving_average(price, day2)
    result = [data1[-i] - data2[-i] for i in range(1, min(len(data1), len(data2)) + 1)]
    return result[::-1]

class stock_monitor(object):
    def __init__(self):    
        self. save_stock_data = {}

    def get_real_stock(self,stockno):
        real_price = twstock.realtime.get(str(stockno))
        time_now = datetime.now()
        real_time = pd.Timestamp(time_now.year,time_now.month,time_now.day)  
        
        self.real_price = real_price
        
        if real_price['success']:
            real_stock = pd.DataFrame({
                    'open':[float(real_price['realtime']['open'])],
                    'close':[float(real_price['realtime']['latest_trade_price'])],
                    'high':[float(real_price['realtime']['high'])],
                    'low':[float(real_price['realtime']['low'])],
                    'volume':[float(real_price['realtime']['accumulate_trade_volume'])]
                    },index = [real_time])
            self.price_now = [float(real_price['realtime']['latest_trade_price'])]
            return real_stock
        else:
            self.price_now = [np.nan]
            print('can catch the latest price of %s' % str(stockno)) 


    def append_real_stock(self, stockno, stock):
        time_now = datetime.now()
        real_time = pd.Timestamp(time_now.year,time_now.month,time_now.day)   

        latest_stock_save = stock.iloc[-1].name    
        
        real_stock = self.get_real_stock(stockno)
        
        if latest_stock_save != real_time:
            stock = stock.append(real_stock)            
            
        else:
            if not (time_now.hour >= 14) or (time_now.hour==13 & time_now.minute>30):
                stock.update(real_stock) 
            else:
                print("don't need refresh")
        return(stock)
    
    
    def stock_warning(self,
                      select_month = False,
                      year = 2019, 
                      month =3):
        token = "Z5Cg6UUou2ipMn2orBmEm4rZ6b7nbBBhbctzff9Ch2u"
        stockno = self.stockno
        
        try:
            if str(stockno) in self.save_stock_data:
                
                stock = self.save_stock_data[str(stockno)]
                stock = self.append_real_stock(stockno, stock)
                
            else:
                stock_data = twstock.Stock(str(stockno))
                if select_month:
                    data = stock_data.fetch_from(year, month)
                else:
                    data = stock_data.fetch_31()
                data = pd.DataFrame(data)
                
                stock = data[['open','close','high','low','capacity']]
                
                stock.columns = ['open', 'close', 'high', 'low', 'volume']
                stock['volume'] = stock['volume'].apply(lambda x:float(x)/1000)
                #stock['close'].plot()
                stock.index = data.date
                
                stock = self.append_real_stock(stockno, stock)
            
            self.save_stock_data.update({str(stockno):stock})
            
            SMA = abstract.SMA(stock)
            RSI = abstract.RSI(stock)
            STOCH = abstract.STOCH(stock) 
            BIAS = [np.nan]*9+ma_bias_ratio(stock.close, 5, 10)
            BIAS = pd.Series(BIAS)
            BIAS.index = stock.index
            
            #STOCH.plot()
            #stock['close'].plot(secondary_y=True)
            
            #RSI.plot()
            #stock['close'].plot(secondary_y=True)
            
            
            
            k = STOCH.slowk[-1]
            d = STOCH.slowd[-1]
            rsi = RSI[-1] 
            
            msg = '\n' + self.real_price['info']['time']+'\n'
            msg += self.real_price['info']['name']+'的股價: '
            msg += self.real_price['realtime']['latest_trade_price'] +'\n'
            
            KD1 = (max(k,d)<20) & (k>d)
            if KD1:
                msg +='!!! KD < 20 且 K > D' +'\n'
                
            KD2 = (min(k,d)>20) & (k<d)
            if KD2:
                msg +='!!! KD > 20 且 K < D' +'\n'
            
            RSI1 = rsi<20
            if RSI1:
                msg += '!!! RSI < 20' +'\n'
            
            RSI2 = rsi>80
            if RSI2:
                msg += '!!! RSI > 80' +'\n'
            
            
            
            msg += 'K = ' + str(round(k,0)) +'\n'
            msg += 'D = ' + str(round(d,0)) +'\n'
            msg += 'RSI = ' + str(round(rsi,0)) 
            #msg += '\n'
            #msg += str(real_price['realtime'])
            
            start_time = str(stock.index[0])
            end_time = str(stock.index[-1])
            #.strftime('%d-%m-%Y')
            
            n = len(stock)
            price_now = pd.Series(self.price_now*n)
            price_now.index = stock.index
            pic = plot_candles(
                    start_time=start_time,## 開始時間
                    end_time=end_time,## 結束時間
                    pricing=stock,
                    ## dataframe 只吃 ['open_price', 'close_price', 'high', 'low', 'volume']
                    title = stockno,                      ## 名稱而已
                    volume_bars=True,               ## 畫不畫 量圖
                    overlays=[SMA,price_now],                    ##  跟股價圖 疊起來的是什麼指標
                    technicals = [RSI, STOCH, BIAS],    ## 其他圖要畫甚麼
                    technicals_titles=['RSI', 'KD','BIAS'] ## 其他圖的名稱
                    )        
            if KD1 or KD2 or RSI1 or RSI2 or self.sent_plot:
                image_path = 'plot_stock.jpg'
                plt.savefig(image_path)
                lineNotify(token, msg, image_path)
                
            
            print(msg)
            
        except:
            msg = 'something went wrong'
            lineNotify(token, msg, 'error.jpg')
            if self.scheduler:
                self.scheduler.shutdown(wait=False)
            else:
                print(msg)

    def manual_monitor(self, stockno,sent_plot = False):
        self.stockno = stockno
        self.scheduler = None
        self.sent_plot = sent_plot
        self.stock_warning()
        
    def schedule_monitor(self, stockno, minute_interval = 10,sent_plot = False):
        start_date = time.strftime('%Y-%m-%d 09:00:00', time.localtime(time.time()))
        end_date = time.strftime('%Y-%m-%d 13:00:00', time.localtime(time.time()))
        self.stockno = stockno
        self.sent_plot = sent_plot
        
        self.scheduler = BlockingScheduler()
        self.scheduler.add_job(self.stock_warning,
                              trigger = 'interval',
                              minutes = minute_interval,
                              args=(),
                              start_date = start_date,
                              end_date = end_date)
        
        self.scheduler.start()
        


stock_list = ['2484','3036','0050','00677U']
sent_plot = False
monitor = stock_monitor()
#monitor.manual_monitor(stock_list[], sent_plot)

for stockno in stock_list:
    monitor.manual_monitor(stockno, sent_plot)
    
#monitor.schedule_monitor(stock_list[0], 20)


#save_stock_data = {}
#for stockno in stock_list:
##stockno = stock_list[2]
#    save_stock_data = stock_warning(save_stock_data, stockno)
#
#
####  schedule modeling
#start_date = time.strftime('%Y-%m-%d 09:00:00', time.localtime(time.time()))
#end_date = time.strftime('%Y-%m-%d 13:00:00', time.localtime(time.time()))
#
#scheduler = BlockingScheduler()
#scheduler.add_job(stock_warning,
#                  trigger = 'interval',
#                  minutes = 1,
#                  args=(save_stock_data,stock_list[0],scheduler),
#                  start_date = start_date,
#                  end_date = end_date)
#
#scheduler.start()
#
#
##selec_month = False
##year = 2019
##month = 1
#5日RSI、KD值和乖離率