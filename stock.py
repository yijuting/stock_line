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
import talib
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
        self.msg = ""
        self.token = "Z5Cg6UUou2ipMn2orBmEm4rZ6b7nbBBhbctzff9Ch2u"

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
    
    
    def stock_warning(self, scheduler = None):
        
        stockno = self.stockno
        self.scheduler = scheduler
        
        try:
            if str(stockno) in self.save_stock_data:
                
                stock = self.save_stock_data[str(stockno)]
                stock = self.append_real_stock(stockno, stock)
                
            else:
                stock_data = twstock.Stock(str(stockno))
                year = datetime.now().year
                month = datetime.now().month-2
                month = month if month>=1 else month+12
                data = stock_data.fetch_from(year, month)

                data = pd.DataFrame(data)
                
                stock = data[['open','close','high','low','capacity']]
                
                stock.columns = ['open', 'close', 'high', 'low', 'volume']
                stock['volume'] = stock['volume'].apply(lambda x:float(x)/1000)
                #stock['close'].plot()
                stock.index = data.date
                
                stock = self.append_real_stock(stockno, stock)
            
            self.save_stock_data.update({str(stockno):stock})
            
            min_price = min(stock.close[-10:len(stock)])
            max_price = max(stock.close[-10:len(stock)])
            
            SMA = talib.MA(np.array(stock.close), 30, matype=0)
            SMA = pd.Series(SMA)
            SMA.index = stock.index
            RSI = talib.RSI(np.array(stock.close),timeperiod = 5)            
            RSI = pd.Series(RSI)
            RSI.index = stock.index

            
            K,D = talib.STOCH(high = np.array(stock.high), 
                              low = np.array(stock.low), 
                              close = np.array(stock.close),
                              fastk_period=9,
                              slowk_period=3,
                              slowk_matype=0,
                              slowd_period=3,
                              slowd_matype=0)
            STOCH = pd.DataFrame(K, index = stock.index, columns = ['K'])
            STOCH['D'] = pd.Series(D, index = stock.index, name = 'D')
            J_df = pd.merge(STOCH.K.to_frame(), STOCH.D.to_frame(), 
                            left_index=True, right_index=True).apply(
                                    lambda x: (3*x.K) - (2*x.D), axis = 1)
            
            BIAS = [np.nan]*9+ma_bias_ratio(stock.close, 5, 10)
            BIAS = pd.Series(BIAS)
            BIAS.index = stock.index
            

            price_now = self.real_price['realtime']['latest_trade_price']
            
            k = STOCH.K[-1]
            d = STOCH.D[-1]
            rsi = RSI[-1] 
            bias = BIAS[-1]
            

            msg = self.real_price['info']['code']
            msg += self.real_price['info']['name']+'的股價: '
            msg += price_now +'\n'
            
            msg += '10日內最低收盤價: %s \n' % min_price
            msg += '10日內最高收盤價: %s \n' % max_price
            
            KD1 = (d<20) & (k>d)
            if KD1:
                msg +='up!!!   KD < 20 且 K > D' +'\n'
                
            KD2 = (d>80) & (k<d)
            if KD2:
                msg +='down!!! KD > 80 且 K < D' +'\n'
                
            min_rsi = min(RSI[-10:len(RSI)])
            max_rsi = max(RSI[-10:len(RSI)])
            RSI1 = rsi<20
            if RSI1:
                if (float(price_now)<=min_price)&(rsi>=min_rsi):
                    "high up!!! 股價新低 但 RSI不是新低"
                msg += 'up!!!   RSI < 20' +'\n'
            
            RSI2 = rsi>80
            if RSI2:
                if (float(price_now)>=min_price)&(rsi<=max_rsi):
                    "risk down!!! 股價新高 但 RSI不是新高"
                msg += 'down!!! RSI > 80' +'\n'
            
            BIAS1 = bias<-17
            if BIAS1:
                msg += 'up!!! BIAS < -17' +'\n'

            BIAS1 = bias > 17
            if BIAS1:
                msg += 'down!!! BIAS > 17' +'\n'            
            
            msg += 'K = ' + str(round(k,0)) +'\n'
            msg += 'D = ' + str(round(d,0)) +'\n'
            msg += 'RSI = ' + str(round(rsi,0))+'\n' 
            msg += '乖離率 = ' + str(round(bias,0))+'\n' 
            #msg += '\n'
            #msg += str(real_price['realtime'])
            
            start_time = str(stock.index[-20])
            end_time = str(stock.index[-1])
            #.strftime('%d-%m-%Y')
            
            n = len(stock)
            price_now = pd.Series(self.price_now*n)
            price_now.index =  stock.index
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
                msg = self.real_price['info']['time']+'\n' + msg
                image_path = 'plot_stock.jpg'
                plt.savefig(image_path)
                lineNotify(self.token, msg, image_path)
                
            else:
                self.msg += '\n'+msg
            
            print(msg)
            
        except:
            msg = 'something went wrong'
            
            if self.scheduler:
                lineNotify(self.token, msg, 'error.jpg')
                self.scheduler.shutdown(wait=False)
            else:
                print(msg)

    def sent_routing(self):
        msg = self.real_price['info']['time']+'\n' + self.msg
        lineNotify(self.token, msg)
        
    
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
        


#stock_list = ['2484','3036','0050','00677U']


#monitor.manual_monitor(stock_list[], sent_plot)
def start_monitor():
    monitor = stock_monitor()
    stock_list = ['2484','3036','3289','1441','00677U']
    sent_plot = False
    
    for stockno in stock_list:
        monitor.manual_monitor(stockno, sent_plot)
    monitor.sent_routing()
    
def start_monitor_no_alert():
    monitor = stock_monitor()
    stock_list = ['2484','3036','3289','1441','00677U']
    sent_plot = False
    
    for stockno in stock_list:
        monitor.manual_monitor(stockno, sent_plot)




scheduler = BlockingScheduler()

scheduler.add_job(start_monitor,
                  trigger = 'cron',
                  day_of_week='mon-fri', 
                  hour=8, minute=30, end_date='2020-05-20')

scheduler.add_job(start_monitor,
                  trigger = 'cron',
                  day_of_week='mon-fri', 
                  hour=9, minute=0, end_date='2020-05-20')

scheduler.add_job(start_monitor_no_alert,
                  trigger = 'cron',
                  day_of_week='mon-fri', 
                  hour=9, minute=30, end_date='2020-05-20')

scheduler.add_job(start_monitor_no_alert,
                  trigger = 'cron',
                  day_of_week='mon-fri', 
                  hour=10, minute=30, end_date='2020-05-20')

scheduler.add_job(start_monitor_no_alert,
                  trigger = 'cron',
                  day_of_week='mon-fri', 
                  hour=11, minute=30, end_date='2020-05-20')

scheduler.add_job(start_monitor_no_alert,
                  trigger = 'cron',
                  day_of_week='mon-fri', 
                  hour=12, minute=30, end_date='2020-05-20')

scheduler.add_job(start_monitor_no_alert,
                  trigger = 'cron',
                  day_of_week='mon-fri', 
                  hour=13, minute=30, end_date='2020-05-20')

scheduler.add_job(start_monitor,
                  trigger = 'cron',
                  day_of_week='mon-fri', 
                  hour=14, minute=30, end_date='2020-05-20')
        
scheduler.start()


