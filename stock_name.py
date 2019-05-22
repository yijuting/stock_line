# -*- coding: utf-8 -*-
"""
Created on Wed May 22 18:15:10 2019

@author: diana
"""

import pandas as pd
import requests
import re
import pickle
def fetch_table(url):
    """
    fetch table from the Internet
    Args:
        url: website url
    Return:
        pd_table : pandas table
    """
    
    
    # pretend to be the chrome brower to solve the forbidden problem
    header = {
      "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.75 Safari/537.36",
      "X-Requested-With": "XMLHttpRequest"
    }
    html_text = requests.get(url, headers=header)
    
    # to solve garbled text
    html_text.encoding =  html_text.apparent_encoding
    pd_table = pd.read_html(html_text.text)[0]
    
    return pd_table

def store_csv():
    """
    Store the information to csv file
    """
    url_stock = "http://isin.twse.com.tw/isin/C_public.jsp?strMode=2"
    url_otc = "http://isin.twse.com.tw/isin/C_public.jsp?strMode=4"
    stock_table = fetch_table(url_stock)
    stock_table.to_csv("stock_name.csv",index=None,encoding="utf_8_sig")
    otc_table = fetch_table(url_otc)
    otc_table.to_csv("otc_name.csv",index=None,encoding="utf_8_sig")

def extract_code(csv_string):
    """
    extract code from pandas data frame
    Args:
        index_range: a list which length is 2, containing start and end index
        csv_string : the name to the csv file
        
    Return:
        code_list: a list contain stock code
    """
    code = {}
    table = pd.read_csv(csv_string)    
    for i in range(2,len(table)):
        string = table.iloc[i][0]   
        if '\u3000' in string:
            code_temp = string.split('\u3000')
        elif ' ' in string:
            code_temp = string.split(' ')
        else:
            continue
        code.update({code_temp[0]:code_temp[1]})
        
    return code


#oct_code_list = extract_code([4452,5210],"otc_name.csv")
#print ("The length of oct:",len(oct_code_list))
#print(oct_code_list)
#
stock_code_list = extract_code("stock_name.csv")
print ("The length of stock:",len(stock_code_list))
print (stock_code_list)

with open('stock_name.pickle', 'wb') as handle:
    pickle.dump(stock_code_list, handle, protocol=pickle.HIGHEST_PROTOCOL)