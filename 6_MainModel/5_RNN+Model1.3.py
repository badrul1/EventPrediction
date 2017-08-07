# Root path
#root = "C:/DS/Github/MusicRecommendation"  # BA, Windows
root = "/home/badrul/git/EventPrediction" # BA, Linux
#root = "/home/ubuntu/EventPrediction" # BA, Aws

# Core
import numpy as np
import pandas as pd
from IPython.core.debugger import Tracer    # Used for debugging
import logging
from random import *

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

# Visualization
import matplotlib.pyplot as plt             # Quick

# Misc
import random
import importlib
import warnings
warnings.filterwarnings('ignore')
import logging
logging.basicConfig(filename='RNN.log',level=logging.DEBUG)

#-------------- Custom Libs -----------------#
os.chdir(root)

# Import the codebase module
fPath = root + "/1_codemodule"
if fPath not in sys.path: sys.path.append(fPath)

# Custom Libs
import coreCode as cc
import lastfmCode as fm


# Data science (comment out if not needed)
import tensorflow as tf
from tensorflow.contrib import rnn
from tensorflow.python.framework import ops
ops.reset_default_graph()
from sklearn import metrics
from sklearn import preprocessing


settingsDict =  cc.loadSettings()
dbPath = root + settingsDict['mainDbPath']
fmSimilarDbPath = root + settingsDict['fmSimilarDbPath']
fmTagsDbPath = root + settingsDict['fmTagsDbPath']
trackMetaDbPath = root + settingsDict['trackmetadata']
periodGranularity = int(settingsDict['periodGranularity'])


def RNN(x, weights, biases,n_steps):
    # Current data input shape: (batch_size, n_steps, n_input)
    # Required shape: 'n_steps' tensors list of shape (batch_size, n_input)
    
    # Unstack to get a list of 'n_steps' tensors of shape (batch_size, n_input)
    x = tf.unstack(x, n_steps, 1)  # See https://stackoverflow.com/questions/45278276/tensorflow-lstm-dropout-implementation-shape-problems/45279243#45279243

    # Define a lstm cell with tensorflow
    if cellType == "BasicLSTMCell":
        lstm_cell = rnn.BasicLSTMCell(n_hidden, forget_bias=1.0)
        outputs, states = rnn.static_rnn(lstm_cell, x, dtype=tf.float32)
    elif cellType == "TimeFreqLSTMCell":
        lstm_cell =rnn.TimeFreqLSTMCell(n_hidden, use_peepholes=True, feature_size= 22, forget_bias=1.0)
        outputs, states = rnn.static_rnn(lstm_cell, x, dtype=tf.float32)
    elif cellType == "GridLSTMCell":
        lstm_cell =rnn.GridLSTMCell(n_hidden, forget_bias=1.0)
        outputs, states = rnn.static_rnn(lstm_cell, x, dtype=tf.float32)        
    else:
        print("Did not recognize {}".format(cellType))
    # Get lstm cell output
    

    # Linear activation, using rnn inner loop last output
    return tf.matmul(outputs[-1], weights['out']) + biases['out']

def buildGraph(n_steps,n_input):
    global x, y, pred, cost, optimizer,accuracy
    
    tf.reset_default_graph()
    # tf Graph input
    
    x = tf.placeholder("float", [None, n_steps, n_input])
    y = tf.placeholder("float", [None, n_classes])

    # Define weights
    weights = {
        'out': tf.Variable(tf.random_normal([n_hidden, n_classes]))
    }
    biases = {
        'out': tf.Variable(tf.random_normal([n_classes]))
    }

    pred = RNN(x, weights, biases,n_steps)[-1]  # We only want the last item in the predictions
    cost = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits(logits=pred, labels=y[-1]))
    optimizer = tf.train.AdamOptimizer(learning_rate=learning_rate).minimize(cost)
    
    # Evaluate model
    correct_pred = tf.equal(tf.argmax(pred,1), tf.argmax(y,1))
    accuracy = tf.reduce_mean(tf.cast(correct_pred, tf.float32))


# In[16]:


# Build the graph
loadFromSave = False
n_steps = 1 # timesteps
n_hidden = 160 # hidden layer num of features
n_classes = 2
batch_size = 10 #1344
learning_rate = 0.001
cellType = "BasicLSTMCell"  # Choose: TimeFreqLSTMCell BasicLSTMCell

#fieldList="UserID, t, HrsFrom5pm, isSun,isMon,isTue,isWed,isThu,isFri,isSat, t1,t2,t3,t4,t5,t10,t12hrs,t23_5hrs,t24hrs,t24_5hrs,t1wk,t2wks,t3wks,t4wks"
fieldList="UserID, t, HrsFrom6pm, isSun,isMon,isTue,isWed,isThu,isFri,isSat, t10,t12hrs,t24hrs,t1wk,t2wks,t3wks,t4wks"
n_input = len(fieldList.split(","))-2 # -2 as we drop UserID and t

# Build graph
buildGraph(n_steps,n_input = n_input)
# Initializing the variables
sess = tf.Session()
init = tf.global_variables_initializer()
saver = tf.train.Saver()
if loadFromSave:
    saver.restore(sess,'./3_Data/saves/model.ckpt')
