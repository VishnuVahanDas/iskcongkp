import base64, hashlib, os
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

WORKING_KEY = os.environ["HDFC_WORKING_KEY"]

def _key() -> bytes:
    return hashlib.md5(WORKING_KEY.encode()).digest()

def encrypt(plain: str) -> str:
    cipher = AES.new(_key(), AES.MODE_CBC, iv=b"\0"*16)
    enc = cipher.encrypt(pad(plain.encode(), AES.block_size))
    return base64.b64encode(enc).decode()

def decrypt(cipher_text: str) -> str:
    cipher = AES.new(_key(), AES.MODE_CBC, iv=b"\0"*16)
    data = base64.b64decode(cipher_text)
    return unpad(cipher.decrypt(data), AES.block_size).decode()