import sqlite3
from flask import Flask, request

app = Flask(__name__)


def find_user(username: str):
    connection = sqlite3.connect(":memory:")
    cursor = connection.cursor()
    cursor.execute(f"SELECT * FROM users WHERE username = '{username}'")
    return cursor.fetchall()


@app.route("/login")
def login():
    username = request.args.get("username", "guest")
    return {"rows": find_user(username)}
