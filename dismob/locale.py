# Copyright (c) 2025 Benoît Pelletier
# SPDX-License-Identifier: MPL-2.0
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os
import babel.dates
import dateutil.parser
import pytz
from datetime import datetime

def now() -> datetime:
    return datetime.now(tz=babel.dates.UTC)

def parse_date(date: str) -> datetime | None:
    """
    Parse a date string into a datetime object.
    Handles both ISO format and other common formats.
    Returns None if parsing fails.
    """
    try:
        # Always use dateutil.parser for robust parsing (handles ISO, with/without tz)
        return dateutil.parser.isoparse(date)
    except Exception:
        try:
            return dateutil.parser.parse(date)
        except Exception:
            return None

def format_date(date: str | datetime) -> str | None:
    """
    Format a date string into a locale-specific format.
    """
    if isinstance(date, str):
        dt = parse_date(date)
    else:
        dt = date

    tz = os.getenv("TZ")
    locale_str = os.getenv("LOCALE")
    return babel.dates.format_datetime(dt, locale=locale_str, tzinfo=pytz.timezone(tz))
