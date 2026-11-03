"""用真实子进程验证日志与退出码，不调用模型或数据库。"""
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from run_demo_logged import run_logged


class DemoLauncherTests(unittest.TestCase):
    def test_stderr_does_not_change_success_or_hide_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            for code in (0, 7):
                with self.subTest(code=code):
                    log = Path(temp) / ('exit-' + str(code) + '.log')
                    script = Path(temp) / 'child.py'
                    script.write_text('import sys\nsys.stderr.write(chr(100) + chr(10))\nsys.exit(' + str(code) + ')')
                    self.assertEqual(run_logged([sys.executable, str(script)], log), code)
                    self.assertEqual(log.read_text(), 'd\n')

    def test_start_failure_is_not_reported_as_success(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(OSError):
                run_logged([str(Path(temp) / 'missing-executable')], Path(temp) / 'error.log')
