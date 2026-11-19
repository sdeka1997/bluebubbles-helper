#!/usr/bin/env python3
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "Messages/MacOS-11+/BlueBubblesHelper/BlueBubblesHelper.m"


def branch(source, event):
    start = source.index('isEqualToString:@"%s"' % event)
    end = source.index("} else if ([event isEqualToString:", start)
    return source[start:end]


class FocusStatusSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.body = branch(SOURCE.read_text(), "check-focus-status")

    def test_prefers_sequoia_selector_then_falls_back(self):
        """Sequoia only has the public name; older macOS only the underscored one."""
        public = self.body.index('@"fetchUpdatedStatusForHandle:completion:"')
        private = self.body.index('@"_fetchUpdatedStatusForHandle:completion:"')
        self.assertLess(public, private)

    def test_calls_the_selector_it_checked(self):
        """The call must go through the selector found, not a hardcoded name."""
        self.assertIn("instancesRespondToSelector:fetch]", self.body)
        self.assertIn("fetchStatus([cls sharedInstance], fetch, handle,", self.body)
        self.assertNotIn("] _fetchUpdatedStatusForHandle:", self.body)

    def test_still_answers_silenced_and_missing_selector(self):
        self.assertIn('@"silenced"', self.body)
        self.assertIn('@"Selector not found!"', self.body)


if __name__ == "__main__":
    unittest.main()
