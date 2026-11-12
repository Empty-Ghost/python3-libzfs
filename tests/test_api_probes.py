"""Compile the actual configure probes against legacy and OpenZFS 2.4 APIs.

No OpenZFS installation or pool is needed. Run:
    python3 -m unittest discover -s tests -v
"""
from pathlib import Path
import os
import re
import shlex
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
AC = (ROOT / "configure.ac").read_text()
START = AC.index("dnl OpenZFS 2.4 API changes.")
END = AC.index("CFLAGS=$py_libzfs_save_CFLAGS", START)
PROBES = re.findall(
    r"AC_MSG_CHECKING\(\[(HAVE_\w+)\]\)\s*"
    r"AC_COMPILE_IFELSE\(\[AC_LANG_PROGRAM\(\s*"
    r"\[#include <libzfs.h>\],\s*\[(.*?)\]\s*"
    r"\)\], \[AC_SUBST\(\1, (\d+)\)\], \[AC_SUBST\(\1, (\d+)\)\]\)",
    AC[START:END], re.S,
)
CC = shlex.split(os.environ.get("CC", "cc"))

def header(modern, status_args=3):
    const = "const " if modern else ""
    return f"""
#include <stddef.h>
#include <stdint.h>
typedef unsigned int uint_t;
typedef int boolean_t;
typedef struct nvpair nvpair_t;
typedef struct nvlist nvlist_t;
typedef struct zpool_handle zpool_handle_t;
typedef int zpool_status_t;
typedef int zpool_errata_t;
int zpool_add(zpool_handle_t *, nvlist_t *{', boolean_t' if modern else ''});
typedef int (*zfs_userspace_cb_t)(void *, const char *, uint32_t, uint64_t{', uint64_t' if modern else ''});
zpool_status_t zpool_get_status(zpool_handle_t *, {const}char **{', zpool_errata_t *' if status_args == 3 else ''});
int nvpair_value_string({const}nvpair_t *, {const}char **);
int nvpair_value_string_array(nvpair_t *, {const}char ***, uint_t *);
int nvlist_add_string_array(nvlist_t *, const char *, {const}char * const *, uint_t);
int nvlist_add_nvlist_array(nvlist_t *, const char *, {const}nvlist_t *{' const' if modern else ''} *, uint_t);
"""

@unittest.skipUnless(shutil.which(CC[0]), "C compiler required")
class APIProbeTests(unittest.TestCase):
    def test_probes_against_headers(self):
        self.assertEqual(len(PROBES), 7)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            for modern, status_args in ((False, 2), (False, 3), (True, 3)):
                (path / "libzfs.h").write_text(header(modern, status_args))
                for name, body, yes, no in PROBES:
                    with self.subTest(modern=modern, status_args=status_args, probe=name):
                        source = '#include <libzfs.h>\nint main(void) {\n' + body + '\nreturn 0;\n}\n'
                        (path / "probe.c").write_text(source)
                        result = subprocess.run(
                            CC + ["-Werror=incompatible-pointer-types", "-Werror=implicit-function-declaration",
                                  "-I", directory, "-c", str(path / "probe.c"), "-o", str(path / "probe.o")],
                            capture_output=True, text=True,
                        )
                        self.assertEqual(result.returncode == 0, modern, result.stderr)

    def test_shipped_configure_probes(self):
        """Exercise the checked-in shell probes, including flag restoration."""
        script = (ROOT / "configure").read_text()
        start = script.index("# OpenZFS 2.4 API changes.")
        end = script.index("CFLAGS=$py_libzfs_save_CFLAGS", start)
        block = script[start:end] + "CFLAGS=$py_libzfs_save_CFLAGS\n"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "confdefs.h").write_text("")
            harness = """
exec 5>/dev/null
exec 6>/dev/null
as_me=test
as_nop=:
ac_ext=c
ac_objext=o
CFLAGS=-DPROBE_SENTINEL
ac_fn_c_try_compile() {
    $CC $CFLAGS -I. -c conftest.c -o conftest.o 2>conftest.err
}
""" + block + '\ntest "$CFLAGS" = "-DPROBE_SENTINEL" || exit 1\n'
            harness += "\n".join(f'printf "{name}=%s\\n" "${name}"' for name, *_ in PROBES)
            for modern, status_args in ((False, 2), (False, 3), (True, 3)):
                with self.subTest(modern=modern, status_args=status_args):
                    (path / "libzfs.h").write_text(header(modern, status_args))
                    result = subprocess.run(
                        ["sh", "-c", harness], cwd=path,
                        env={**os.environ, "CC": shlex.join(CC)},
                        capture_output=True, text=True, check=True,
                    )
                    values = dict(line.split("=") for line in result.stdout.splitlines())
                    self.assertEqual(values, {name: yes if modern else no for name, _, yes, no in PROBES})

if __name__ == "__main__":
    unittest.main()
