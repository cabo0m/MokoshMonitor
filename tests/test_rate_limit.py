import unittest
from unittest.mock import Mock
from datetime import datetime, timedelta, timezone

import monitor


class RateLimitTests(unittest.TestCase):
    def response(self, value=None):
        r = Mock()
        r.status_code = 429
        r.headers = {} if value is None else {"Retry-After": value}
        return r

    def test_retry_after_seconds(self):
        self.assertEqual(monitor.retry_delay(self.response("120")), 120)

    def test_retry_after_default(self):
        self.assertEqual(monitor.retry_delay(self.response()), 900)

    def test_retry_after_caps_and_floor(self):
        self.assertEqual(monitor.retry_delay(self.response("1")), 60)
        self.assertEqual(monitor.retry_delay(self.response("999999")), 86400)

    def test_http_date(self):
        from email.utils import format_datetime
        future = datetime.now(timezone.utc) + timedelta(seconds=240)
        delay = monitor.retry_delay(self.response(format_datetime(future)))
        self.assertGreaterEqual(delay, 238)
        self.assertLessEqual(delay, 240)

    def test_api_429_does_not_trigger_html_fallback(self):
        session = Mock()
        session.headers = {}
        session.get.return_value = self.response("120")
        with self.assertRaises(monitor.RateLimited):
            monitor.fetch_catalog(monitor.DEFAULTS, session=session)
        self.assertEqual(session.get.call_count, 1)


if __name__ == "__main__":
    unittest.main()
