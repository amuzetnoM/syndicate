from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db_manager import DatabaseManager


def test_save_bot_audit_and_get_task(tmp_path):
    db_path = tmp_path / "testdb.db"
    db = DatabaseManager(db_path)

    # Create a dummy task
    with db._get_connection() as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO llm_tasks (document_path, prompt, status) VALUES (?, ?, 'pending')", ("path.md", "p"))
        task_id = cur.lastrowid
        # Ensure no sanitizer records
    # Save a bot audit
    aid = db.save_bot_audit("tester", "approve_attempt", f"task={task_id}")
    assert isinstance(aid, int) and aid > 0

    t = db.get_llm_task(task_id)
    assert t is not None
    assert t["document_path"] == "path.md"
    # Approve should mark completed
    ok = db.approve_llm_task(task_id, "tester")
    assert ok
    t2 = db.get_llm_task(task_id)
    assert t2["status"] == "completed"
