from datetime import datetime, timedelta, tzinfo


class UTC(tzinfo):
    """UTC"""

    def utcoffset(self, dt):
        return timedelta(0)

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return timedelta(0)


class FeedHelper():
    def __init__(self, start_date, minutes_to_advance):
        TZ_UTC = UTC()
        self.minutes_to_advance = minutes_to_advance
        self.start_date = start_date.replace(tzinfo=TZ_UTC)
        self.end_date = self.start_date + \
            timedelta(minutes=self.minutes_to_advance)
        self.now = datetime.utcnow().replace(tzinfo=TZ_UTC)
        if self.end_date > self.now:
            self.end_date = self.now
        self.start = False
        self.done = False

    def advance(self):
        """
        Returns True if keep going,
                False if we already hit the end time and cannot advance
        :return: True or False
        """
        if not self.start:
            self.start = True
            return True

        if self.done:
            return False

        self.start_date = self.end_date
        self.end_date += timedelta(minutes=self.minutes_to_advance)
        if self.end_date > self.now:
            self.end_date = self.now
            self.done = True

        return True
