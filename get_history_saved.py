# -*- coding: utf-8 -*-
"""
Created on Thu Jun 13 23:59:54 2019

@author: diana
"""

import requests
from io import StringIO
import pandas as pd
import numpy as np
from datetime import datetime
import time
from matplotlib import pyplot as plt
import peakutils
import pickle


import talib
import twstock
import random

from apscheduler.schedulers.blocking import BlockingScheduler
from plot_candles import lineNotify, plot_candles

import pymongo

client = pymongo.MongoClient()
db = client['stock']

collect2 = db['Collections']

data = collect2.find({'earn':{"$gt": 3000}},{'stockno':1,'data':1,'_id':0}).sort(
        [("earn", pymongo.DESCENDING)])

for item in data:
    for col, element in item.items():
            if col == 'stockno':
                stockno = element
            else:
                data = pd.DataFrame(element)
