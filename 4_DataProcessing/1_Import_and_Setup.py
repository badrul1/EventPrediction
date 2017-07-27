import os
import sys
import pandas as pd
import csv
import json
import sqlite3
import logging

## Parameters you can change

# Abs path to settings file
#root = "C:/DS/Github/MusicRecommendation"  # BA, Windows
root = "/home/badrul/git/EventPrediction"  # BA, Linux

# Select the dataset to view
datasetToUse ="inputfile_sml" # inputfile , inputfile_hlf , or inputfile_verysml


## Finish setting up
os.chdir(root)
## Add the prelim module
fPath = root + "/1_codemodule"
if fPath not in sys.path: sys.path.append(fPath)
from coreCode import *

settingsDict =  loadSettings()
inputFilePath = root + settingsDict[datasetToUse]
dbPath = root + settingsDict['mainDbPath']
logging.basicConfig(filename= root + '/errlog.log',level=logging.DEBUG)

def dropCreateTable(dbCursor,tblName, tblSelect):
    sqlStr= 'DROP TABLE IF EXISTS {}'.format(tblName)
    dbCursor.execute(sqlStr)

    sqlStr ="CREATE TABLE {}".format(tblName) + " AS " + tblSelect
    dbCursor.execute(sqlStr)

db = sqlite3.connect(dbPath)

colHeadings=['UserID','PlayedTimestamp','ArtistID','ArtistName','TrackID','TrackName']
dataFormat={'UserID': str, 'PlayedTimestamp': str, 'ArtistID' :str, 'ArtistName': str, 'TrackID': str, 'TrackName': str}

parse_dates = ['PlayedTimestamp']

# Load data from CSV
inpData = pd.read_csv(inputFilePath, sep='\t', error_bad_lines= False,quoting=csv.QUOTE_NONE, header=None,names=colHeadings, dtype=dataFormat,parse_dates=parse_dates)
inpData.to_sql('tblInputData', db, flavor='sqlite',
                                            schema=None, if_exists='replace', index=True,
                                            index_label=None, chunksize=None, dtype=None)


db = sqlite3.connect(dbPath)
c = db.cursor()

dropCreateTable(c,'tblTracks', 'Select TrackID, TrackName, ArtistID, ArtistName from tblInputData group By trackID')
dropCreateTable(c,'tblUserDailyPlays', 'SELECT Cast(substr(userID,-5) as integer) as UserID, date(PlayedTimestamp),count(*) as NumOfPlays, count(Distinct trackID) as NumOfTracks from tblInputData group by userID, date(PlayedTimestamp) ORDER BY NumOfPlays')
dropCreateTable(c,'tblUsers', 'SELECT Cast(substr(userID,-5) as integer) as userID, min(PlayedTimestamp) as FirstPlay, max(PlayedTimestamp) as LastPlay,0 as TestUser, 0 as TestCutOff from tblInputData Group by Cast(substr(userID,-5) as integer)')
db.close()

db = sqlite3.connect(dbPath)
c=db.cursor()

newFields = 'FirstPlayed, MinsSinceFirstPlay integer, MinsSincePrevPlay integer, MinsSinceNextPlay integer, historyID integer'

# Create tblMain
c=db.cursor()
c.execute('DROP TABLE IF EXISTS tblMain')
tblMain_SQL = 'CREATE TABLE tblMain (UserID integer, PlayedTimestamp text, ArtistID text, TrackID text, ' + newFields +')';

c.execute(tblMain_SQL)

# Create PlayTimetable
c.execute('DROP TABLE IF EXISTS tblPlayTimetable')
sqlStr = "CREATE TABLE 'tblPlayTimetable' ('userID' INTEGER,"

for i in range (1,169):
    sqlStr += "'%s' INTEGER," %i 
    

sqlStr +="PRIMARY KEY('userID'));"
db = sqlite3.connect(dbPath)
c = db.cursor()
c.execute(sqlStr)
db.commit()
db.close()

db = sqlite3.connect(dbPath)
c = db.cursor()
sqlStr ="""SELECT CAST(substr(tblInputData.userID,-5) as integer) as UserID, 
(strftime('%s',tblInputData.PlayedTimestamp) - strftime('%s',tblUsers.FirstPlay))/60 as MinsSinceFirstPlay, 
tblUsers.FirstPlay, PlayedTimestamp, 
ArtistID, TrackID 
FROM tblInputData 
INNER JOIN tblUsers ON Cast(substr(tblInputData.userID,-5) as integer) = tblUsers.userID 
ORDER BY UserID,MinsSinceFirstPlay"""
res =c.execute(sqlStr)

rowCount = 1
userID=0
MinsSinceFirstPlay = ""

d = db.cursor()
d.execute('Delete from tblMain')
db.commit()

for row in res:   
    tmp=list(row)
    
    if tmp[0] != userID:   # Start of a new user
        rowCount = 1
        userID = int(row[0])
        MinsSinceFirstPlay = tmp[1]          
        MinsSincePrevPlay = tmp[1]
    else:
        MinsSincePrevPlay = tmp[1] - MinsSinceFirstPlay
        MinsSinceFirstPlay = tmp[1] 
    
    
    tmp.append(str(rowCount))
    tmp.append(str(MinsSincePrevPlay))
    
    tmp = ['Null' if v is None else v for v in tmp]
    tmp2 = [t.replace("\\\'R","''R") if type(t)=='str' else t for t in tmp] 
    tmp2 = [t.replace("\\\'S","''S") if type(t)=='str' else t for t in tmp2] 
    tmp2=str(tuple(tmp2))
    
    insertStr = "Insert into tblMain (UserID, MinsSinceFirstPlay, FirstPlayed, PlayedTimeStamp, ArtistID, TrackID, historyID, MinsSincePrevPlay) Values " + tmp2
    try:
        d.execute(insertStr)
        rowCount +=1
    except:
        logging.warning(str(row))
        logging.warning(insertStr)
    
    
db.commit()
db.close()


db = sqlite3.connect(dbPath)
c = db.cursor()
SqlStr = "Update tblMain Set MinsSinceNextPlay = (Select MinsSincePrevPlay from tblMain as b where b.UserID = UserID and b.HistoryID = HistoryID + 1)"
c.execute(SqlStr)
db.commit()
db.close()


db = sqlite3.connect(dbPath)
c = db.cursor()

# Create PlayTimetable
c.execute('DROP TABLE IF EXISTS tblPeriod')
sqlStr = "CREATE TABLE 'tblPeriod' ('PeriodID' INTEGER PRIMARY KEY,'PeriodDateTime' Timestamp,'HrsFrom6pm' Integer)"
c.execute(sqlStr)
db.close()

db = sqlite3.connect(dbPath)
c = db.cursor()

# Create PlayTimetable
c.execute('DROP TABLE IF EXISTS tblMain2')
sqlStr = "CREATE TABLE 'tblMain2' ('UserID' INTEGER,'PeriodID' Integer, 'PlayedMusic' Integer)"
c.execute(sqlStr)
db.close()