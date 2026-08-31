"""
Test runner that clears the cache before every test.

DRF keeps its throttle counters in the cache, and the cache is not reset
between tests. Without this, the requests one test makes are still counted
against the next one, so a test that passes alone fails inside the suite -
five of them did - and which tests fail depends on what ran before them.
That makes the suite unable to tell a real regression from noise, which is
worse than having no suite.

Enabled through TEST_RUNNER in settings.
"""
from django.core.cache import cache
from django.test.runner import DiscoverRunner


class CacheIsolatingTestRunner(DiscoverRunner):
    def setup_test_environment(self, **kwargs):
        super().setup_test_environment(**kwargs)

        from django.test import SimpleTestCase

        original_pre_setup = SimpleTestCase._pre_setup

        def _pre_setup(test_case):
            # Runs before setUp, so a test never inherits another's
            # throttle budget or cached queries.
            cache.clear()
            original_pre_setup(test_case)

        SimpleTestCase._pre_setup = _pre_setup
