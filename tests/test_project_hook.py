"""The example project hook catches an unapproved font (#46 simulation)."""
import importlib.util
import io
import pathlib
import tempfile
import unittest
from contextlib import redirect_stdout

ROOT = pathlib.Path(__file__).resolve().parents[1]
HOOK = ROOT / "examples" / "project-hook"
spec = importlib.util.spec_from_file_location("check_fonts", HOOK / "check_fonts.py")
check_fonts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_fonts)


class FontHookTests(unittest.TestCase):
    def run_hook(self, css):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp, "styles.css")
            path.write_text(css, encoding="utf-8")
            out = io.StringIO()
            with redirect_stdout(out):
                code = check_fonts.main([str(HOOK / "fonts.json"), str(path)])
            return code, out.getvalue()

    def test_unapproved_font_fails(self):
        code, out = self.run_hook("h1 { font-family: 'Times New Roman', serif; }")
        self.assertEqual(code, 1)
        self.assertIn("'Times New Roman' is not in the approved tokens", out)
        self.assertIn("'serif'", out)

    def test_approved_fonts_pass(self):
        self.assertEqual(self.run_hook("body{font-family:Helvetica, Arial, sans-serif}")[0], 0)


if __name__ == "__main__":
    unittest.main()
