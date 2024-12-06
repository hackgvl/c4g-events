"""Contains the event class, which holds information for an event"""

import os
import urllib

import pytz
from dateutil import parser


def parse_location(event_json):
    """Parse location string from event json"""
    if event_json["venue"] is None:
        return None

    if None not in (
        event_json["venue"]["name"],
        event_json["venue"]["address"],
        event_json["venue"]["city"],
        event_json["venue"]["state"],
        event_json["venue"]["zip"],
    ):
        return (
            f"{event_json['venue']['name']} at "
            f"{event_json['venue']['address']} {event_json['venue']['city']}, "
            f"{event_json['venue']['state']} {event_json['venue']['zip']}"
        )

    if (
        event_json["venue"]["lat"] is not None
        and event_json["venue"]["lon"] is not None
    ):
        return f"lat/long: {event_json['venue']['lat']}, {event_json['venue']['lon']}"

    return f"{event_json['venue']['name']}"


def truncate_string(string, length=250):
    """Truncate string and add ellipses if it's too long"""
    return string[:length] + (string[length:] and "...")


def get_location_url(location):
    """Return google maps link for location or plaintext"""
    if location is None:
        return "No location"

    return (
        "<https://www.google.com/maps/search/?api=1&query="
        f"{urllib.parse.quote(location)}|{location}>"
    )


def print_status(status):
    """Prints status with emojis :D"""
    if status == "upcoming":
        return "Upcoming ✅"

    if status == "past":
        return "Past ✔"

    if status == "cancelled":
        return "Cancelled ❌"

    return status.title()


def print_datetime(time):
    """Print datetime in local timezone as string"""
    return time.astimezone(pytz.timezone(os.environ.get("TZ"))).strftime(
        "%B %-d, %Y %I:%M %p %Z"
    )


class Event:
    """Event records all the data from an event, and has methods to generate the
    message from an event
    """

    # pylint: disable=too-many-instance-attributes
    # Events have lots of data that we need to save together
    def __init__(
        self, *, title, group_name, description, location, time, url, status, uuid
    ):
        # pylint: disable=too-many-arguments
        self.title = title
        self.group_name = group_name
        self.description = description
        self.location = location
        self.time = time
        self.url = url
        self.status = status
        self.uuid = uuid

    # creates a struct of event information used to compose different formats of the event message
    @classmethod
    def from_event_json(cls, event_json):
        """Create an event class object from the raw event json returned by the OpenApi"""
        return cls(
            title=event_json["event_name"],
            group_name=event_json["group_name"],
            description=event_json["description"],
            location=parse_location(event_json),
            time=parser.isoparse(event_json["time"]),
            url=event_json["url"],
            status=event_json["status"],
            uuid=event_json["uuid"],
        )

    def generate_blocks(self):
        """Compose part of a slack message using the blocks layout"""
        return [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": truncate_string(self.title)},
            },
            {
                "type": "section",
                "text": {
                    "type": "plain_text",
                    "text": truncate_string(self.description),
                },
                "fields": [
                    {"type": "mrkdwn", "text": f"*{truncate_string(self.group_name)}*"},
                    {"type": "mrkdwn", "text": f"<{self.url}|*Link* :link:>"},
                    {"type": "mrkdwn", "text": "*Status*"},
                    {"type": "mrkdwn", "text": print_status(self.status)},
                    {"type": "mrkdwn", "text": "*Location*"},
                    {"type": "mrkdwn", "text": get_location_url(self.location)},
                    {"type": "mrkdwn", "text": "*Time*"},
                    {"type": "plain_text", "text": print_datetime(self.time)},
                ],
            },
        ]

    def generate_text(self):
        """Compose a text string of event information for backup"""
        return (
            f"{truncate_string(self.title)}\n"
            f"Description: {truncate_string(self.description)}\n"
            f"Link: {self.url}\n"
            f"Status: {print_status(self.status)}\n"
            f"Location: {self.location}\n"
            f"Time: {print_datetime(self.time)}"
        )
