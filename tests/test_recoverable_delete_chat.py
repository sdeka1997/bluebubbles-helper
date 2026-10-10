#!/usr/bin/env python3
"""Source-level behavior checks for Ventura recoverable chat deletion.

These checks are intentionally non-destructive: they verify the injected helper's
routing and completion semantics without launching Messages or deleting a chat.
"""

from pathlib import Path
import re
import unittest


SOURCE = (
    Path(__file__).parents[1]
    / "Messages/MacOS-11+/BlueBubblesHelper/BlueBubblesHelper.m"
)


def action_branch(source: str, action: str, next_action: str) -> str:
    match = re.search(
        rf'else if \(\[event isEqualToString:@"{re.escape(action)}"\]\) \{{'
        rf'(.*?)'
        rf'else if \(\[event isEqualToString:@"{re.escape(next_action)}"\]\)',
        source,
        re.DOTALL,
    )
    if match is None:
        raise AssertionError(f'missing "{action}" action before "{next_action}"')
    return match.group(1)


class RecoverableDeleteChatSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = SOURCE.read_text()

    def recoverable_branch(self) -> str:
        return action_branch(
            self.source, "recoverable-delete-chat", "delete-chat"
        )

    def test_routes_to_dedicated_recoverable_delete_handler(self) -> None:
        branch = self.recoverable_branch()
        self.assertIn(
            'recoverablyDeleteChatWithGuid:data[@"chatGuid"] transaction:transaction',
            branch,
        )
        self.assertNotIn("_chat_remove:", branch)

    def test_handler_uses_ck_guid_lookup_and_native_recoverable_api(self) -> None:
        self.assertRegex(
            self.source,
            r"conversationForExistingChatWithGUID:\s*chatGuid",
        )
        self.assertRegex(
            self.source,
            r"recoverableDeleteForConversations:\s*@\[conversation\]"
            r"\s*deleteDate:\s*deleteDate"
            r"\s*synchronousQuery:\s*NO"
            r"\s*completionHandler:\s*completionHandler",
        )

    def handler_body(self) -> str:
        handler = re.search(
            r"\+\(void\) recoverablyDeleteChatWithGuid:.*?\n\}",
            self.source,
            re.DOTALL,
        )
        if handler is None:
            self.fail("missing recoverable-delete handler")
        return handler.group(0)

    def test_success_response_is_sent_only_from_completion(self) -> None:
        body = self.handler_body()
        completion = body.find("void (^completionHandler)(void) =")
        native_call = body.find(
            "[conversationList recoverableDeleteForConversations:"
        )
        success = body.find("respond(nil)")
        self.assertGreaterEqual(completion, 0)
        self.assertGreater(success, completion)
        self.assertLess(success, native_call)
        self.assertEqual(body.count("respond(nil)"), 1)

    def test_every_response_goes_through_one_shot_guard(self) -> None:
        body = self.handler_body()
        self.assertIn("if (responded) return;", body)
        guard = body.find("void (^respond)(NSString *) =")
        after_guard = body[body.find("void (^deleteConversation)(void)"):]
        self.assertGreaterEqual(guard, 0)
        self.assertNotIn("sendRecoverableDeleteError:", after_guard)
        self.assertNotIn("sendMessage:", after_guard)

    def test_lookup_runs_inside_exception_handler(self) -> None:
        body = self.handler_body()
        try_at = body.find("@try {")
        self.assertGreaterEqual(try_at, 0)
        self.assertGreater(body.find("[conversationListClass sharedConversationList]"), try_at)
        self.assertGreater(
            body.find("conversationForExistingChatWithGUID:chatGuid"), try_at
        )

    def test_missing_completion_times_out_with_error(self) -> None:
        body = self.handler_body()
        self.assertIn("dispatch_after(", body)
        self.assertIn("did not confirm within 30 seconds", body)

    def test_rejects_non_string_or_empty_guid(self) -> None:
        body = self.handler_body()
        self.assertIn("isKindOfClass:[NSString class]", body)
        self.assertIn("chatGuid.length == 0", body)

    def test_unavailable_and_exception_paths_send_errors(self) -> None:
        self.assertIn("Recoverable chat deletion is unavailable", self.source)
        self.assertIn("Recoverable chat deletion failed", self.source)
        self.assertIn("@catch (NSException *exception)", self.source)

    def test_legacy_delete_chat_remains_permanent_and_separate(self) -> None:
        legacy = action_branch(self.source, "delete-chat", "delete-message")
        self.assertIn("_chat_remove:", legacy)
        self.assertNotIn("recoverableDeleteForConversations:", legacy)


if __name__ == "__main__":
    unittest.main()
