#!/usr/bin/env python3
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "Messages/MacOS-11+/BlueBubblesHelper/BlueBubblesHelper.m"


def method_body(source, signature):
    start = source.index(signature)
    end = source.index("\n}\n", start)
    return source[start:end]


class SendChatFallbackSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SOURCE.read_text()

    def test_send_path_resolves_chat_with_fallbacks(self):
        """Every Private API send goes through the fallback-aware lookup."""
        send = method_body(self.source, "+(void) sendMessage: (NSDictionary *) data transfers:")
        self.assertIn("[BlueBubblesHelper getChatForSend: data :transaction]", send)
        self.assertNotIn("getChat: data[@\"chatGuid\"]", send)

    def test_guid_lookup_stays_first_then_group_id_then_handle(self):
        """Chats the Mac knows by GUID must resolve exactly as before."""
        body = method_body(self.source, "+(IMChat *) getChatForSend:")
        guid = body.index("[BlueBubblesHelper getChat: data[@\"chatGuid\"] :nil]")
        group = body.index("existingChatWithGroupID:")
        handle = body.index("chatForIMHandle:")
        self.assertLess(guid, group)
        self.assertLess(group, handle)
        self.assertIn("@\"Chat does not exist!\"", body)

    def test_handle_fallback_is_one_to_one_only(self):
        """A group must never be resolved (or created) from its participants."""
        body = method_body(self.source, "+(IMChat *) getChatForSend:")
        self.assertIn("containsString:@\";-;\"]", body)
        self.assertIn("count] == 1", body)
        self.assertNotIn("chatForIMHandles:", body)

    def test_plain_guid_lookup_is_unchanged(self):
        """Non-send actions keep the original GUID-only lookup."""
        body = method_body(self.source, "+(IMChat *) getChat: (NSString *) guid")
        self.assertNotIn("GroupID", body)
        self.assertNotIn("IMHandle", body)


if __name__ == "__main__":
    unittest.main(verbosity=2)
