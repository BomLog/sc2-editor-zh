import tempfile
import unittest
from pathlib import Path

import dpifix_core as core


class LocalizationReleaseTests(unittest.TestCase):
    def test_mismatched_external_file_is_backed_up_and_replaced(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "bundled.txt"
            target = root / "external.txt"
            source.write_text("bundled", encoding="utf-8")
            target.write_text("user version", encoding="utf-8")

            status = core._release_localization_file(str(source), str(target))

            self.assertEqual(status, "replaced")
            self.assertEqual(target.read_text(encoding="utf-8"), "bundled")
            backups = list(root.glob("external.txt.bak.sc2ed_dpifix_*"))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_text(encoding="utf-8"), "user version")

    def test_missing_external_file_is_released(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "bundled.txt"
            target = root / "nested" / "external.txt"
            source.write_text("bundled", encoding="utf-8")

            status = core._release_localization_file(str(source), str(target))

            self.assertEqual(status, "released")
            self.assertEqual(target.read_text(encoding="utf-8"), "bundled")

    def test_matching_external_file_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "bundled.txt"
            target = root / "external.txt"
            source.write_text("same", encoding="utf-8")
            target.write_text("same", encoding="utf-8")

            status = core._release_localization_file(str(source), str(target))

            self.assertEqual(status, "valid")
            self.assertFalse(list(root.glob("*.bak.sc2ed_dpifix_*")))

    def test_compatible_hook_dll_ignores_build_timestamp_difference(self):
        markers = (
            b"MZ",
            b"SC2L10nGetNameCount",
            b"SC2L10nGetHookVersion",
            core._hook_version_marker(),
            "OfficialDependencyNames.tsv".encode("utf-16le"),
            b"loaded official dependency names",
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "bundled.dll"
            target = root / core.L10N_DLL
            source.write_bytes(b"source-build".join(markers))
            target.write_bytes(b"external-build".join(markers))

            status = core._release_localization_file(str(source), str(target))

            self.assertEqual(status, "valid")
            self.assertIn(b"external-build", target.read_bytes())

    def test_outdated_hook_dll_is_backed_up_and_replaced(self):
        common_markers = (
            b"MZ",
            b"SC2L10nGetNameCount",
            b"SC2L10nGetHookVersion",
            "OfficialDependencyNames.tsv".encode("utf-16le"),
            b"loaded official dependency names",
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "bundled.dll"
            target = root / core.L10N_DLL
            source.write_bytes(b"".join(common_markers + (core._hook_version_marker(),)))
            target.write_bytes(
                b"".join(common_markers + (core._hook_version_marker("1.0.0"),))
            )

            status = core._release_localization_file(str(source), str(target))

            self.assertEqual(status, "replaced")
            self.assertEqual(target.read_bytes(), source.read_bytes())
            backups = list(root.glob(f"{core.L10N_DLL}.bak.sc2ed_dpifix_*"))
            self.assertEqual(len(backups), 1)
            self.assertIn(core._hook_version_marker("1.0.0"), backups[0].read_bytes())

    def test_missing_bundled_file_is_an_error(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(core.PatchError):
                core._release_localization_file(
                    str(root / "missing.txt"), str(root / "external.txt")
                )

    def test_temporary_uninstall_and_restore_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            editor = Path(directory) / "Editor"
            first = editor / core.L10N_TABLE
            second = editor / core.L10N_FILES[3]
            first.parent.mkdir(parents=True)
            second.parent.mkdir(parents=True)
            first.write_text("table", encoding="utf-8")
            second.write_text("strings", encoding="utf-8")

            count = core._temporarily_uninstall_editor_dir(str(editor))

            self.assertEqual(count, 2)
            self.assertFalse(first.exists())
            self.assertFalse(second.exists())
            stash = editor / core.L10N_STASH_DIR
            self.assertTrue((stash / core.L10N_STASH_MANIFEST).is_file())

            restored, conflicts = core._restore_localization_editor_dir(str(editor))

            self.assertEqual((restored, conflicts), (2, 0))
            self.assertEqual(first.read_text(encoding="utf-8"), "table")
            self.assertEqual(second.read_text(encoding="utf-8"), "strings")
            self.assertFalse(stash.exists())

    def test_restore_backs_up_a_conflicting_new_file(self):
        with tempfile.TemporaryDirectory() as directory:
            editor = Path(directory) / "Editor"
            target = editor / core.L10N_TABLE
            target.parent.mkdir(parents=True)
            target.write_text("original", encoding="utf-8")
            core._temporarily_uninstall_editor_dir(str(editor))
            target.write_text("new file", encoding="utf-8")

            restored, conflicts = core._restore_localization_editor_dir(str(editor))

            self.assertEqual((restored, conflicts), (1, 1))
            self.assertEqual(target.read_text(encoding="utf-8"), "original")
            backups = list(editor.glob(f"{core.L10N_TABLE}.bak.sc2ed_dpifix_*"))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_text(encoding="utf-8"), "new file")

    def test_restore_refuses_a_corrupt_stashed_file(self):
        with tempfile.TemporaryDirectory() as directory:
            editor = Path(directory) / "Editor"
            target = editor / core.L10N_TABLE
            target.parent.mkdir(parents=True)
            target.write_text("original", encoding="utf-8")
            core._temporarily_uninstall_editor_dir(str(editor))
            stored = editor / core.L10N_STASH_DIR / "files" / core.L10N_TABLE
            stored.write_text("corrupt", encoding="utf-8")

            with self.assertRaises(core.PatchError):
                core._restore_localization_editor_dir(str(editor))

            self.assertFalse(target.exists())
            self.assertTrue(stored.exists())


if __name__ == "__main__":
    unittest.main()
