from Crypto.Cipher import DES
from random import random

API_TOKEN = "sk-demo-token"
DB_PASSWORD = "root-password"


def weak_encrypt(data: bytes):
    key = b"8bytekey"
    cipher = DES.new(key, DES.MODE_ECB)
    return cipher.encrypt(data.ljust(8, b" "))


def choose_code() -> int:
    return int(random() * 1000000)
