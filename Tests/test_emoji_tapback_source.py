#!/usr/bin/env python3
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "Messages/MacOS-11+/BlueBubblesHelper/BlueBubblesHelper.m"


class EmojiTapbackSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SOURCE.read_text()

    def test_custom_emoji_uses_immessage_constructor(self):
        """Custom reactions must stay on IMCore and carry Apple's emoji field."""
        self.assertIn(
            "instantMessageWithAssociatedMessageContent:associatedMessageGUID:associatedMessageType:associatedMessageRange:associatedMessageEmoji:messageSummaryInfo:threadIdentifier:",
            self.source,
        )
        self.assertIn('data[@"reactionEmoji"]', self.source)
        self.assertIn("return 2006;", self.source)
        self.assertIn("return 3006;", self.source)

    def test_custom_emoji_does_not_add_chatkit_or_rewritten_helper_api(self):
        """The minimal backport must not revive the ChatKit loader dependency."""
        for forbidden in (
            "#import <CKChatItem.h>",
            "#import <CKChatController.h>",
            'NSClassFromString(@"CKChatItem")',
            'NSClassFromString(@"IMEmojiTapback")',
        ):
            self.assertNotIn(forbidden, self.source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
