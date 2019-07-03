# -*- coding: utf-8 -*-
"""
Created on Tue Jun 25 19:08:59 2019

@author: diana
"""
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



client = pymongo.MongoClient()
db = client['stock']
collect = db['stock_new']
collect2 = db['sell_0.05']
sell_earn = 0.05

data = collect.find({},{'stockno':1,'data':1,'_id':0}).sort(
        [("earn2", pymongo.DESCENDING)])
id_dict={}
stock_all=[]
for item in data:
    id_dict.update({item['stockno']:len(stock_all)})
    stock_all.append(item['data'])
    
    

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

def get_data(stockno):
    print('getting data',stockno)

    data = pd.DataFrame(stock_all[id_dict[stockno]]).T

    return data



def get_index(stockno):
    stock = get_data(stockno)
    buy = stock['buy']              
        
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
                    print(stock.iloc[ind])
                    
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
                    print(stock.iloc[ind])

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
                        print(stock.iloc[ind])
                    elif (earn_rate<=-0.03)&(buy_stock==0):
                        budget += earn
                        buy_count-=buy_count  
                        cost_cum = 0
                        sell_cum += [date,]
                        sell_price += [price,]
                        earn_now += [earn_rate,]
                        print(earn_rate)
                        print(budget)
                        print(stock.iloc[ind])
                            
                    elif (earn_rate>=sell_earn)&(buy_stock==0):
                        budget += earn
                        buy_count-=buy_count  
                        cost_cum = 0
                        sell_cum += [date,]
                        sell_price += [price,]
                        earn_now += [earn_rate,]
                        print(earn_rate)
                        print(budget)
                        print(stock.iloc[ind])

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
                        print(stock.iloc[ind])
                    elif (earn_rate2<=-0.03)&(buy_stock==0):
                        budget2 += earn2
                        buy_count2-=buy_count2
                        cost_cum2 = 0
                        sell_cum2 += [date,]
                        sell_price2 += [price,]
                        earn_now2 += [earn_rate2,]
                        print(earn_rate2)
                        print(budget2)
                        print(stock.iloc[ind])
                    elif (earn_rate2>=sell_earn)&(buy_stock==0):
                        budget2 += earn2
                        buy_count2-=buy_count2
                        cost_cum2 = 0
                        sell_cum2 += [date,]
                        sell_price2 += [price,]
                        earn_now2 += [earn_rate2,]
                        print(earn_rate2)
                        print(budget2)
                        print(stock.iloc[ind])
                
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
#    stock.index = pd.Series(stock.index).dt.strftime('%Y-%m-%d')
    for ind in range(0,len(stock)):
        temp = pd.DataFrame(stock.iloc[ind]).T.to_dict('index')
        result['data'].update(temp)
    collect2.insert_one(result)
    
    return result
            

stock_list = [stock for stock,_ in id_dict.items()]

for stockno in stock_list:
    result = get_index(stockno)

