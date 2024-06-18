# Welcome to Cloud Functions for Firebase for Python!
# To get started, simply uncomment the below code or create your own.
# Deploy with `firebase deploy`

from firebase_functions import https_fn
from firebase_admin import initialize_app, firestore
from firebase_functions import identity_fn
import google.cloud.firestore

# initialize_app()
#
#
# @https_fn.on_request()
# def on_request_example(req: https_fn.Request) -> https_fn.Response:
#     return https_fn.Response("Hello world!")


app = initialize_app()

@identity_fn.before_user_created()
def on_user_creation(event: identity_fn.AuthBlockingEvent) -> identity_fn.BeforeCreateResponse | None:
    firestore_client: google.cloud.firestore.Client = firestore.client()
    firestore_client.collection("users").document(event.data.uid).set(
        {"HasCycle": False, "CycleOccupied": None})
    return

