PeriodGranularity = 60 # E.g. 15, 30, 60
# Train / Test split
MinsSincePrevPlay = 60   # Best to keep this at 60
newUsers = 10   # Num of randomly selected users to separate out of eval 2

# Root path
root = "C:/DS/Github/MusicRecommendation"  # BA, Windows
#root = "/home/badrul/Documents/github/MusicRecommendation" # BA, Linux

# Core
import numpy as np
import pandas as pd
from IPython.core.debugger import Tracer    # Used for debugging
import logging

# File and database management
import csv
import os
import sys
import json
import sqlite3
from pathlib import Path

# Date/Time
import datetime
import time
from datetime import timedelta
# Recommend switching to: http://arrow.readthedocs.io/en/latest/

# Visualization
from ggplot import *                        # Preferred
import matplotlib.pyplot as plt             # Quick

# Data science (comment out if not needed)
#from sklearn.manifold import TSNE
from sklearn.metrics import roc_curve, auc

# Misc
import random

#-------------- Custom Libs -----------------#
os.chdir(root)

# Import the codebase module
fPath = root + "/1_codemodule"
if fPath not in sys.path: sys.path.append(fPath)

# Custom Libs
import coreCode as cc
import lastfmCode as fm


# Function definition

def estBetaParams(mu, var):
    a = ((1 - mu) / var - 1 / mu) * mu ** 2
    b = a * (1 / mu - 1)
    return (a, b)


def getNextPlayProb_Beta(df, Timeslot):
    # Calculate posteriors: a=a+y and b=b+n-y
    playCount = df[df.Timeslot == Timeslot]['PlayCount'].sum()
    # Count num of weeks up to this point
    totalWks = len(df.PlayDate.dt.week.unique())
    a = priorDf.loc[timeslot]['a'] + playCount
    b = priorDf.loc[timeslot]['b'] + totalWks - playCount
    # Tracer()()
    mu = a / (a + b)
    # print(playCount,totalWks,a,b,mu)
    return mu


def toTimeSlot(dt, periodInterval):
    return str(int(dt.strftime('%w')) + 1) + dt.strftime('-%H-') + str(
        int((int(dt.strftime('%M')) / periodInterval + 1)))


def CalcProb(df):
    df.reset_index(inplace=True, drop=True)  # Important that this line is run every time the rest of it is run

    for i in range(0, df.shape[0]):  # let i go through 1 to length
        timeslot = df.iloc[i]['Timeslot']
        userID = df.iloc[i]['UserID']
        df2 = df.iloc[0:i][df.UserID == userID]  # Extract just rows up to point i for this user
        res = getNextPlayProb_Beta(df2, timeslot)  # Filter for the specific user and pass to function
        df.loc[(i), 'EstProb'] = res
    return df

settingsDict =  cc.loadSettings()
dbPath = root + settingsDict['mainDbPath']
fmSimilarDbPath = root + settingsDict['fmSimilarDbPath']
fmTagsDbPath = root + settingsDict['fmTagsDbPath']
trackMetaDbPath = root + settingsDict['trackmetadata']

# Fetch the test data
con = sqlite3.connect(dbPath)

SQLStr="""
SELECT M.UserID, PlayDate, Timeslot, count(*) as PlayCount from tblMainAgg as M 
INNER JOIN tblUsers ON M.UserID = tblUsers.UserID 
WHERE tblUsers.TestUser =1 GROUP BY M.UserID, PlayDate, Timeslot""".format(PeriodGranularity)
testDf = pd.read_sql_query(SQLStr, con)

con.close()
testDf["PlayDate"] = pd.to_datetime(testDf["PlayDate"])
testDf.sort_values(['UserID','PlayDate'], inplace=True)
print ('User IDs of test users',testDf['UserID'].unique())


p= testDf.PlayDate.drop_duplicates()
p - pd.to_timedelta(p.dt.dayofweek, unit='D')


