"""The hackgreenville labs slack bot"""

import asyncio
import datetime
import os
import sqlite3
import sys
import threading
import traceback
import aiohttp
import pytz
import uvicorn

from asyncache import cached
from cachetools import TTLCache
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.fastapi.async_handler import AsyncSlackRequestHandler
import database

from event import Event

# 50kb - Current API responses are around ~11.7kb as of 09/30/2023
MAX_BYTES = 50000

# configure app
APP = AsyncApp(
    token=os.environ.get("BOT_TOKEN"), signing_secret=os.environ.get("SIGNING_SECRET")
)
APP_HANDLER = AsyncSlackRequestHandler(APP)

DBPATH = os.path.abspath(os.environ.get("DB_PATH", "./slack-events-bot.db"))
CONN = sqlite3.connect(DBPATH)


async def periodically_check_api():
    """Periodically check the api every hour

    This function runs in a thread, meaning that it needs to create it's own
    database connection. This is OK however, since it only runs once an hour
    """
    print("Checking api every hour")
    while True:
        try:
            with sqlite3.connect(DBPATH) as conn:
                await check_api(conn)
        except Exception:  # pylint: disable=broad-except
            print(traceback.format_exc())
            os._exit(1)
        await asyncio.sleep(60 * 60)  # 60 minutes x 60 seconds


@APP.command("/add_channel")
async def add_channel(ack, say, logger, command):
    """Handle adding a slack channel to the bot"""
    del say
    logger.info(f"{command['command']} from {command['channel_id']}")
    if command["channel_id"] is not None:
        try:
            await database.add_channel(CONN, command["channel_id"])
            await ack("Added channel to slack events bot 👍")
        except sqlite3.IntegrityError:
            await ack("slack events bot has already been activated for this channel")


@APP.command("/remove_channel")
async def remove_channel(ack, say, logger, command):
    """Handle removing a slack channel from the bot"""
    del say
    logger.info(f"{command['command']} from {command['channel_id']}")
    if command["channel_id"] is not None:
        try:
            await database.remove_channel(CONN, command["channel_id"])
            await ack("Removed channel from slack events bot 👍")
        except sqlite3.IntegrityError:
            await ack("slack events bot is not activated for this channel")


@APP.command("/check_api")
async def trigger_check_api(ack, say, logger, command):
    """Handle manually rechecking the api for updates"""
    del say
    logger.info(f"{command['command']} from {command['channel_id']}")
    if command["channel_id"] is not None:
        await ack("Checking api for events 👍")
        await check_api(CONN)


@cached(cache=TTLCache(maxsize=MAX_BYTES, ttl=15 * 60))
async def check_api(conn):
    """Check the api for updates and update any existing messages"""
    async with aiohttp.ClientSession() as session:
        async with session.get("https://events.openupstate.org/api/gtc") as resp:
            # get timezone aware today
            today = datetime.date.today()
            today = datetime.datetime(
                today.year, today.month, today.day, tzinfo=pytz.utc
            )

            # keep current week's post up to date
            await parse_events_for_week(conn, today, resp)

            # potentially post next week 5 days early
            probe_date = today + datetime.timedelta(days=5)
            await parse_events_for_week(conn, probe_date, resp)


async def parse_events_for_week(conn, probe_date, resp):
    """Parses events for the week containing the probe date"""
    week_start = probe_date - datetime.timedelta(days=(probe_date.weekday() % 7) + 1)
    week_end = week_start + datetime.timedelta(days=7)

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": (
                    "HackGreenville Events for the week of "
                    f"{week_start.strftime('%B %-d')}"
                ),
            },
        },
        {"type": "divider"},
    ]

    text = (
        f"HackGreenville Events for the week of {week_start.strftime('%B %-d')}"
        "\n\n===\n\n"
    )

    for event_data in await resp.json():
        event = Event.from_event_json(event_data)

        # ignore event if it's not in the current week
        if event.time < week_start or event.time > week_end:
            continue

        # ignore event if it has a non-supported status
        if event.status not in ["cancelled", "upcoming", "past"]:
            print(f"Couldn't parse event {event.uuid} " f"with status: {event.status}")
            continue

        blocks += event.generate_blocks() + [{"type": "divider"}]
        text += f"{event.generate_text()}\n\n"

    await post_or_update_messages(conn, week_start, blocks, text)


async def post_or_update_messages(conn, week, blocks, text):
    """Posts or updates a message in a slack channel for a week"""
    channels = await database.get_slack_channel_ids(conn)
    messages = await database.get_messages(conn, week)

    # used to lookup the message id and message for a particular
    # channel
    message_details = {
        message["slack_channel_id"]: {
            "timestamp": message["message_timestamp"],
            "message": message["message"],
        }
        for message in messages
    }

    # used to quickly lookup if a message has been posted for a
    # particular channel
    posted_channels_set = set(message["slack_channel_id"] for message in messages)

    for slack_channel_id in channels:
        if (
            slack_channel_id in posted_channels_set
            and text == message_details[slack_channel_id]["message"]
        ):
            print(
                f"Week of {week.strftime('%B %-d')} in {slack_channel_id} "
                "hasn't changed, not updating"
            )

        elif slack_channel_id in posted_channels_set:
            print(f"updating week {week.strftime('%B %-d')} " f"in {slack_channel_id}")

            timestamp = message_details[slack_channel_id]["timestamp"]
            slack_response = await APP.client.chat_update(
                ts=timestamp, channel=slack_channel_id, blocks=blocks, text=text
            )

            await database.update_message(conn, week, text, timestamp, slack_channel_id)

        else:
            print(f"posting week {week.strftime('%B %-d')} " f"in {slack_channel_id}")

            slack_response = await APP.client.chat_postMessage(
                channel=slack_channel_id,
                blocks=blocks,
                text=text,
                unfurl_links=False,
                unfurl_media=False,
            )

            await database.create_message(
                conn, week, text, slack_response["ts"], slack_channel_id
            )


API = FastAPI()


@API.post("/slack/events")
async def endpoint(req: Request):
    """The front door for all Slack requests"""
    return await APP_HANDLER.handle(req)


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
    database.create_tables(CONN)
    print("Created database tables!")

    # start checking api every hour in background thread
    thread = threading.Thread(
        target=asyncio.run, args=(periodically_check_api(),), name="periodic_api_check"
    )
    try:
        thread.daemon = True
        thread.start()
    except (KeyboardInterrupt, SystemExit):
        thread.join()
        sys.exit()

    uvicorn.run(API, port=int(int(os.environ.get("PORT").strip("\"'"))), host="0.0.0.0")

CONN.close()
