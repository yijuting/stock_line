# -*- coding: utf-8 -*-
"""
Created on Wed May 22 18:13:18 2019

@author: diana
"""



#from io import StringIO
import pandas as pd
import numpy as np
import datetime
import time
import random

import peakutils

import math

import talib
import twstock
import copy

import pickle
import pymongo
#######mongo db#######
client = pymongo.MongoClient()
db = client['stock']
collect = db['stock_new']
#############


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

def get_data(stockno, month_before = 6):
    print('getting data',stockno)
    stock_data = twstock.Stock(str(stockno))
    time.sleep(random.randint(5,15))
    year = datetime.datetime.now().year
    month = datetime.datetime.now().month-month_before
    year = year if month>=1 else year-1
    month = month if month>=1 else month+12
    data = stock_data.fetch_from(year, month)
    
#    stock = pd.DataFrame()
#    
#    stock['open'] = stock_data.open
#    stock['close'] = stock_data.close
#    stock['high'] = stock_data.high
#    stock['low'] = stock_data.low
#    stock['capacity'] = stock_data.capacity
    stock = data[['open','close','high','low','capacity']]
    stock.columns = ['open', 'close', 'high', 'low', 'volume']
    stock['volume'] = stock['volume'].apply(lambda x:float(x)/1000)
    stock.index = stock_data.date
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
                      fastk_period=5,
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
            
            KD1 = ((k<20) or (d<20)) & (k>d)
            if KD1:
                prob+=1
                
            KD2 = ((k>80) or (d>80)) & (k<d)
            if KD2:
                prob-=1

            temp_peak = find_nearest(np.array(highpeak),ind)
            temp_min = min(stock.low[temp_peak:ind])
            min_rsi = RSI[temp_peak]
            if (float(price_now)==temp_min)&(rsi!=min_rsi):
                prob+=1            
            
            if rsi==min_rsi:
                prob-=1
                
            temp_peak = find_nearest(np.array(lowpeak),ind)
            temp_max = max(stock.high[temp_peak:ind])
            max_rsi = RSI[temp_peak]
            if (float(price_now)==temp_max)&(rsi!=max_rsi):
                prob-=1

            if rsi==max_rsi:
                prob+=1
                
            RSI1 = rsi<20
            if RSI1:
                prob+=1
            
            RSI2 = rsi>80
            if RSI2:
                prob-=1
            
#            BIAS1 = bias<-17
#            if BIAS1:
#                prob+=1
#
#            BIAS1 = bias > 17
#            if BIAS1:
#                prob-=1     
                
            buy+=[prob,]
                
        else:
            buy+=[0,]
    data['buy'] = pd.Series(buy, index = stock.index, name = 'buy')
                
        
    buy_cum = []
    buy_price = []
    sell_cum = []
    sell_price = []
    budget = 200000
    earn_now = []

    
    buy_cum2 = []
    buy_price2 = []
    sell_cum2 = []
    sell_price2 = []
    budget2 = 200000
    earn_now2 = []
  
    
    if max(list(set(buy)))>0:
        buy_count = 0
        cost_cum = 0
        buy_count2 = 0
        cost_cum2 = 0
        for ind,date in enumerate(stock.index):
            price = stock.open[ind]
            if ind>10:
                buy_stock = buy[ind-1]
                one = round(price*1000*(1+0.000855),0)
                if (buy_stock>=1)&(budget-one>0):
                    count = math.floor(budget/one)
                    cost = one*count
                    budget-=cost
                    cost_cum += cost
                    buy_count+=count
                    buy_cum += [date,]
                    buy_price += [price,]
                    print(-cost)
                    print(budget)
                    print(data.iloc[ind])
                    
                if (buy_stock>=2)&(budget2-one>0):
                    count2 = math.floor(budget2/one)
                    cost2 = one*count2
                    budget2-=cost2
                    cost_cum2 += cost2
                    buy_count2 += count2
                    buy_cum2 += [date,]
                    buy_price2 += [price,]
                    print(-cost2)
                    print(budget2)
                    print(data.iloc[ind])

                if (buy_count>0):
                    price = stock.close[ind]
                    one = round(price*1000*(1-0.003855),0)
                    earn = one*buy_count
                    earn_rate = round((earn-cost_cum)/cost_cum,2)
                    if (buy_stock<0):
                        budget += earn
                        buy_count-=buy_count  
                        cost_cum = 0
                        sell_cum += [date,]
                        sell_price += [price,]
                        earn_now += [earn_rate,]
                        print(earn_rate)
                        print(budget)
                        print(data.iloc[ind])
                    elif (earn_rate<=-0.03)&(buy_stock==0):
                        budget += earn
                        buy_count-=buy_count  
                        cost_cum = 0
                        sell_cum += [date,]
                        sell_price += [price,]
                        earn_now += [earn_rate,]
                        print(earn_rate)
                        print(budget)
                        print(data.iloc[ind])
                            
                    elif (earn_rate>=0.1)&(buy_stock==0):
                        budget += earn
                        buy_count-=buy_count  
                        cost_cum = 0
                        sell_cum += [date,]
                        sell_price += [price,]
                        earn_now += [earn_rate,]
                        print(earn_rate)
                        print(budget)
                        print(data.iloc[ind])

                if (buy_count2>0):
                    one = round(price*1000*(1-0.003855),0)
                    earn2 = one*buy_count2
                    earn_rate2 = round((earn2-cost_cum2)/cost_cum2,2)
                    price = stock.close[ind]
                    if (buy_stock<0):
                        budget2 += earn2
                        buy_count2-=buy_count2
                        cost_cum2 = 0
                        sell_cum2 += [date,]
                        sell_price2 += [price,]
                        earn_now2 += [earn_rate2,]
                        print(earn_rate2)
                        print(budget2)
                        print(data.iloc[ind])
                    elif (earn_rate2<=-0.03)&(buy_stock==0):
                        budget2 += earn2
                        buy_count2-=buy_count2
                        cost_cum2 = 0
                        sell_cum2 += [date,]
                        sell_price2 += [price,]
                        earn_now2 += [earn_rate2,]
                        print(earn_rate2)
                        print(budget2)
                        print(data.iloc[ind])
                    elif (earn_rate2>=0.1)&(buy_stock==0):
                        budget2 += earn2
                        buy_count2-=buy_count2
                        cost_cum2 = 0
                        sell_cum2 += [date,]
                        sell_price2 += [price,]
                        earn_now2 += [earn_rate2,]
                        print(earn_rate2)
                        print(budget2)
                        print(data.iloc[ind])
                
        if buy_count>0:
            price = stock.close[ind]
            one = round(price*1000*(1-0.003855),0)
            earn = one*buy_count
            if earn>cost_cum:
                budget += earn
                cost_cum = 0
                sell_cum += [date,]
                sell_price += [price,]
                earn_rate = round((earn-cost_cum)/cost_cum,2)
                earn_now += [earn_rate,]
                print(earn_rate)
                print(budget)
                print(stock.iloc[ind])
        if buy_count2>0:
            price = stock.close[ind]
            one = round(price*1000*(1-0.003855),0)
            earn2 = one*buy_count2
            if earn2>cost_cum2:
                budget2 += earn2
                cost_cum2 = 0
                sell_cum2 += [date,]
                sell_price2 += [price,]
                earn_rate2 = round((earn2-cost_cum2)/cost_cum2,2)
                earn_now2 += [earn_rate2,]
                print(earn_rate)
                print((earn-cost_cum)/cost_cum)
                print(budget)
                print(stock.iloc[ind])
    n=200000         
    result = {'stockno':stockno,
              'budget':budget,
              'earn':round((budget-n)/n,4),
              'buy':buy_cum,'buy_price':buy_price,
              'sell':sell_cum,'sell_price':sell_price,
              'earn_now':earn_now,
              'care':buy[-1],
              'budget2':budget2,
              'earn2':round((budget2-n)/n,4),
              'buy2':buy_cum2,'buy_price2':buy_price2,
              'sell2':sell_cum2,'sell_price2':sell_price2,
              'earn_now2':earn_now2,
              }
    result.update({'data':{}})
    data.index = pd.Series(data.index).dt.strftime('%Y-%m-%d')
    for ind in range(0,len(data)):
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

