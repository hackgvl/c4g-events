"""
Location for configuration settings and app-wide constants.
"""

import os

from fastapi import FastAPI
from slack_bolt.adapter.fastapi.async_handler import AsyncSlackRequestHandler
from slack_bolt.async_app import AsyncApp
from slack_bolt.oauth.async_oauth_settings import AsyncOAuthSettings
from slack_sdk.oauth import AuthorizeUrlGenerator
from slack_sdk.oauth.state_store import FileOAuthStateStore

API = FastAPI()

SCOPES = [
    "chat:write",
    "chat:write.public",
    "commands",
    "incoming-webhook",
    "users:read",
]

STATE_STORE = FileOAuthStateStore(expiration_seconds=300, base_dir="./data")

SLACK_APP = AsyncApp(
    token=os.environ.get("BOT_TOKEN"),
    signing_secret=os.environ.get("SIGNING_SECRET"),
    oauth_settings=AsyncOAuthSettings(
        client_id=os.environ.get("CLIENT_ID"),
        client_secret=os.environ.get("CLIENT_SECRET"),
        scopes=SCOPES,
        user_scopes=[],
        redirect_uri=None,
        install_path="/slack/install",
        redirect_uri_path="/slack/auth",
        state_store=STATE_STORE,
    ),
)

SLACK_APP_HANDLER = AsyncSlackRequestHandler(SLACK_APP)

AUTHORIZE_URL_GENERATOR = AuthorizeUrlGenerator(
    client_id=os.environ.get("CLIENT_ID"),
    scopes=SCOPES,
    user_scopes=[],
)
