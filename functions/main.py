# Welcome to Cloud Functions for Firebase for Python!
# To get started, simply uncomment the below code or create your own.
# Deploy with `firebase deploy`

from firebase_functions import https_fn
from firebase_admin import initialize_app, firestore
import google.cloud.firestore
from Crypto.Cipher import AES
import binascii
import os
import time
from typing import Any
import json
import base64

app = initialize_app()


@https_fn.on_call()
async def get_token(req: https_fn.CallableRequest) -> Any:
    firestore_client: google.cloud.firestore.Client = firestore.client()
    seecret = os.getenv("SEECRET")
    key = b"aaaaaaaabbbbbbbb"
    if seecret is not None:
        key = base64.b64decode(seecret)
        if len(key) > 16:
            key = key[:16]

    IV = os.urandom(16)
    token = req.data["token"]
    if token is None:
        raise https_fn.HttpsError(
            https_fn.FunctionsErrorCode.MISSING_FIELD, "Missing field token")

    encryptor = AES.new(key, AES.MODE_CBC, IV=IV)
    decryptor = AES.new(key, AES.MODE_CBC, IV=token[0:16])
    json_string = decryptor.decrypt(token[16:])
    parsedToken = json.loads(json_string)
    isUnlocked = parsedToken["isUnlocked"]
    cycleId = parsedToken["cycleId"]
    standTime = parsedToken["time"]
    mac = parsedToken["mac"]
    if isUnlocked is None or cycleId is None or standTime is None or mac is None:
        raise https_fn.HttpsError(
            https_fn.FunctionsErrorCode.MISSING_FIELD, "Invalid Token")

    uid = req.auth.uid
    if uid is None:
        raise https_fn.HttpsError(
            https_fn.FunctionsErrorCode.MISSING_FIELD, "Missing field uid")

    current_time = time.time_ns()
    cycleRef = firestore_client.collection("cycles").document(cycleId)
    standRef = firestore_client.collection("stands").document(mac)
    userRef = firestore_client.collection("users").document(uid)
    firestore_client.collection("unlockRequests").add(
        document_id=time, document_data={
            "cycleId": cycleRef,
            "madeAtTime": current_time,
            "tookFrom": standRef,
            "madeBy": userRef})
    firestore_client.collection("users").document(uid).update(
        {"hasCycle": True, "cycleOccupied": cycleRef},
    )
    stand = firestore_client.collection("stands").document(mac)
    stand.cycles.remove(cycleId)
    stand.update({"cycles": stand.cycles})
    token = f"{req.auth.uid}:{req.data['cycle_id']}:{current_time};"
    token += '\0' * (16 - len(token) % 16)
    encrypted = encryptor.encrypt(bytes(token, 'utf-8'))

    return {
        "token": str(binascii.hexlify(
            IV +
            encrypted
        )),
    }


async def update_data(req: https_fn.CallableRequest) -> Any:
    firestore_client: google.cloud.firestore.Client = firestore.client()
    seecret = os.getenv("SEECRET")
    key = b"aaaaaaaabbbbbbbb"
    if seecret is not None:
        key = base64.b64decode(seecret)
        if len(key) > 16:
            key = key[:16]
    token = req.data["token"]
    if token is None:
        raise https_fn.HttpsError(
            https_fn.FunctionsErrorCode.MISSING_FIELD, "Missing field token")
    uid = req.auth.uid
    if uid is None:
        raise https_fn.HttpsError(
            https_fn.FunctionsErrorCode.MISSING_FIELD, "Missing field uid")

    IV = token[0:16]
    decryptor = AES.new(key, AES.MODE_CBC, IV=IV)
    json_string = decryptor.decrypt(token[16:])
    parsedToken = json.loads(json_string)
    isUnlocked = parsedToken["isUnlocked"]
    cycleId = parsedToken["cycleId"]
    standTime = parsedToken["time"]
    mac = parsedToken["mac"]
    if isUnlocked is None or standTime is None or mac is None:
        raise https_fn.HttpsError(
            https_fn.FunctionsErrorCode.MISSING_FIELD, "Invalid Token")
    if not isUnlocked:
        cycleRef = firestore_client.collection("cycles").document(cycleId)
        docs = (firestore_client.collection("unlockRequests").where(
            filter=firestore.StructuredQuery.FieldFilter("cycleId", "==", cycleRef)).stream())
        async for doc in docs:
            standRef = firestore_client.collection("stands").document(mac)
            d = doc.to_dict()
            d["returnedAt"] = time.time_ns()
            d["returnedTo"] = standRef
            firestore_client.collection(
                "unlockRequests").document(docs.id).update(d)
