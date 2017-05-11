import dask.dataframe as dd
import pandas as pd
import json
import csv
import itertools

def checkRow(path,N):
    with open(path, 'r') as f:
        print("This is the line.")
        print(next(itertools.islice(csv.reader(f), N, None)))

def loadSettings():
    with open('../settings/settings.json') as json_data:
        s = json.load(json_data)
        return s

