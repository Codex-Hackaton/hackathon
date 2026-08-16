from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from penalty_app.application import SessionService
from penalty_app.domain import PenaltyType, SessionState
from penalty_app.persistence import SQLiteSessionRepository


class SQLiteSessionRepositoryTests(unittest.TestCase):
    def test_session_state_and_audit_log_survive_a_restart(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            database_path = Path(temporary_directory) / "offmate.sqlite3"
            repository = SQLiteSessionRepository(database_path)
            service = SessionService(repository)

            created = service.create_session(
                owner_user_id="user_a",
                active_member_ids=["user_b"],
                default_penalty=PenaltyType.OBSTRUCTION,
            )
            session_id = created.session.session_id
            service.start_viewing(session_id=session_id, actor_user_id="user_a")
            service.end_viewing(session_id=session_id, actor_user_id="user_a")
            repository.close()

            reopened = SQLiteSessionRepository(database_path)
            restored = reopened.get(session_id)

            self.assertEqual(restored.session.state, SessionState.PENALTY_ACTIVE)
            self.assertEqual(restored.session.active_penalty, PenaltyType.OBSTRUCTION)
            self.assertEqual(restored.controller_user_id, "user_b")
            self.assertEqual(
                [event.action for event in restored.audit_events],
                [
                    "SESSION_CREATED",
                    "VIEWING_WINDOW_STARTED",
                    "DEFAULT_PENALTY_APPLIED",
                ],
            )
            self.assertEqual(
                [record.session.session_id for record in reopened.list_for_user("user_b")],
                [session_id],
            )
            reopened.close()


if __name__ == "__main__":
    unittest.main()
