import numpy as np
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

def padRows(X,Y,batch_size, reverse=False):
    rowsToPad=0
    if np.mod(len(X),batch_size) != 0:
        # tf requires consistent inputs so need to pad
        rowsToPad=batch_size-np.mod(len(X),batch_size)
        p1=np.zeros([rowsToPad,X.shape[1]])
        p2=np.zeros([rowsToPad,Y.shape[1]])
        if reverse:
            Y = np.append(p1, Y, axis=0)
            Y = np.append(p2,Y,axis=0)
        else:
            X = np.append(X, p1, axis=0)
            Y = np.append(Y, p2, axis=0)
    return (X,Y,rowsToPad)


#### Disseration specific code ###
def getUsers(dbPath):
    con = sqlite3.connect(dbPath)
    c = con.cursor()

    # Get list of UserIDs
    users = pd.read_sql_query("Select UserID from tblUsers Where tblUsers.TestUser = 0",con)
    con.close()
    return users

def _getTrainTestData(dbPath,tblName, fieldList, userIDs=None, periodGranularity =30,displayWarnings = True):
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
        SqlStr = "SELECT {} from {} where UserID = {}".format(fieldList, tblName, u)
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


def getHiddenPeriodsData(dbPath, tblName, fieldList, oneHot, userIDs=None,periodGranularity =30):
    trainDf, testDf = _getTrainTestData(dbPath, tblName, fieldList, userIDs, periodGranularity)
    if trainDf.shape[0] == 0:
        # No rows
        return None, None, None, None

    ### Train data
    xTrain = trainDf.drop(['t', 'UserID'], 1).values

    # Test data
    xTest = testDf.drop(['t', 'UserID'], 1).values

    if oneHot:
        # One-Hot version
        yTrain_onehot = pd.get_dummies(trainDf['t']).values.astype(float)  # One-Hot version
        yTest_onehot = pd.get_dummies(testDf['t']).values.astype(float)
        return xTrain, yTrain_onehot, xTest, yTest_onehot
    else:
        yTrain = trainDf['t'].values.astype(int)
        yTrain = yTrain.reshape(len(yTrain), 1)
        yTest = testDf['t'].values.astype(int)
        yTest = yTest.reshape(len(yTest), 1)
        return xTrain, yTrain, xTest,yTest


def _getHiddenUsersDataDf(dbPath, tblName, fieldList, periodGranularity=30, firstNPerc=1.0):
    con = sqlite3.connect(dbPath)
    c = con.cursor()

    # Get list of UserIDs
    users = pd.read_sql_query("Select UserID from tblUsers Where tblUsers.TestUser = 1", con)

    # fieldList="t, PeriodID, UserID, HrsFrom6pm, isSun,isMon,isTue,isWed,isThu,isFri,isSat,t1,t2,t3,t4,t5,t10,t12hrs,t24hrs,t1wk,t2wks,t3wks,t4wks"
    testDf = pd.DataFrame(columns=[fieldList])  # Create an emmpty df
    periodsInAMonth = int(60 / periodGranularity) * 24 * 7 * 4

    totalRows = 0

    for user in users.itertuples():
        # Get training dataset

        SqlStr = "SELECT {} from {} where UserID = {}".format(fieldList + ",PeriodID", tblName, user.userID)
        df = pd.read_sql_query(SqlStr, con)
        df["PeriodID"] = df["PeriodID"].astype(int)
        df.sort_values(['PeriodID'])
        totalRows += len(df)
        # Caluclate period cutt-off
        cutoff = int(len(df) * firstNPerc)
        testDf = testDf.append(df.iloc[0:cutoff])[df.columns.tolist()]

    testDf["PeriodID"] = testDf["PeriodID"].astype(int)
    testDf["UserID"] = testDf["UserID"].astype(int)
    testDf.sort_values(['UserID', 'PeriodID'], inplace=True)

    return testDf


def getHiddenUsersData(dbPath, tblName, fieldList, oneHot,firstNPerc=0.5, periodGranularity = 30):
    testDf2 = _getHiddenUsersDataDf(dbPath, tblName, fieldList, periodGranularity,firstNPerc)  # Get the first half of everyones history

    # Get hidden users data
    xTest2 = testDf2.drop(['t', 'UserID', 'PeriodID'], 1).values
    yTest2 = testDf2['t'].values.astype(int)
    yTest2 = yTest2.reshape(-1, 1)

    if oneHot:
        # One-Hot version
        yTest2_onehot = pd.get_dummies(testDf2['t']).values.astype(float)
        return xTest2, yTest2_onehot,testDf2
    else:
        return xTest2, yTest2,testDf2