import duckdb
import json
import os
import sys
import time

def get_connection():
    con = duckdb.connect(database=":memory:")
    con.execute("PRAGMA threads=4;")
    try:
        con.execute("INSTALL fts; LOAD fts;")
    except Exception as e:
        print(f"Warning loading FTS: {e}")
    return con

print("Initialized catalog generator module.")
