import os
import unittest
import tempfile
from pathlib import Path
from utils import get_sqlite_connection

class TestUtilsSQLite(unittest.TestCase):
    def test_sqlite_wal_mode_and_busy_timeout(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_wal.sqlite"
            conn = get_sqlite_connection(db_path)
            mode = conn.execute("PRAGMA journal_mode;").fetchone()[0]
            self.assertEqual(mode.lower(), "wal")
            conn.close()

if __name__ == "__main__":
    unittest.main()
