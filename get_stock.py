# -*- coding: utf-8 -*-
"""
Created on Wed May 22 18:13:18 2019

@author: diana
"""



#from io import StringIO
import pandas as pd
import numpy as np
from datetime import datetime
import time
import random

import peakutils


import talib
import twstock
import copy

import pickle
import pymongo

client = pymongo.MongoClient()
db = client['stock']
collect = db['Collections']

def find_nearest(array,value):
#    print(array,value)
    idx = (np.abs(array-value)).argmin()
    
    if array[idx]<value:
        result = array[idx]
    elif idx>=1:
        result = array[idx-1]
    else:
        result=0
    return result

def ma_bias_ratio(price, day1):
    """Calculate moving average bias ratio"""
    price = list(price)
    average = np.mean(price)
    price_now = price[-1]
    return (price_now-average)/average*100

def get_data(stockno, month_before = 12):
    print('getting data',stockno)
    stock_data = twstock.Stock(str(stockno))
    year = datetime.now().year
    month = datetime.now().month-month_before
    year = year if month>=1 else year-1
    month = month if month>=1 else month+12
    data = stock_data.fetch_from(year, month)
    
    data = pd.DataFrame(data)
    stock = data[['open','close','high','low','capacity']]
    stock.columns = ['open', 'close', 'high', 'low', 'volume']
    stock['volume'] = stock['volume'].apply(lambda x:float(x)/1000)
    stock.index = data.date
    time.sleep(random.randint(5,15))
    return stock



def get_index(stock):
    data = copy.deepcopy(stock)
    RSI = talib.RSI(np.array(stock.open),timeperiod = 5)            
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

    data['D'] = pd.Series(D, index = stock.index, name = 'D')
    data['K'] = pd.Series(K, index = stock.index, name = 'K')
    data['RSI'] = RSI
    
    
    peak = []
    price = pd.Series(stock.high)
    highpeak = list(peakutils.indexes(price, thres=0.5, min_dist=30))
    if len(highpeak)==0:
        highpeak = [np.array(price).argmax(),]
    peak += highpeak
    price = pd.Series(stock.low)
    lowpeak = list(peakutils.indexes(-price, thres=0.5, min_dist=30))
    if len(lowpeak)==0:
        lowpeak = [np.array(price).argmin(),]
    peak += lowpeak
    peak.sort()
#    print(highpeak,lowpeak)
    price = pd.Series(stock.close)
    
    buy = []
    for ind,date in enumerate(stock.index):
        near_peak = find_nearest(np.array(peak),ind)
        bias = ma_bias_ratio(stock.close, ind-near_peak)
        if ind>=10:
            price_now = stock.open[ind]
            
            
            k = K[ind]
            d = D[ind]
            rsi = RSI[ind]
              
            prob = 0
            
            KD1 = (k<20) & (d<20) & (k>d)
            if KD1:
                prob+=1
                
            KD2 = (k>80) &(d>80) & (k<d)
            if KD2:
                prob-=1

            temp_peak = find_nearest(np.array(highpeak),ind)
            temp_min = min(stock.low[temp_peak:ind])
            min_rsi = RSI[temp_peak]
            if (float(price_now)<=temp_min)&(rsi>=min_rsi):
                prob+=1            
               
            temp_peak = find_nearest(np.array(lowpeak),ind)
            temp_max = max(stock.high[temp_peak:ind])
            max_rsi = RSI[temp_peak]
            if (float(price_now)>=temp_max)&(rsi<=max_rsi):
                prob-=1
            RSI1 = rsi<20
            if RSI1:
                prob+=1
            
            RSI2 = rsi>80
            if RSI2:
                prob-=1
            
            BIAS1 = bias<-17
            if BIAS1:
                prob+=1

            BIAS1 = bias > 17
            if BIAS1:
                prob-=1     
                
            if prob<0:
                buy+=[-1,]
            if prob>=2:
                buy+=[2,]
            if (prob<2) & (prob>=0):
                buy+=[0,]
                
        else:
            buy+=[0,]
    data['buy'] = pd.Series(buy, index = stock.index, name = 'buy')
                
        
    buy_cum = []
    buy_price = []
    sell_cum = []
    sell_price = []
    budget = 100000
    money = 0    
    
    if (1 in list(set(buy))) or (2 in list(set(buy))) :
        buy_count = 0
        cost_cum = 0
        for ind,date in enumerate(stock.index):
            
            price = stock.open[ind]
            if ind>10:
                buy_stock = buy[ind]
                if (buy_stock>1)&(budget/2/(price*1000)>0):
                    count = int(budget/2/(price*1000))
                    if buy_stock>2:
                        count = int(budget/2/(price*1000))
                    cost = price*1000*(1+0.000855)*count
                    budget-=cost
                    money -= cost
                    cost_cum += cost
                    buy_count+=count
                    buy_cum += [date,]
                    buy_price += [price,]

                if (buy_count>0):
                    if (buy_stock<0):
                        earn = price*1000*(1-0.003855)*buy_count
                        budget+=earn
                        money += earn
                        buy_count-=buy_count  
                        cost_cum = 0
                        sell_cum += [date,]
                        sell_price += [price,]
                    else:
                        earn = price*1000*(1-0.003855)*buy_count
                        if (earn-cost_cum)/cost_cum>0.05:
                            budget += earn
                            money += earn
                            buy_count-=buy_count  
                            cost_cum = 0
                            sell_cum += [date,]
                            sell_price += [price,]
        if buy_count>0:
            earn = price*1000*(1-0.003855)*buy_count
            if earn+money>0:
                budget += earn
                money += earn
                cost_cum = 0
                sell_cum += [date,]
                sell_price += [price,]
                
    result = {'stockno':stockno,
              'budget':budget,
              'earn':money,
              'buy':buy_cum,'buy_price':buy_price,
              'sell':sell_cum,'sell_price':sell_price,
              'care':buy[-1],
              'index':(RSI[-1],K[-1],D[-1],bias)}
    result.update({'data':{}})
    data.index = pd.Series(data.index).dt.strftime('%Y-%m-%d')
    for ind in range(-10,-1):
        temp = pd.DataFrame(data.iloc[ind]).T.to_dict('index')
        result['data'].update(temp)
    collect.insert_one(result)
    
    return result


