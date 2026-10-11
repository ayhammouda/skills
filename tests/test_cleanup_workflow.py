"""Deterministic replay + independent preservation oracles, not model compliance."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import cleanup_fixture as fixture
import cleanup_replay as replay


class CleanupWorkflow(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="cleanup scenario ü-")
        self.addCleanup(self.temp.cleanup)
        self.state = fixture.setup_review(Path(self.temp.name) / "fixture with spaces")

    def test_full_workflow_preserves_work_knowledge_and_recovery(self):
        state = self.state
        replay.audit(state)
        fixture.verify_review(state, "audit")
        with self.assertRaisesRegex(AssertionError, "Removed obsolete tracked"):
            fixture.verify_review(state, "default")
        replay.apply_reviewed_files(state)
        fixture.verify_review(state, "default")
        self.assertFalse(replay.delete_fixture_branch(state))
        fixture.verify_review(state, "default")
        self.assertTrue(replay.delete_fixture_branch(state, authorized=True))
        fixture.verify_review(state, "branches")
        self.assertEqual(fixture.restore(state), 8)
        replay.audit(state)
        fixture.verify_review(state, "repeat")
        fixture.setup_operations(state)
        self.assertTrue(replay.operation_active(state))
        self.assertFalse(replay.delete_fixture_branch(state, "finished-later", authorized=True))
        fixture.verify_operations(state)
        events = [json.loads(line) for line in (Path(state["root"]) / "fetch-trace.jsonl").read_text().splitlines()]
        children = [event.get("argv", []) for event in events if event.get("event") == "child_start"]
        self.assertFalse(any("maintenance" in argv or "gc" in argv for argv in children), children)

    def test_changed_candidate_aborts_before_any_mutation(self):
        state = self.state
        (Path(state["trees"]["retired worktree"]) / "new-user-notes.md").write_text("Unreviewed work")
        before = fixture.snapshot(state), fixture.review_snapshot(state)
        with self.assertRaisesRegex(AssertionError, "evidence changed"):
            replay.apply_reviewed_files(state)
        self.assertEqual((fixture.snapshot(state), fixture.review_snapshot(state)), before)
        self.assertFalse((Path(state["root"]) / "recovery").exists())

    def test_ineligible_branches_survive_explicit_opt_in(self):
        state = self.state
        for branch in ["finished-task", "main", "release/protected", "live-upstream",
                       "local-no-upstream", "multi-upstream", "unique-gone"]:
            with self.subTest(branch=branch):
                before = fixture.snapshot(state), fixture.review_snapshot(state)
                self.assertFalse(replay.delete_fixture_branch(state, branch, authorized=True))
                self.assertEqual((fixture.snapshot(state), fixture.review_snapshot(state)), before)

    def test_remote_failure_is_not_absence(self):
        state = self.state
        replay.apply_reviewed_files(state)
        remote = Path(state["remote"])
        remote.rename(remote.with_suffix(".unavailable"))
        before = fixture.snapshot({**state, "remote": str(remote.with_suffix(".unavailable"))})
        self.assertFalse(replay.delete_fixture_branch(state, authorized=True))
        self.assertEqual(fixture.snapshot({**state, "remote": str(remote.with_suffix(".unavailable"))}), before)

    def test_branch_changed_during_fetch_is_retained(self):
        state = self.state
        replay.apply_reviewed_files(state)
        original_git = replay.git

        def concurrent_change(repo, *args, **kwargs):
            result = original_git(repo, *args, **kwargs)
            if args[0] == "fetch":
                original_git(repo, "update-ref", "refs/heads/finished-task", state["unique"])
            return result

        with patch.object(replay, "git", side_effect=concurrent_change):
            self.assertFalse(replay.delete_fixture_branch(state, authorized=True))
        self.assertEqual(fixture.git(state["project"], "rev-parse", "finished-task").stdout.decode().strip(), state["unique"])

    def test_preservation_oracle_detects_lost_user_work(self):
        state = self.state
        replay.apply_reviewed_files(state)
        (Path(state["project"]) / "user-staged.md").write_text("Lost unstaged edit")
        with self.assertRaisesRegex(AssertionError, "Preserved primary file"):
            fixture.verify_review(state, "default")

    def test_retention_oracle_detects_missing_decision_rationale(self):
        state = self.state
        replay.apply_reviewed_files(state)
        document = Path(state["project"]) / "docs/architecture.md"
        document.write_text(document.read_text().replace("network service", "different approach"))
        with self.assertRaises(AssertionError):
            fixture.verify_review(state, "default")

    def test_recovery_oracle_detects_corrupt_backup(self):
        state = self.state
        replay.apply_reviewed_files(state)
        archive = Path(state["root"]) / "recovery/temporary-ai-files.tar"
        import tarfile
        with tarfile.open(archive) as stream:
            offset = stream.getmembers()[0].offset_data
        with archive.open("r+b") as stream:
            stream.seek(offset)
            stream.write(b"!")
        with self.assertRaisesRegex(AssertionError, "Backup bytes verified"):
            fixture.verify_review(state, "default")


if __name__ == "__main__":
    unittest.main()
