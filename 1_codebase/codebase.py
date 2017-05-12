import pandas as pd
import json
import os
import csv
import sqlite3 as lite


def loadSettings():

    with open('2_settings/settings.json') as json_data:
        s = json.load(json_data)
        return s

def create_connection(db_file):
    """ create a database connection to a SQLite database """
    try:
        conn = sqlite3.connect(db_file)
        print(sqlite3.version)
    except Error as e:
        print(e)
    finally:
        conn.close()