#for stockno,temp in history.items():
#    if stockno=='calculate':
#        continue
#    result={'stockno':stockno}
#    result.update(temp)
#    collect.insert_one(result)

with open('stock_name.pickle', 'rb') as handle:
    stock_code_list = pickle.load(handle)
    
with open('history.pickle', 'rb') as handle:
    history = pickle.load(handle)
with open('care.pickle', 'rb') as handle:
    care = pickle.load(handle)
#
#history = {'calculate':[]}
#care = {}
#

count=1
for ind,(stockno,_) in enumerate(stock_code_list.items()):
    start = time.time()
#    if ind in [66,67]:
#        print(ind,stockno)
#        stock = get_data(stockno)
#        result = get_index(stock)
#        print(result)
#        if result[stockno]['earn']!=0:
#            history.update(result)
#            with open('history.pickle', 'wb') as handle:
#                pickle.dump(history, handle, protocol=pickle.HIGHEST_PROTOCOL)
#
#        if result[stockno]['care']>0:
#            care.update(result)
#            with open('care.pickle', 'wb') as handle:
#                pickle.dump(care, handle, protocol=pickle.HIGHEST_PROTOCOL)
#                
    if stockno not in history['calculate']:
        print(ind,stockno)
        
#        with open('history.pickle', 'wb') as handle:
#            pickle.dump(history, handle, protocol=pickle.HIGHEST_PROTOCOL)
#        with open('care.pickle', 'wb') as handle:
#            pickle.dump(care, handle, protocol=pickle.HIGHEST_PROTOCOL)
        
        time_now = datetime.now()
        if (((time_now.hour==9)&(time_now.minute<5))or((time_now.hour==8) & (time_now.minute>57))):
            time.sleep(600)
        for H in range(9,15):
            if (time_now.hour==H & ((time_now.minute<35)or(time_now.minute>27))):
                time.sleep(600)
        if (((time_now.hour==12)&(time_now.minute<5))or((time_now.hour==11) & (time_now.minute>57))):
            time.sleep(600)
        if (time_now.hour==13 &  ((time_now.minute<25)or(time_now.minute>17))):
            time.sleep(600)
        
        count+=1
        time.sleep(random.randint(0,20))

        if len(stockno)==4:
            try:
                stock = get_data(stockno)
            except:
                print('time out!')
                try:
                    time.sleep(random.randint(60*30,60*50))
                    stock = get_data(stockno)
                except:
                    print('time out!')
                    time.sleep(random.randint(60*80,60*100))
                    stock = get_data(stockno)                   
            result = get_index(stock)
            print(result)
#            if result[stockno]['earn']!=0:
#                history.update(result)
            if result['care']>0:
                care.update(result)
                with open('care.pickle', 'wb') as handle:
                    pickle.dump(care, handle, protocol=pickle.HIGHEST_PROTOCOL)
        history['calculate'].append(stockno)
        with open('history.pickle', 'wb') as handle:
            pickle.dump(history, handle, protocol=pickle.HIGHEST_PROTOCOL)
        if count %3 ==0:
            time.sleep(random.randint(60*20,60*40))
        else:
            time.sleep(random.randint(60*3*count,60*5*count))
            
        end = time.time()
        print('Time: ',end - start)