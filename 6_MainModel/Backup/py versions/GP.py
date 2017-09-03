root = "/home/badrul/git/EventPrediction" # BA, Linux
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
#from datetime import timedelta # Deprecated

# Visualization
#import matplotlib.pyplot as plt             # Quick
#%matplotlib inline

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

# Data science (comment out if not needed)
#from sklearn.manifold import TSNE
import tensorflow as tf
from tensorflow.contrib import rnn
from tensorflow.python.framework import ops
ops.reset_default_graph()
from sklearn import metrics
from sklearn import preprocessing
import GPflow


def getTrainAndTestData():
    con = sqlite3.connect(dbPath)
    c = con.cursor()

    # Get list of UserIDs
    users = pd.read_sql_query("Select UserID from tblUsers Where tblUsers.TestUser = 0", con)

    fieldList = "t, UserID, HrsFrom6pm, isSun,isMon,isTue,isWed,isThu,isFri,isSat,t1,t2,t3,t4,t5,t10,t12hrs,t24hrs,t1wk,t2wks,t3wks,t4wks"
    trainDf = pd.DataFrame(columns=[fieldList])  # Create an emmpty df
    testDf = pd.DataFrame(columns=[fieldList])  # Create an emmpty df
    periodsInAMonth = int(60 / periodGranularity) * 24 * 7 * 4

    totalRows = 0

    for user in users.itertuples():
        # Get training dataset
        SqlStr = "SELECT {} from tblTimeSeriesData where UserID = {}".format(fieldList, user.userID)
        df = pd.read_sql_query(SqlStr, con)
        totalRows += len(df)

        # Cut-off 1
        k = random.randint(periodsInAMonth, len(df))
        # Tracer()()  -- for debugging purposes
        testDf = testDf.append(df.iloc[k:k + periodsInAMonth])[df.columns.tolist()]

        tmp = df.drop(df.index[k:k + periodsInAMonth])

        # Cut-off 2
        k = random.randint(periodsInAMonth, len(tmp))
        testDf = testDf.append(tmp.iloc[k:k + periodsInAMonth])[df.columns.tolist()]
        trainDf = trainDf.append(tmp.drop(tmp.index[k:k + periodsInAMonth]))[df.columns.tolist()]

    if len(trainDf) + len(testDf) == totalRows:
        print('Ok')
    else:
        print("Incorrect. Total Rows = {}. TestDf+TrainDf rows = {}+{}={}".format(totalRows, len(testDf), len(trainDf),
                                                                                  len(testDf) + len(trainDf)))

    return trainDf, testDf


def getHiddenTestUsers(firstNPerc=1.0):
    con = sqlite3.connect(dbPath)
    c = con.cursor()

    # Get list of UserIDs
    users = pd.read_sql_query("Select UserID from tblUsers Where tblUsers.TestUser = 1", con)

    fieldList = "t, PeriodID, UserID, HrsFrom6pm, isSun,isMon,isTue,isWed,isThu,isFri,isSat,t1,t2,t3,t4,t5,t10,t12hrs,t24hrs,t1wk,t2wks,t3wks,t4wks"
    testDf = pd.DataFrame(columns=[fieldList])  # Create an emmpty df
    periodsInAMonth = int(60 / periodGranularity) * 24 * 7 * 4

    totalRows = 0

    for user in users.itertuples():
        # Get training dataset
        SqlStr = "SELECT {} from tblTimeSeriesData where UserID = {}".format(fieldList, user.userID)

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

settingsDict =  cc.loadSettings()
dbPath = root + settingsDict['mainDbPath']
fmSimilarDbPath = root + settingsDict['fmSimilarDbPath']
fmTagsDbPath = root + settingsDict['fmTagsDbPath']
trackMetaDbPath = root + settingsDict['trackmetadata']
periodGranularity = int(settingsDict['periodGranularity'])

trainDf,testDf = getTrainAndTestData()
#trainDf['t'].replace(to_replace='0', value='-1', inplace=True)
#testDf['t'].replace(to_replace='0', value='-1', inplace=True)
xTrain = trainDf.drop(['t','UserID'], 1).values

yTrain = trainDf['t'].values.astype(int)
yTrain = yTrain.reshape(len(yTrain),1)

# Test data
xTest= testDf.drop(['t','UserID'], 1).values
yTest = testDf['t'].values.astype(int)
#yTest = np.array([1 if y==1 else -1 for y in yTest])
yTest = yTest.reshape(len(yTest),1)

training_iteration = 20
batch_size = 10000
# Launch the graph
sess = tf.Session()

k = GPflow.kernels.Matern52(1, lengthscales=0.3)

# Training cycle
for iteration in range(training_iteration):
    total_batch = int(len(xTrain) / batch_size)

    # Loop over all batches
    # for i in range(total_batch):
    # batch_x = xTrain[i*batch_size:(i*batch_size)+batch_size]
    # batch_y = yTrain[i*batch_size:(i*batch_size)+batch_size]

    # m = GPflow.gpr.GPR(np.array(batch_x, dtype=float), np.array(batch_y, dtype=float), kern=k)
    # m.likelihood.variance = 0.01

print('ok')
m = GPflow.gpr.GPR(np.array(xTrain, dtype=float), np.array(yTrain, dtype=float), kern=k)
m.likelihood.variance = 0.01
print(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + " Training completed!")

n=1
predictions, var = m.predict_y(xTest[0:n])  # One row of input
print(metrics.classification_report(yTest[0:n],predictions[0:n]))
print("* Precision = labelled as x / how many were actually x in the ones that were labelled")
print("* Recall = labelled as x / how many were actually x in the dataset\r")
print ("0.0 Did not play music. 1.0 = Played muisc\r")