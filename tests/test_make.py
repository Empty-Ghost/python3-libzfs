"""Check Make's rebuild and failure recovery without compiling the extension."""
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which("make"), "make required")
class MakeTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name)
        (self.path / "Makefile").write_text(
            (ROOT / "Makefile.in").read_text().replace("@prefix@", "/usr")
        )
        for name in ("libzfs.pyx", "converter.pxi", "nvpair.pxi", "setup.py",
                     "config.py", "pyproject.toml"):
            (self.path / name).touch()
        (self.path / "pxd").mkdir()
        for source in (ROOT / "pxd").iterdir():
            name = source.name[:-3] if source.name.endswith(".pxi.in") else source.name
            if Path(name).suffix in (".pxd", ".pxi"):
                (self.path / "pxd" / name).touch()
        self.compiler = self.path / "fake_python.py"
        self.compiler.write_text('''
from pathlib import Path
import os
import sys
if sys.argv[1:3] == ['-m', 'cython']:
    Path('libzfs.c').write_text('generated C')
    if os.environ.get('FAIL_CYTHON'):
        sys.exit(1)
else:
    Path('extension-built').touch()
''')

    def run_make(self, fail=False):
        env = dict(os.environ)
        if fail:
            env["FAIL_CYTHON"] = "1"
        return subprocess.run(
            ["make", "build", f"PYTHON={sys.executable} {self.compiler}"],
            cwd=self.path, env=env, capture_output=True, text=True,
        )

    def test_rebuild_missing_extension(self):
        first = self.run_make()
        self.assertEqual(first.returncode, 0, first.stderr)
        artifact = self.path / "extension-built"
        self.assertTrue(artifact.exists())
        artifact.unlink()
        second = self.run_make()
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertTrue(artifact.exists())

    def test_failed_cython_output_is_removed(self):
        failed = self.run_make(fail=True)
        self.assertNotEqual(failed.returncode, 0)
        self.assertFalse((self.path / "libzfs.c").exists())
        recovered = self.run_make()
        self.assertEqual(recovered.returncode, 0, recovered.stderr)
        self.assertTrue((self.path / "extension-built").exists())