#
#
#history = {'calculate':[]}
#care = {}

##
#stockno = '3036'
#stock = get_data(stockno)                   
#result = get_index(stock)
#
#history['calculate'].append(stockno)
#with open('history.pickle', 'wb') as handle:
#    pickle.dump(history, handle, protocol=pickle.HIGHEST_PROTOCOL)
#


with open('stock_name.pickle', 'rb') as handle:
    stock_code_list = pickle.load(handle)
    
with open('history.pickle', 'rb') as handle:
    history = pickle.load(handle)
with open('care.pickle', 'rb') as handle:
    care = pickle.load(handle)
count=1

waiting_stock =[]

#collect2 = db['Collections']
#
#data = collect2.find({'earn':{"$gt": 3000}},{'stockno':1,'buy':1,'_id':0}).sort(
#        [("earn", pymongo.DESCENDING)])
#
#waiting_stock += ['0050','2484','3036','1312','1526']
#for item in data:
#    for col, element in item.items():
#            if col == 'stockno':
#                stockno = element
#            else:
#                frequency = len(element)
#    if frequency>1:
#        waiting_stock += [stockno,]
#        
for ind,(stockno,_) in enumerate(stock_code_list.items()):
    waiting_stock += [stockno,]
    
for ind,stockno in enumerate(waiting_stock):
#for ind,stockno in enumerate(stock_list):
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

    if ind >500 :     
        if stockno not in history['calculate']:
            print(ind,stockno)
            
    #        with open('history.pickle', 'wb') as handle:
    #            pickle.dump(history, handle, protocol=pickle.HIGHEST_PROTOCOL)
    #        with open('care.pickle', 'wb') as handle:
    #            pickle.dump(care, handle, protocol=pickle.HIGHEST_PROTOCOL)
            
            if datetime.date.today().weekday()<=4 :
                time_now = datetime.datetime.now()
                
                if (((time_now.hour==9)&(time_now.minute<20))or((time_now.hour==8) & (time_now.minute>40))):
                    print('sleeping now for %s min' % str(60*6+20))
                    time.sleep(60*60*6+60*20)        
    
    
            
            count+=1
            sleep_time = random.randint(10,20)
            time.sleep(sleep_time)
    
            if len(stockno)==4:
                
                try:
                    stock = get_data(stockno)
                except:
                    print('%s, time out!'% sleep_time)
                    try:
                        sleep_time += random.randint(60*30,60*40)
                        time.sleep(sleep_time)
                        stock = get_data(stockno)
                    except:
                        try:
                            print('%s, time out!'% sleep_time)
                            sleep_time += random.randint(60*60,60*80)
                            time.sleep(sleep_time)
                            stock = get_data(stockno)    
                        except:
                            print('%s, time out!'% sleep_time)
                            sleep_time += random.randint(60*120,60*140)
                            time.sleep(sleep_time)
                            stock = get_data(stockno)                           
                result = get_index(stock)
    #            print(result)
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
                sleep_time = random.randint(60*20,60*40)
                time.sleep(sleep_time)
            else:
                sleep_time = max(random.randint(60*count,60*3*count),30)
                time.sleep(sleep_time)
          
            end = time.time()
            print('Time: ',end - start)
