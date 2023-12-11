"""
  FastAPI entrypoint for the slack-events-bot application

  Visit the /docs route for more information on the routes contained within.
"""
import asyncio
import datetime
import logging
import os
import re
import sys
import threading
from collections.abc import Awaitable, Callable
from typing import Union

import uvicorn
from fastapi import HTTPException, Request
from fastapi.responses import PlainTextResponse
from starlette.types import Message

import database
from auth import validate_slack_command_source
from bot import periodically_check_api, periodically_delete_old_messages
from config import API, SLACK_APP_HANDLER


async def identify_slack_team_domain(payload: bytes) -> Union[str, None]:
    """Extracts the value of 'team_domain=' from the request body sent by Slack."""
    decoded_payload = payload.decode("utf-8")

    match = re.search(r"team_domain=(.+?(?=&))", decoded_payload)

    if match is None:
        return logging.error("The team_domain could not be extracted from the payload.")

    return match.groups()[0]


async def check_api_being_requested(path: str, payload: bytes) -> bool:
    """Determines if a user is attempting to execute the /check_api command."""
    decoded_payload = payload.decode("utf-8")

    return path == "/slack/events" and "command=%2Fcheck_api" in decoded_payload


async def check_api_on_cooldown(team_domain: Union[str, None]) -> bool:
    """
    Checks to see if the /check_api command has been run in the last 15 minutes in the
    specified server (denoted by its team_domain).

    If an expiry time does not exist, or if the expiry time found is in the past,
    then the user is allowed to proceed with accessing the check_api method. In both
    of these instances a new expiry time is created for 15 minutes out.

    If either of those criteria aren't then the resource is on cooldown for the
    accessing entity and we will signal that to the system.
    """
    if team_domain is None:
        # Electing to just return true to let users see a throttle message if this occurs.
        logging.warning("team_domain was None in check_api_on_cooldown")
        return True

    expiry = await database.get_cooldown_expiry_time(team_domain, "check_api")

    if expiry is None:
        return False

    if datetime.datetime.now(datetime.timezone.utc) > datetime.datetime.fromisoformat(
        expiry
    ):
        return False

    return True


async def update_check_api_cooldown(team_domain: str | None) -> None:
    """
    Creates a new cooldown record for an accessor to the check_api method
    after they've been permitted access.
    """
    if team_domain is None:
        return

    await database.create_cooldown(team_domain, "check_api", 15)


async def set_body(req: Request, body: bytes):
    """
    Overrides the Request class's __receive method as a workaround to an issue
    where accessing a request body in middleware causes it to become blocking.

    See https://github.com/tiangolo/fastapi/discussions/8187 for the discussion
    and this post (https://github.com/tiangolo/fastapi/discussions/8187#discussioncomment-5148049)
    for where this code originates. Thanks, https://github.com/liukelin!
    """

    async def receive() -> Message:
        return {"type": "http.request", "body": body}

    # pylint: disable=protected-access
    req._receive = receive


async def get_body(req: Request) -> bytes:
    """
    Leans into the overriden Request.__receive method seen above in set_body
    to workaround 'await req.body()' causing the application to hang.
    """
    body = await req.body()
    await set_body(req, body)
    return body


@API.middleware("http")
async def rate_limit_check_api(
    req: Request, call_next: Callable[[Request], Awaitable[None]]
):
    """Looks to see if /check_api has been run recently, and returns an error if so."""
    req_body = await get_body(req)

    if await check_api_being_requested(req.scope["path"], req_body):
        team_domain = await identify_slack_team_domain(req_body)
        if await check_api_on_cooldown(team_domain):
            return PlainTextResponse(
                (
                    "This command has been run recently and is on a cooldown period. "
                    "Please try again in a little while!"
                )
            )

        await update_check_api_cooldown(team_domain)

    return await call_next(req)


@API.post("/slack/events")
@validate_slack_command_source
async def slack_endpoint(req: Request):
    """The front door for all Slack requests"""

    return await SLACK_APP_HANDLER.handle(req)


@API.get("/healthz", tags=["Utility"])
async def health_check(req: Request):
    """
    Route used to test if the server is still online.

    Returns a 500 response if one or more threads are found to be dead. Enough of these
    in a row will cause the docker container to be placed into an unhealthy state and soon
    restarted.

    Returns a 200 response otherwise.
    """
    del req

    for thd in threading.enumerate():
        if not thd.is_alive():
            raise HTTPException(
                status_code=500,
                detail=f"The {thd.name} thread has died. This container will soon restart.",
            )

    return {"detail": "Everything is lookin' good!"}


if __name__ == "__main__":
    # create database tables if they don't exist
    database.create_tables()
    print("Created database tables!")

    # once a day, purge rows older than 90 days
    thread = threading.Thread(
        target=asyncio.run,
        args=(periodically_delete_old_messages(),),
        name="periodic_message_deletion",
    )
    try:
        thread.daemon = True
        thread.start()
    except (KeyboardInterrupt, SystemExit):
        thread.join(timeout=60)
        sys.exit()

    # start checking api every hour in background thread
    thread = threading.Thread(
        target=asyncio.run, args=(periodically_check_api(),), name="periodic_api_check"
    )
    try:
        thread.daemon = True
        thread.start()
    except (KeyboardInterrupt, SystemExit):
        thread.join(timeout=60)
        sys.exit()

    # Default port is 3000
    uvicorn.run(
        API, port=int(int(os.environ.get("PORT", "3000").strip("\"'"))), host="0.0.0.0"
    )
