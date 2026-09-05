import tempfile
import unittest
from pathlib import Path

import dpifix_core as core
from generate_official_dependency_names import ac_display_stems, resource_aliases


class LocalizationReleaseTests(unittest.TestCase):
    def test_hook_state_requires_fallback_and_tree_hooks(self):
        tree_only = "tree localization hook installed on SendMessageW import"

        self.assertEqual(
            core._localization_hook_state(tree_only), ("waiting", "")
        )

        complete = (
            "hook installed at SC2Editor_x64.exe+0x404B57\n" + tree_only
        )
        self.assertEqual(
            core._localization_hook_state(complete), ("ready", "")
        )

    def test_hook_failure_takes_priority_over_success_markers(self):
        status = (
            "hook installed at SC2Editor_x64.exe+0x404B57\n"
            "tree localization hook installed on SendMessageW import\n"
            "resource hook signature mismatch; hook refused\n"
        )

        self.assertEqual(
            core._localization_hook_state(status),
            ("failed", "resource hook signature mismatch; hook refused"),
        )

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
            b"SC2L10nGetDisplayAliasCount",
            b"SC2L10nGetResourceNameCount",
            b"SC2L10nGetPreservedModelIdCount",
            b"SC2L10nGetTreeInsertHookMarker",
            b"SC2L10nGetHookVersion",
            core._hook_version_marker(),
            "OfficialDependencyNames.tsv".encode("utf-16le"),
            "OfficialResourceNames.tsv".encode("utf-16le"),
            b"loaded official dependency names",
            b"loaded official resource names",
            b"loaded model ids to preserve",
            b"SC2ED_DPIFIX_TREE_INSERT_HOOK=1",
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
            b"SC2L10nGetDisplayAliasCount",
            b"SC2L10nGetResourceNameCount",
            b"SC2L10nGetPreservedModelIdCount",
            b"SC2L10nGetTreeInsertHookMarker",
            b"SC2L10nGetHookVersion",
            "OfficialDependencyNames.tsv".encode("utf-16le"),
            "OfficialResourceNames.tsv".encode("utf-16le"),
            b"loaded official dependency names",
            b"loaded official resource names",
            b"loaded model ids to preserve",
            b"SC2ED_DPIFIX_TREE_INSERT_HOOK=1",
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

    def test_data_file_edits_are_preserved_across_launches(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "OfficialResourceNames.tsv"
            upstream = root / "upstream.tsv"
            upstream.write_text("upstream", encoding="utf-8")
            statuses = {"valid": 0, "released": 0, "updated": 0,
                        "preserved": 0, "replaced": 0}
            baseline = {}

            core._sync_localization_data(
                "hook/OfficialResourceNames.tsv", str(target), str(upstream),
                baseline, statuses,
            )
            self.assertEqual(statuses["released"], 1)
            self.assertEqual(target.read_text(encoding="utf-8"), "upstream")

            target.write_text("my own translation", encoding="utf-8")
            core._sync_localization_data(
                "hook/OfficialResourceNames.tsv", str(target), str(upstream),
                baseline, statuses,
            )
            self.assertEqual(statuses["preserved"], 1)
            self.assertEqual(
                target.read_text(encoding="utf-8"), "my own translation"
            )

    def test_untouched_data_file_follows_bundle_update(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "OfficialResourceNames.tsv"
            upstream = root / "upstream.tsv"
            upstream.write_text("upstream v1", encoding="utf-8")
            statuses = {"valid": 0, "released": 0, "updated": 0,
                        "preserved": 0, "replaced": 0}
            baseline = {}

            core._sync_localization_data(
                "hook/OfficialResourceNames.tsv", str(target), str(upstream),
                baseline, statuses,
            )

            upstream.write_text("upstream v2", encoding="utf-8")
            core._sync_localization_data(
                "hook/OfficialResourceNames.tsv", str(target), str(upstream),
                baseline, statuses,
            )
            self.assertEqual(statuses["updated"], 1)
            self.assertEqual(
                target.read_text(encoding="utf-8"), "upstream v2"
            )
            self.assertEqual(
                baseline["hook/OfficialResourceNames.tsv"],
                core._sha256_hex(str(upstream)),
            )

    def _fake_packages(self, root):
        hook = root / "packages" / "hook"
        editor = root / "packages" / "editor"
        hook.mkdir(parents=True)
        editor.mkdir(parents=True)
        dll_markers = (
            b"MZ", b"SC2L10nGetNameCount", b"SC2L10nGetDisplayAliasCount",
            b"SC2L10nGetResourceNameCount", b"SC2L10nGetPreservedModelIdCount",
            b"SC2L10nGetTreeInsertHookMarker", b"SC2L10nGetHookVersion",
            core._hook_version_marker(),
            "OfficialDependencyNames.tsv".encode("utf-16le"),
            "OfficialResourceNames.tsv".encode("utf-16le"),
            b"loaded official dependency names",
            b"loaded official resource names",
            b"loaded model ids to preserve",
            b"SC2ED_DPIFIX_TREE_INSERT_HOOK=1",
        )
        (hook / core.L10N_DLL).write_bytes(b"fake".join(dll_markers))
        (hook / core.L10N_TABLE).write_text("dependency tsv", encoding="utf-8")
        (hook / core.L10N_RESOURCE_TABLE).write_text("resource tsv", encoding="utf-8")
        (hook / core.L10N_PACKAGE_MANIFEST).write_text(
            '{"format": 1, "name": "hook", "target": "deploy", "files": ['
            f'{{"path": "{core.L10N_DLL}", "policy": "managed"}}, '
            f'{{"path": "{core.L10N_TABLE}", "policy": "editable"}}, '
            f'{{"path": "{core.L10N_RESOURCE_TABLE}", "policy": "editable"}}]}}',
            encoding="utf-8",
        )
        strings = editor / "LocalizedData" / "GameStrings.txt"
        strings.parent.mkdir(parents=True, exist_ok=True)
        strings.write_text("editor strings", encoding="utf-8")
        (editor / core.L10N_PACKAGE_MANIFEST).write_text(
            '{"format": 1, "name": "editor", "target": "editor", "files": ['
            '{"path": "LocalizedData/GameStrings.txt", "policy": "editable"}]}',
            encoding="utf-8",
        )
        return hook, editor

    def test_load_localization_packages_discovers_both_targets(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._fake_packages(root)

            packages = core.load_localization_packages(base=str(root))

            self.assertEqual(
                [(p["name"], p["target"]) for p in packages],
                [("editor", "editor"), ("hook", "deploy")],
            )
            hook = next(p for p in packages if p["name"] == "hook")
            policies = {e["path"]: e["policy"] for e in hook["files"]}
            self.assertEqual(
                policies[core.L10N_DLL], "managed"
            )
            self.assertEqual(
                policies[core.L10N_TABLE], "editable"
            )

    def test_missing_package_file_is_an_error(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._fake_packages(root)
            (root / "packages" / "hook" / core.L10N_TABLE).unlink()

            with self.assertRaises(core.PatchError):
                core.load_localization_packages(base=str(root))

    def test_release_packages_split_deploy_and_editor_targets(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            hook, editor = self._fake_packages(root)
            deploy = root / "deploy"
            editor_target = root / "SC2" / "Editor"
            statuses = {"valid": 0, "released": 0, "updated": 0,
                        "preserved": 0, "replaced": 0,
                        "legacy_removed": 0, "legacy_backed_up": 0}
            baseline = {}
            packages = core.load_localization_packages(base=str(root))

            core._release_localization_packages(
                packages, str(deploy), str(editor_target), baseline, statuses,
            )

            # hook 包 → deploy；editor 包 → 编辑器目录，互不混放。
            self.assertTrue((deploy / core.L10N_DLL).is_file())
            self.assertTrue((deploy / core.L10N_TABLE).is_file())
            self.assertFalse((editor_target / core.L10N_TABLE).exists())
            self.assertTrue(
                (editor_target / "LocalizedData" / "GameStrings.txt").is_file()
            )
            self.assertFalse((deploy / "LocalizedData").exists())
            self.assertEqual(statuses["released"], 4)
            self.assertEqual(
                baseline["editor/LocalizedData/GameStrings.txt"],
                core._sha256_hex(str(editor / "LocalizedData" / "GameStrings.txt")),
            )

            # 用户编辑 editor 数据 → 保留；managed DLL 被篡改 → 备份并替换。
            edited = editor_target / "LocalizedData" / "GameStrings.txt"
            edited.write_text("my own strings", encoding="utf-8")
            (deploy / core.L10N_DLL).write_bytes(b"tampered")
            statuses = {key: 0 for key in statuses}
            core._release_localization_packages(
                packages, str(deploy), str(editor_target), baseline, statuses,
            )
            self.assertEqual(statuses["preserved"], 1)
            self.assertEqual(edited.read_text(encoding="utf-8"), "my own strings")
            self.assertEqual(statuses["replaced"], 1)
            self.assertTrue(
                core._valid_hook_dll(str(deploy / core.L10N_DLL))
            )

    def test_prepare_localization_cleans_legacy_editor_hook_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            hook, editor = self._fake_packages(root)
            deploy = root / "deploy"
            editor_target = root / "SC2" / "Editor"
            editor_target.mkdir(parents=True)
            legacy_tsv = editor_target / core.L10N_TABLE
            legacy_tsv.write_text(
                (hook / core.L10N_TABLE).read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            stale_log = editor_target / core.L10N_LOG
            stale_log.write_text("old hook log", encoding="utf-8")
            statuses = {"valid": 0, "released": 0, "updated": 0,
                        "preserved": 0, "replaced": 0,
                        "legacy_removed": 0, "legacy_backed_up": 0}
            baseline = {}
            packages = core.load_localization_packages(base=str(root))

            core._release_localization_packages(
                packages, str(deploy), str(editor_target), baseline, statuses,
            )
            core._remove_legacy_hook_files(
                editor_target, packages, statuses,
            )

            # 与新版一致 → 直接清理；旧日志一并移除。
            self.assertFalse(legacy_tsv.exists())
            self.assertFalse(stale_log.exists())
            self.assertEqual(statuses["legacy_removed"], 1)
            self.assertEqual(statuses["legacy_backed_up"], 0)
            self.assertFalse(list(editor_target.glob("*.bak.sc2ed_dpifix_*")))


class ResourceAliasTests(unittest.TestCase):
    def test_resource_aliases_cover_editor_acronym_spellings(self):
        aliases = resource_aliases("VoidShardACDamageFieldImpactFX")

        self.assertIn("Void Shard ACDamage Field Impact FX", aliases)
        self.assertIn("Void Shard AC Damage Field Impact FX", aliases)
        self.assertIn("VoidShardACDamageFieldImpactFX", aliases)

    def test_ac_display_stems_reproduce_parent_annotated_tree_name(self):
        stems = ac_display_stems(
            "Void Shard ACDamage Field Impact", {"Impact FX"}
        )

        self.assertIn("Void Shard Damage Field", stems)
        self.assertIn("Void Shard Void Shard Damage Field", stems)


if __name__ == "__main__":
    unittest.main()
