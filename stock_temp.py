# -*- coding: utf-8 -*-
"""
Created on Thu Mar 14 10:34:20 2019

@author: YIJU.TING
"""

def crawl_price(date,stockNo=None):
    r = requests.post('http://www.twse.com.tw/exchangeReport/MI_INDEX?response=csv&date=' + str(date).split(' ')[0].replace('-','') + '&type=ALL')
    ret = pd.read_csv(StringIO("\n".join([i.translate({ord(c): None for c in ' '}) 
                                        for i in r.text.split('\n') 
                                        if len(i.split('",')) == 17 and i[0] != '='])), header=0)
    ret = ret.set_index('證券代號')
    ret['成交金額'] = ret['成交金額'].str.replace(',','')
    ret['成交股數'] = ret['成交股數'].str.replace(',','')
    return ret

def catch_stock_price(n_days = None):
    data = {}
    date = datetime.datetime.now()
    fail_count = 0
    allow_continuous_fail_count = 5
    while len(data) < n_days:
    
        print('parsing', date)
        # 使用 crawPrice 爬資料
        try:
            # 抓資料
            data[date] = crawl_price(date)
            print('success!')
            fail_count = 0
        except:
            # 假日爬不到
            print('fail! check the date is holiday')
            fail_count += 1
            if fail_count == allow_continuous_fail_count:
                raise
                break
        
        # 減一天
        date -= datetime.timedelta(days=1)
        time.sleep(10)
    return data

data = catch_stock_price(n_days = None)  
  
close = pd.DataFrame({k:d['收盤價'] for k,d in data.items()}).transpose()
close.index = pd.to_datetime(close.index)

open = pd.DataFrame({k:d['開盤價'] for k,d in data.items()}).transpose()
open.index = pd.to_datetime(open.index)

high = pd.DataFrame({k:d['最高價'] for k,d in data.items()}).transpose()
high.index = pd.to_datetime(high.index)

low = pd.DataFrame({k:d['最低價'] for k,d in data.items()}).transpose()
low.index = pd.to_datetime(low.index)

volume = pd.DataFrame({k:d['成交股數'] for k,d in data.items()}).transpose()
volume.index = pd.to_datetime(volume.index)



def select_stock(stockno,year = None,month = None,day = None):
    if not year:
        date = datetime.datetime.now().year
    else:
        if not month:
            date = str(year)
        else:
            if not day:
                date = str(year)+'-'+str(month)
            else:
                date = str(year)+'-'+str(month)+'-'+str(day)
        
    stock = {
        'close':close[str(stockno)][str(date)].dropna().astype(float),
        'open':open[str(stockno)][str(date)].dropna().astype(float),
        'high':high[str(stockno)][str(date)].dropna().astype(float),
        'low':low[str(stockno)][str(date)].dropna().astype(float),
        'volume': volume[str(stockno)][str(date)].dropna().astype(float),
    }
    return stock

stock = select_stock(stockno)

