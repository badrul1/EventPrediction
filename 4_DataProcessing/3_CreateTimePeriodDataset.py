# Root path
#root = "C:/DS/Github/MusicRecommendation"  # BA, Windows
root = "/home/badrul/git/EventPrediction"  # BA, Linux


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
#import time
#from pendulum import Pendulum

# Visualization
#from ggplot import *                        # Preferred vis tool
import matplotlib.pyplot as plt             # Quick viz tool
#get_ipython().magic('matplotlib inline')

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


settingsDict =  cc.loadSettings()
dbPath = root + settingsDict['mainDbPath']
fmSimilarDbPath = root + settingsDict['fmSimilarDbPath']
fmTagsDbPath = root + settingsDict['fmTagsDbPath']
trackMetaDbPath = root + settingsDict['trackmetadata']
periodGranularity = int(settingsDict['periodGranularity'])


con = sqlite3.connect(dbPath)
cur = con.cursor()

SQLStr = "Select PlayedTimestamp from tblMain"
tblMain = pd.read_sql_query(SQLStr, con)
tblMain.PlayedTimestamp = pd.to_datetime(tblMain.PlayedTimestamp)

startDT = tblMain.PlayedTimestamp.min()
endDT = tblMain.PlayedTimestamp.max()

# This is the main line. Makes a call to code stored in the core module.
dtArray = cc.createDateTimeRange(startDT,endDT, periodGranularity)

# Save to db and create the 'HrsFrom6pm' field too
cur.execute('Delete from tblPeriod')
for idx, dt in enumerate(dtArray):
    HrsFrom5pm = abs(int(dt.strftime('%H')) - 17)
    SqlStr="INSERT INTO tblPeriod (PeriodID, PeriodDateTime, HrsFrom5pm) VALUES ({},'{}',{})".format(idx, dt,HrsFrom5pm)
    cur.execute(SqlStr)

con.commit()
con.close()
print('Insert into tbl period... Ok')

con = sqlite3.connect(dbPath)
cur = con.cursor()

# tblPeriod
SQLStr = "Select * from tblPeriod"
tblPeriod = pd.read_sql_query(SQLStr, con)
tblPeriod.PeriodDateTime = pd.to_datetime(tblPeriod.PeriodDateTime)

# tblUser
SQLStr = "Select UserID as UserID, FirstPlay, LastPlay, TestUser from tblUsers"
tblUser = pd.read_sql_query(SQLStr, con)
tblUser.FirstPlay = pd.to_datetime(tblUser.FirstPlay)
tblUser.LastPlay = pd.to_datetime(tblUser.LastPlay)
# Bring in the PeriodID into tblUsers for the First and Last play
idx = tblPeriod.PeriodDateTime.searchsorted(tblUser['FirstPlay'].values)
tblUser['FirstPlayPeriodID'] = idx
idx = tblPeriod.PeriodDateTime.searchsorted(tblUser['LastPlay'].values)
tblUser['LastPlayPeriodID'] = idx

# tblMain
SQLStr = "Select UserID, PlayedTimestamp from tblMain"
tblMain = pd.read_sql_query(SQLStr, con)
tblMain.PlayedTimestamp = pd.to_datetime(tblMain.PlayedTimestamp)
# Bring in the PeriodID into tblMain
idx = tblPeriod.PeriodDateTime.searchsorted(tblMain['PlayedTimestamp'].values)
tblMain['PeriodID'] = idx

# Drop the timetamp col and just use periodID
tblMain=tblMain.groupby(['UserID','PeriodID']).count().reset_index()

con.close()
print('TblMain...Ok')

con = sqlite3.connect(dbPath)
cur = con.cursor()

SqlStr = "Delete from tblMain2"
cur.execute(SqlStr)
con.commit()

for row in tblUser.itertuples():
    m = tblMain[tblMain.UserID == row.UserID]
    for pid in range (row.FirstPlayPeriodID,row.LastPlayPeriodID):
        # Check if the user listened to music in this period
        playedMusic = m[m.PeriodID == pid]
        playedMusic = (len(playedMusic) > 0) *1
        SqlStr="Insert into tblMain2 (UserID, PeriodID, PlayedMusic) Values ({},{},{})".format(row.UserID, pid,playedMusic)
        cur.execute(SqlStr)    

con.commit()
con.close()
print('Ok')


# Some quick checks
con = sqlite3.connect(dbPath)
SQLStr = "Select * from tblMain2"
tblMain2 = pd.read_sql_query(SQLStr, con)
con.close()

tblMain2.head(20)


