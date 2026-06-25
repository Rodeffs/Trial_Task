import sqlite3
from fastapi import FastAPI


"""
Этот файл и будет тем самым бэкэндом для работы с FastAPI
"""


con = sqlite3.connect("aybolit.db")
cur = con.cursor()

app = FastAPI()



