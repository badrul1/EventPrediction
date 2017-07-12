import pandas as pd
import json
import os
import csv
import sqlite3 as lite
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