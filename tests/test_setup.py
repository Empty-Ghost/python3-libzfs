"""Verify configure flags survive a backend that excludes the source path."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(importlib.util.find_spec("Cython"), "Cython required")
class SetupTests(unittest.TestCase):
    def test_configuration_without_source_on_import_path(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "setup.py").write_text((ROOT / "setup.py").read_text())
            (path / "config.py").write_text(
                "CFLAGS = ['-DCONFIG_LOADED']\n"
                "CPPFLAGS = ['-I/configured/headers']\n"
                "LDFLAGS = ['-L/configured/libraries']\n"
            )
            script = '''
import runpy
import sys
from unittest.mock import patch
source = sys.argv[1]
sys.argv = [source, '--name']
with patch('setuptools.setup') as setup:
    runpy.run_path(source, run_name='__main__')
extension = setup.call_args.kwargs['ext_modules'][0]
assert extension.extra_compile_args == ['-DCONFIG_LOADED', '-I/configured/headers']
assert extension.extra_link_args == ['-L/configured/libraries']
'''
            result = subprocess.run(
                [sys.executable, "-c", script, str(path / "setup.py")],
                cwd=ROOT, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
