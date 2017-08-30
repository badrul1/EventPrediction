#!/usr/bin/env python
"""
Thierry Bertin-Mahieux (2011) Columbia University
tb2332@columbia.edu


This code shows how to use the SQLite database made with tags
from the Last.fm dataset.
Code developed using python 2.6 on an Ubuntu machine, utf-8 by default.

This is part of the Million Song Dataset project from
LabROSA (Columbia University) and The Echo Nest.


Copyright 2011, Thierry Bertin-Mahieux <tb2332@columbia.edu>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os
import sys
import sqlite3
import pandas as pd


def sanitize(tag):
    """
    sanitize a tag so it can be included or queried in the db
    """
    tag = tag.replace("'","''")
    return tag


def getTagsForTrack(dbPath,tid):

    # sanity check
    if not os.path.isfile(dbPath):
        print ('ERROR: db file %s does not exist?' % dbPath)
        exit

    # open connection
    conn = sqlite3.connect(dbPath)

    sql = "SELECT tag FROM tags"
    res = conn.execute(sql)
    data = res.fetchall()

    return data

def getTracksForTag(dbPath, tag):
    # sanity check
    if not os.path.isfile(dbPath):
        print ('ERROR: db file %s does not exist?' % dbPath)
        exit

    # open connection
    conn = sqlite3.connect(dbPath)

    tag = sanitize(tag)
    sql = "SELECT tids.tid FROM tid_tag, tids, tags WHERE tids.ROWID=tid_tag.tid AND tid_tag.tag=tags.ROWID AND tags.tag='%s'" % tag
    res = conn.execute(sql)
    data = res.fetchall()
    conn.close()

    return [d[0] for d in data]


def getSimilarity_Dest(dbPath,tid):
    # Get all songs which consider tid as similar to itself
    sql = "SELECT target FROM similars_dest WHERE tid='%s'" % tid
    res = conn.execute(sql)
    data = res.fetchone()[0]
    conn.close

    data_unpacked = []
    for idx, d in enumerate(data.split(',')):
        if idx % 2 == 0:
            # If this is the string portion
            pair = [d]
        else:
            # If this is the score
            pair.append(float(d))
            data_unpacked.append(pair)
    # sort
    data_unpacked = sorted(data_unpacked, key=lambda x: x[1], reverse=True)
    return data_unpacked

def getSimilariity (dbPath,tid, threshold):
    # Get all similar songs (with value) to tid and where similarity score is above threshold

    # sanity check
    if not os.path.isfile(dbPath):
        print ('ERROR: db file %s does not exist?' % dbPath)
        exit

    # open connection
    conn = sqlite3.connect(dbPath)

    sql = "SELECT target FROM similars_src WHERE tid='%s'" % tid
    res = conn.execute(sql)
    data = res.fetchone()[0]   # This line must be to deal with potential duplicates I imagine
    conn.close

    aboveThreshold = False
    data_unpacked = []
    for idx, d in enumerate(data.split(',')):
        if idx % 2 == 0:
            # If this is the string portion
            pair = [d]
        else:
            # If this is the score
            if (float(d) >= threshold):
                pair.append(float(d))
                data_unpacked.append(pair)

    # sort
    data_unpacked = sorted(data_unpacked, key=lambda x: x[1], reverse=True)
    return data_unpacked

def getSimilariityAll (dbPath, threshold):
    # Get all similar songs (with value) to tid and where similarity score is above threshold

    # sanity check
    if not os.path.isfile(dbPath):
        print ('ERROR: db file %s does not exist?' % dbPath)
        exit

    # open connection
    conn = sqlite3.connect(dbPath)

    sql = "SELECT tid, target FROM similars_src"
    res = conn.execute(sql)
    data = res.fetchall()
    conn.close

    r=[]
    for row in data:

        s = [row[0]] # this is the main tid
        flag = False
        for idx, d in enumerate(row[1].split(',')):

            if idx % 2 == 0:
            # If this is the string portion
                u = d
            else:
                # If this is the score
                if (float(d) >= threshold):
                    s.extend([u])
                    flag=True

        if flag:
            r.extend([s])


    return r


def convertTrackIDTo(dbPath, tids, convertTo):
    con = sqlite3.connect(dbPath)
    sqlStr = "SELECT track_id, {0} from songs".format(convertTo)

    # Load into Pandas
    res = pd.read_sql_query(sqlStr, con)
    con.close()
    res = res.set_index('track_id')

    s = pd.Series(tids).map(res[convertTo]).tolist()
    return s
