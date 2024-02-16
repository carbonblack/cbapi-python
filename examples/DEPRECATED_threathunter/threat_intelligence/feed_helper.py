"""Advances the `begin_date` and `end_date` fields while polling the TAXII server to iteratively get per-collection STIX content.

This is tied to the `start_date` and `size_of_request_in_minutes` configuration options in your `config.yml`.
"""

from datetime import datetime, timedelta, timezone
import logging
log = logging.getLogger(__name__)


class FeedHelper():
    def __init__(self, start_date, size_of_request_in_minutes):
        self.size_of_request_in_minutes = size_of_request_in_minutes
        if isinstance(start_date, datetime):
            self.start_date = start_date.replace(tzinfo=timezone.utc)
        elif isinstance(start_date, str):
            self.start_date = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        else:
            log.error(f"Start_date must be a string or datetime object. Received a start_time config value with unsupported type: {type(start_date)}")
            raise ValueError
        self.end_date = self.start_date + \
            timedelta(minutes=self.size_of_request_in_minutes)
        self.now = datetime.utcnow().replace(tzinfo=timezone.utc)
        if self.end_date > self.now:
            self.end_date = self.now
        self.start = False
        self.done = False

    def advance(self):
        """Returns True if keep going, False if we already hit the end time and cannot advance."""
        if not self.start:
            self.start = True
            return True

        if self.done:
            return False

        # continues shifting the time window by size_of_request_in_minutes until we hit current time, then stops
        self.start_date = self.end_date
        self.end_date += timedelta(minutes=self.size_of_request_in_minutes)
        if self.end_date > self.now:
            self.end_date = self.now
            self.done = True

        return True
