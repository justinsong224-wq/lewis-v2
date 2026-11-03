from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import view_demo

class CaseViewerTests(unittest.TestCase):
    def test_selects_existing_sms_database_without_changing_bytes(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(view_demo, 'ROOT', Path(temp)):
            database = Path(temp) / 'backend/workspace/validation/sms-history.db'
            database.parent.mkdir(parents=True)
            database.write_bytes(b'existing-history')
            self.assertEqual(view_demo.select_database(), database)
            self.assertEqual(database.read_bytes(), b'existing-history')

    def test_missing_database_is_not_silently_created(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(view_demo, 'ROOT', Path(temp)):
            with self.assertRaises(FileNotFoundError):
                view_demo.select_database()
