import pandas as pd
import json
import os
import csv
import random
import sqlite3
from pathlib import Path


def loadSettings():

    with open('2_settings/settings.json') as json_data:
        s = json.load(json_data)
        return s

def create_connection(dbPath):
    """ create a database connection to a SQLite database """
    try:
        conn = sqlite3.connect(dbPath)
        print(sqlite3.version)
    except Error as e:
        print(e)
    finally:
        conn.close()


def exportToCSV(cursor, fPath):
    # Check output folder exists
    _ensurePathExists(fPath)

    with open(fPath, "w", newline='') as csv_file:  # Python 3 version
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow([i[0] for i in cursor.description])  # write headers
        csv_writer.writerows(cursor)


def _ensurePathExists(fPath):
    path = Path(fPath)
    path.parent.mkdir(parents=True, exist_ok=True)


def dropCreateTable(dbCursor,tblName, tblSelect):
    sqlStr= 'DROP TABLE IF EXISTS {}'.format(tblName)
    dbCursor.execute(sqlStr)

    sqlStr ="CREATE TABLE {}".format(tblName) + " AS " + tblSelect
    dbCursor.execute(sqlStr)

def createDateTimeRange(startDT,endDT, minsToAdd):
    DTArray = [startDT]
    dt = startDT

    while  dt < endDT:
        dt=dt + pd.Timedelta(minutes=minsToAdd)
        DTArray.append(dt)
    return DTArray

def padRows(X,Y,batch_size):
    rowsToPad=0
    if np.mod(len(X),batch_size) != 0:
        # tf requires consistent inputs so need to pad
        rowsToPad=batch_size-np.mod(len(X),batch_size)
        p=np.zeros([rowsToPad,X.shape[1]])
        X = np.append(X,p,axis=0)

        p=np.zeros([rowsToPad,Y.shape[1]])
        Y = np.append(Y,p,axis=0)
    return (X,Y,rowsToPad)


#### Disseration specific code ###
def getUsers(dbPath):
    con = sqlite3.connect(dbPath)
    c = con.cursor()

    # Get list of UserIDs
    users = pd.read_sql_query("Select UserID from tblUsers Where tblUsers.TestUser = 0",con)
    con.close()
    return users

def getTrainTestData(dbPath,fieldList, userIDs=None, periodGranularity =30,displayWarnings = True):
    # Returns data as a Pandas dataframe
    # fieldList is a comma separated string and specifies the fields to bring back in field1, field2 ... format
    # If userIDs is not provided, then returns all data

    con = sqlite3.connect(dbPath)
    c = con.cursor()

    df = pd.read_sql_query("Select UserID from tblUsers Where tblUsers.TestUser = 0", con)
    if userIDs is None: userIDs = df.userID.values  # If Not provided assume all users

    trainDf = pd.DataFrame(columns=[fieldList])  # Create an empty df
    testDf = pd.DataFrame(columns=[fieldList])  # Create an empty df
    periodsInAMonth = int(60 / periodGranularity) * 24 * 7 * 4
    totalRows = 0

    for u in userIDs:
        # Get training dataset
        SqlStr = "SELECT {} from tblTimeSeriesData where UserID = {}".format(fieldList, u)
        df = pd.read_sql_query(SqlStr, con)

        if len(df) > int(periodsInAMonth * 3):  # user must have at least 3 months worth of data
            totalRows += len(df)

            # Cut-off 1
            k = random.randint(periodsInAMonth, len(df))

            testDf = testDf.append(df.iloc[k:k + periodsInAMonth])[df.columns.tolist()]

            tmp = df.drop(df.index[k:k + periodsInAMonth])

            # Cut-off 2
            k = random.randint(periodsInAMonth, len(tmp))
            testDf = testDf.append(tmp.iloc[k:k + periodsInAMonth])[df.columns.tolist()]
            trainDf = trainDf.append(tmp.drop(tmp.index[k:k + periodsInAMonth]))[df.columns.tolist()]
        else:
            if displayWarnings: print('Skipping user {} as not enough periods ({})'.format(u, len(df)))

    return trainDf, testDf
