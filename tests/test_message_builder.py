"""
Tests for the message_builder.py utility file.
"""

import datetime

import pytest
import pytz

from message_builder import (
    MAX_MESSAGE_CHARACTER_LENGTH,
    build_event_blocks,
    build_header,
    build_single_event_block,
    chunk_messages,
    total_messages_needed,
)

week_start = datetime.datetime.strptime("10/22/2023", "%m/%d/%Y").replace(
    tzinfo=pytz.utc
)
week_end = week_start + datetime.timedelta(days=7)


@pytest.mark.asyncio
async def test_build_event_blocks_date_range(event_api_response_data):
    """
    Tests that the correct number of event blocks are created given the time constraints.
    """
    event_blocks = await build_event_blocks(
        event_api_response_data, week_start, week_end
    )

    # There are nine events in range that should have blocks
    assert len(event_blocks) == 9


@pytest.mark.asyncio
async def test_build_single_event_block_date_range(single_event_data):
    """
    Tests that events out of range do not have blocks created for them.
    """
    event_data = single_event_data
    event_data["time"] = "2024-10-24T22:30:00Z"

    block = await build_single_event_block(single_event_data, week_start, week_end)

    assert block is None


@pytest.mark.asyncio
async def test_build_single_event_block_invalid_status(single_event_data):
    """
    Tests that the events with invalid statuses do not have blocks created for them.
    """
    event_data = single_event_data
    event_data["status"] = "way off base"

    block = await build_single_event_block(event_data, week_start, week_end)

    assert block is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "total,expected_last_string",
    [
        (1, "HackGreenville Events for the week of October 22 - 1 of 1"),
        (15, "HackGreenville Events for the week of October 22 - 15 of 15"),
    ],
)
async def test_build_header(total, expected_last_string):
    """
    Ensures that the build_header function can build any number of headers.
    """
    result = [await build_header(week_start, idx + 1, total) for idx in range(total)]

    assert len(result) == total
    assert expected_last_string in result[-1]["text"]


@pytest.mark.asyncio
async def test_chunk_messages(event_api_response_data):
    """
    Makes sure that the message chunker does not allow any message to exceed the maximum
    character limit that has been set.
    """
    event_blocks = await build_event_blocks(
        event_api_response_data, week_start, week_end
    )

    result = await chunk_messages(event_blocks, week_start)

    assert len(result) == 2
    assert all(
        len(text) < MAX_MESSAGE_CHARACTER_LENGTH
        for text in [msg["text"] for msg in result]
    )


@pytest.mark.asyncio
async def test_total_messages_needed_with_borderline_edge_case():
    """
    Ensures total message count is rounded upwards appropriately
    whenever the event data character count is just below n * MAX_MESSAGE_CHARACTER_LENGTH
    and the addition of post headers causes it message count to then spillover.

    The test data used is that reported in https://github.com/hackgvl/slack-events-bot/issues/52
    """
    # Abbreviated problem case from actual data that originally caused the bug to manifest.
    borderline_test_case = [
        {
            "text_length": 463,
        },
        {
            "text_length": 311,
        },
        {
            "text_length": 397,
        },
        {
            "text_length": 507,
        },
        {
            "text_length": 456,
        },
        {
            "text_length": 463,
        },
        {
            "text_length": 352,
        },
    ]

    assert await total_messages_needed(borderline_test_case) == 2


@pytest.mark.asyncio
async def test_total_messages_needed_always_at_least_1():
    """
    Ensures that the total message needed count is always at least one.

    This is because we create a post for weeks that have zero events in case
    new ones are added later, and we don't want the posts to have "- 1 of 0" in their
    headers.
    """
    assert await total_messages_needed([]) == 1
