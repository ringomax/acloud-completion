import importlib.util
import tempfile
import unittest
from pathlib import Path

path = Path(__file__).resolve().parents[1] / "scripts/install-figxit.py"
module_spec = importlib.util.spec_from_file_location("installer", path)
installer = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(installer)


class OverlayTest(unittest.TestCase):
    def test_preserves_bundled_specs_and_custom_specs_across_reinstallation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = root / "Figxit.app"
            bundle = app / "Contents/Resources/specs"
            bundle.mkdir(parents=True)
            (bundle / "index.js").write_text('export default ["git", "pnpm"];')
            for name in ("git", "pnpm"):
                (bundle / (name + ".js")).write_text('export default {name: "' + name + '"};')
            extra = root / "extra"
            extra.mkdir()
            (extra / "gcloud.js").write_text('export default {name: "gcloud"};')
            overlay = installer.install(app, root / "data", [extra])
            installer.install(app, root / "data")
            self.assertEqual((overlay / "git.js").read_text(), (bundle / "git.js").read_text())
            self.assertEqual((overlay / "pnpm.js").read_text(), (bundle / "pnpm.js").read_text())
            self.assertTrue((overlay / "acloud.js").is_file())
            self.assertTrue((overlay / "gcloud.js").is_file())
            self.assertIn('"gcloud"', (overlay / "index.js").read_text())
            self.assertIn('import bundled from', (overlay / "index.js").read_text())