else:
    sess.run(init)


# Launch the graph
def trainModel(X, Y, sess,training_iterations = 5):
    # Training cycle
    l=np.shape(xTrain)[0]
    for i in range(training_iterations):
        logging.info("Now on iteration {}".format(i))
        # Loop over all rows in order of earliest to latest
        for pos in range(0+batch_size, l,3):
            if (pos % 10000) == 0: 
                #print("Now on pos {} of {} ({}%)".format(pos,l,round((pos/l)*100,2)))
                logging.info("Now on pos {} of {} ({}%)".format(pos,l,round((pos/l)*100,2)))
            
            # For each row, collect the previous batch_size num of rows
            batch_x = X[pos-batch_size:pos]
            batch_y = Y[pos-batch_size:pos]                        
            #if np.mod(len(batch_x),batch_size) == 0:batch_x, batch_y, _ = cc.padRows(batch_x, batch_y, batch_size)
            batch_x = batch_x.reshape((batch_size, n_steps, n_input))  # Rehsape into 3d, even though n_steps is 1            
            tf.Print(x,[x])
            sess.run(optimizer, feed_dict={x: batch_x, y: batch_y})


# Train the model
training_iterations = 5
sample_iteration = 2
display_step = 5
userSample =10

for s in range(sample_iteration):
    print('Now processing sample {}'.format(s))
    logging.info('Now processing sample {}'.format(s))
    users=cc.getUsers(dbPath).sample(userSample)
    for usr in users.itertuples():
        print('Now processing User {}'.format(usr.userID))
        logging.info('Now processing User {}'.format(usr.userID))
        xTrain, yTrain_onehot, xTest, yTest_onehot = cc.getHiddenPeriodsData(dbPath,fieldList,oneHot=True,periodGranularity=periodGranularity,userIDs=[usr.userID])
        
        if xTrain is not None:
            if np.shape(yTrain_onehot)[1] !=1:  # Results have to have both 0's and 1's in them
                trainModel(xTrain, yTrain_onehot, sess,training_iterations)
        saver.save(sess,"./3_Data/saves/model.ckpt")
print('Ok')


users=cc.getUsers(dbPath).sample(2)
u=users.userID.values
_,_,xTest, yTest_onehot = cc.getHiddenPeriodsData(dbPath,fieldList,oneHot=True,periodGranularity=periodGranularity,userIDs=u)
print ('{} users selected for testing. Total rows {}'.format(len(u), len(xTest)))

xTest2, yTest2_onehot, testDf2 = cc.getHiddenUsersData(dbPath,fieldList,oneHot= True,firstNPerc=0.5,periodGranularity=periodGranularity)


def getTestPredictions(X,Y):
    predictions=[]
    l=np.shape(X)[0]
    
    # Testing cycle
    print("Now testing {} rows".format(l))
    logging.info("Now testing {} rows".format(l))
    
    # Pad rows at the beginning so we can get a prediction for every entry
    padX=np.zeros([batch_size-1,X.shape[1]])
    padY=np.zeros([batch_size-1,Y.shape[1]])
    
    X = np.append(padX, X, axis=0)
    Y = np.append(padY, Y, axis=0)
    l=np.shape(X)[0]  # Update length
    
    # Loop over all rows in order of earliest to lates
    
    for pos in range(batch_size, l+1):
        
        if (pos % 20000) == 0: 
                #print("Now on pos {} of {} ({}%)".format(pos,l,round((pos/l)*100,2)))
                logging.info("Now on pos {} of {} ({}%)".format(pos,l,round((pos/l)*100,2)))
        
        # For each row, bring up the history of length bath size
        _x = X[pos-batch_size:pos].reshape((batch_size, n_steps, n_input))  # Rehsape into 3d, even though n_steps is 1            
        _y = Y[pos-batch_size:pos]                        
        
        # Predict!
        p= 1*sess.run(pred, feed_dict={x: _x, y: _y})
        p=p.reshape(-1,n_classes)
        
        if predictions == []:
            predictions = p
        else:
            predictions= np.append(predictions,p,axis=0)
             
    # Remove padding and return predictions
    predictions = np.argmax(predictions,1)
    
    return predictions



print ("Cell type= {}, learning_rate = {}, Iterations = {}, batch size = {}, Steps = {}, Hidden Layers = {}, Classes = {}".format(cellType,learning_rate,training_iterations,batch_size, n_steps ,n_hidden,n_classes))
print('Hidden Periods\n\n')
predictions = getTestPredictions(xTest,yTest_onehot)
print(np.shape(predictions),np.shape(yTest_onehot))
print(metrics.classification_report(yTest_onehot[:,1],predictions))  # Need to feed it yTest not yTest_OneHot here
print(metrics.confusion_matrix(yTest_onehot[:,1],predictions))

print('\nHidden Users')
predictions = getTestPredictions(xTest2,yTest2_onehot)
print(metrics.classification_report(yTest2_onehot[:,1],predictions))  # Need to feed it yTest not yTest_OneHot here
print(np.shape(xTest2),np.shape(yTest2_onehot))