a=tblMain2[0:336].plot.scatter('PeriodID', 'PlayedMusic')
a.set_title('1 week period')

con = sqlite3.connect(dbPath)
c = con.cursor()

# Create tblTimeSeriesData
c.execute('DROP TABLE IF EXISTS tblTimeSeriesData')
sqlStr = "CREATE TABLE 'tblTimeSeriesData' ('PeriodID' Integer, 'UserID' Integer, 'HrsFrom5pm' Integer, 'isSun' Integer, 'isMon' Integer, 'isTue' Integer, 'isWed' Integer, 'isThu' Integer, 'isFri' Integer, 'isSat' Integer, 't' integer, 't1' Integer, 't2' Integer,'t3' Integer,'t4' Integer,'t5' Integer,'t10' Integer,'t12hrs' Integer,'t23_5hrs' Integer,'t24hrs' Integer,'t24_5hrs' Integer,'t1wk' Integer,'t2wks' Integer,'t3wks' Integer,'t4wks' Integer)"
c.execute(sqlStr)

# Go through each user
for row in tblUser.itertuples():
    print('Processing user {} of {}'.format(row.UserID, tblUser.shape[0]))
    userID = row.UserID
    # Bring back the data for that user
    SQLStr = "Select * from tblMain2 where UserID = {} order by PeriodID".format(userID)
    tblMain2 = pd.read_sql_query(SQLStr, con)
    tblMain2.sort_values('PeriodID')
    tblMain2.set_index('PeriodID',inplace = True)

    minPeriodID = tblMain2.index.min()
    maxPeriodID = tblMain2.index.max()
    periodsInMonth = int(60/periodGranularity)*24*7*4
    
    # Go through all the periods for this user and turn into time-series data
    for i in range(minPeriodID+periodsInMonth,maxPeriodID):
        
        periodDt = tblPeriod[tblPeriod.PeriodID == i].PeriodDateTime
        HrsFrom5pm = int(tblPeriod[tblPeriod.PeriodID == i].HrsFrom5pm)
        dayOfWk = int(periodDt.dt.strftime('%w'))
        isSun = (dayOfWk ==0)*1
        isMon = (dayOfWk ==1)*1
        isTue = (dayOfWk ==2)*1
        isWed = (dayOfWk ==3)*1
        isThu = (dayOfWk ==4)*1
        isFri = (dayOfWk ==5)*1
        isSat = (dayOfWk ==6)*1

        t =int(tblMain2.loc[i].PlayedMusic)
        t1 = int(tblMain2.loc[i-1].PlayedMusic)
        t2 = int(tblMain2.loc[i-2].PlayedMusic)
        t3 = int(tblMain2.loc[i-3].PlayedMusic)
        t4 = int(tblMain2.loc[ i-4].PlayedMusic)
        t5 = int(tblMain2.loc[i-5].PlayedMusic)
        t10 = int(tblMain2.loc[i-10].PlayedMusic)
        
        t12hrs = int(tblMain2.loc[i-int(60/periodGranularity)*12].PlayedMusic)   
        t23_5hrs = int(tblMain2.loc[i-int(60/periodGranularity)*23.5].PlayedMusic)
        t24hrs = int(tblMain2.loc[i-int(60/periodGranularity)*24].PlayedMusic)
        t24_5hrs = int(tblMain2.loc[i-int(60/periodGranularity)*24.5].PlayedMusic)
        t1wk = int(tblMain2.loc[i-int(60/periodGranularity)*168].PlayedMusic)
        t2wks = int(tblMain2.loc[i-int(60/periodGranularity)*336].PlayedMusic)
        t3wks = int(tblMain2.loc[i-int(60/periodGranularity)*504].PlayedMusic)
        t4wks = int(tblMain2.loc[i-int(60/periodGranularity)*672].PlayedMusic)

        SqlStr = "Insert into tblTimeSeriesData (PeriodID, UserID, HrsFrom5pm, isSun,isMon,isTue,isWed,isThu,isFri,isSat,t,t1,t2,t3,t4,t5,t10,t12hrs,t23_5hrs, t24hrs, t24_5hrs, t1wk,t2wks,t3wks,t4wks) Values ({},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{})".format(i,userID,HrsFrom5pm,isSun,isMon,isTue,isWed,isThu,isFri,isSat,t,t1,t2,t3,t4,t5,t10,t12hrs,t23_5hrs,t24hrs,t24_5hrs,t1wk,t2wks,t3wks,t4wks)
        c.execute(SqlStr)

con.commit()
con.close()
print('Completed')