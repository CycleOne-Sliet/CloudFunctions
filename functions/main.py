# Welcome to Cloud Functions for Firebase for Python!
# To get started, simply uncomment the below code or create your own.
# Deploy with `firebase deploy`

from firebase_functions import https_fn, options
from firebase_admin import initialize_app, firestore
import google.cloud.firestore
from Crypto.Cipher import AES
import binascii
import os
import time
from typing import Any
import base64

app = initialize_app()
@https_fn.on_call()
def get_token(req: https_fn.CallableRequest) -> Any:
    client: google.cloud.firestore.Client = firestore.client()
    seecret = os.getenv("SEECRET")
    key = b"aaaaaaaabbbbbbbb"
    if seecret is not None:
        key = base64.b64decode(seecret)
        if len(key) > 16:
            key = key[:16]
    IV = os.urandom(16)
    encryptor = AES.new(key, AES.MODE_CBC, IV=IV)
    uid = req.auth.uid
    cycle_id = req.data["cycle_id"]
    if uid is not None:
        if cycle_id is not None:
            print(f"{req.auth.uid}:{req.data['cycle_id']}:{time.time_ns()};", 'utf-8')
            token = f"{req.auth.uid}:{req.data['cycle_id']}:{time.time_ns()};"
            tokenLen = len(token)
            token += '\0' * (16 - len(token) % 16)
            encrypted = encryptor.encrypt(bytes(token, 'utf-8'))
            return {
                "token": str(binascii.hexlify(
                             IV +
                         encrypted
                         )),
            }
        else:
            raise https_fn.HttpsError(https_fn.FunctionsErrorCode.MISSING_FIELD, "Missing field cycle_id")
    else:
        raise https_fn.HttpsError(https_fn.FunctionsErrorCode.MISSING_FIELD, "Missing field uid")

