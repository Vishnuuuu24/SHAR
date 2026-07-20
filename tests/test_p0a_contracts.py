from __future__ import annotations

import hashlib
import json
import shutil
import struct
import tempfile
import unittest
from pathlib import Path

from data.contracts import (
    MANIFEST_FIELDS,
    load_json,
    validate_access_registry,
    validate_manifest_row,
    validate_manifest_schema,
    validate_task_contract,
)
from data.inventory import PNG_SIGNATURE, build_inventory, inspect_bounded, iter_file_items


REPO_ROOT = Path(__file__).resolve().parents[1]


def fake_png(width: int, height: int, payload: bytes = b"") -> bytes:
    return PNG_SIGNATURE + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", width, height) + payload


class InventoryTests(unittest.TestCase):
    def _scan(self, root: Path) -> list:
        dataset = {
            "dataset_id": "fixture",
            "include_extensions": [".png"],
            "component_rules": [{"prefix": "Train", "component_id": "fixture_train"}],
        }
        items = iter_file_items(root, dataset, {".DS_Store"}, ("._",))
        return list(inspect_bounded(items, workers=2, batch_size=2))

    def test_inventory_is_sorted_and_content_addressed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "Train").mkdir()
            (root / "Train/z.png").write_bytes(fake_png(64, 64, b"z"))
            (root / "Train/a.png").write_bytes(fake_png(64, 64, b"a"))
            records = self._scan(root)
            self.assertEqual([record.relative_path for record in records], ["Train/a.png", "Train/z.png"])
            first_digest = records[0].sha256
            self.assertEqual((records[0].width, records[0].height), (64, 64))
            (root / "Train/a.png").write_bytes(fake_png(64, 64, b"changed"))
            self.assertNotEqual(self._scan(root)[0].sha256, first_digest)

    def test_malformed_png_is_a_hard_error(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "Train").mkdir()
            (root / "Train/bad.png").write_bytes(b"not a png")
            record = self._scan(root)[0]
            self.assertEqual(record.status, "error")
            self.assertIn("IHDR", record.error)

    def test_symlink_is_not_followed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "Train").mkdir()
            target = root / "target.png"
            target.write_bytes(fake_png(64, 64))
            (root / "Train/link.png").symlink_to(target)
            records = self._scan(root)
            link = next(record for record in records if record.relative_path == "Train/link.png")
            self.assertEqual(link.status, "error")
            self.assertIn("symlinks", link.error)

    def test_end_to_end_artifact_finalization(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            shutil.copytree(REPO_ROOT / "data", root / "data")
            dataset_root = root / "Datasets/UCF"
            (dataset_root / "Train/Abuse").mkdir(parents=True)
            (dataset_root / "Train/Abuse/a.png").write_bytes(fake_png(64, 64, b"a"))
            (dataset_root / "Train/Abuse/b.png").write_bytes(fake_png(64, 64, b"b"))
            config = {
                "schema_version": "test",
                "ignored_names": [".DS_Store"],
                "ignored_prefixes": ["._"],
                "datasets": [
                    {
                        "dataset_id": "ucf_crime_kaggle_frames",
                        "root": "Datasets/UCF",
                        "include_extensions": [".png"],
                        "component_rules": [{"prefix": "Train", "component_id": "fixture_train"}],
                        "group_depth": 2,
                        "expectations": {
                            "total_files": 2,
                            "prefix_counts": {"Train": 2},
                            "required_child_directories": {"Train": ["Abuse"]},
                            "allowed_resolutions": ["64x64"],
                        },
                    }
                ],
            }
            config_path = root / "data/registry/local_inventory.json"
            config_path.write_text(json.dumps(config), encoding="utf-8")
            artifact = build_inventory(root, config_path, root / "results/p0a", workers=2)
            verification = load_json(artifact / "verification.json")
            self.assertEqual(verification["checks"]["V-D1"]["verdict"], "PASS")
            self.assertFalse(verification["scope_assertions"]["training_performed"])
            self.assertTrue((artifact / "inventory_files.csv.gz").is_file())
            self.assertEqual(build_inventory(root, config_path, root / "results/p0a", workers=2), artifact)
            reproduction = load_json(root / "results/p0a" / f"reproduction-{artifact.name.removeprefix('inventory-')}.json")
            self.assertEqual(reproduction["verdict"], "PASS")
            self.assertTrue(reproduction["byte_identical_detailed_inventory"])


class ContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.schema = load_json(REPO_ROOT / "data/schemas/frame_manifest_row.schema.json")
        self.task = load_json(REPO_ROOT / "data/registry/task_contract.json")
        self.access = load_json(REPO_ROOT / "data/registry/dataset_access.json")
        self.good_row = dict(
            zip(
                MANIFEST_FIELDS,
                [
                    "Train/Abuse/Abuse001_x264_10.png",
                    "ucf_crime_kaggle_frames",
                    "Abuse001_x264",
                    10,
                    "Abuse",
                    "video_inherited",
                    "ucf_kaggle_folder_mirror",
                    "mirror_snapshot_pending_digest",
                    None,
                    "train",
                    hashlib.sha256(b"fixture").hexdigest(),
                ],
            )
        )

    def test_checked_in_contracts_are_valid(self) -> None:
        self.assertEqual(validate_manifest_schema(self.schema), [])
        self.assertEqual(validate_task_contract(self.task), [])
        self.assertEqual(validate_access_registry(self.access), [])

    def test_manifest_positive_fixture(self) -> None:
        self.assertEqual(validate_manifest_row(self.good_row), [])

    def test_manifest_rejects_missing_unordered_and_extra_fields(self) -> None:
        bad = dict(self.good_row)
        bad.pop("source_video_id")
        bad["unexpected"] = "value"
        self.assertTrue(validate_manifest_row(bad))

    def test_manifest_rejects_bad_paths_digests_and_enums(self) -> None:
        for filepath in ("/absolute.png", "../escape.png", "Train\\bad.png"):
            bad = dict(self.good_row)
            bad["filepath"] = filepath
            self.assertTrue(validate_manifest_row(bad), filepath)
        bad = dict(self.good_row)
        bad["file_digest"] = "ABC"
        bad["label_scope"] = "invented"
        bad["split"] = "quarantine"
        self.assertGreaterEqual(len(validate_manifest_row(bad)), 3)

    def test_manifest_interval_is_boolean_or_null(self) -> None:
        for value in (None, True, False):
            row = dict(self.good_row)
            row["inside_official_interval"] = value
            self.assertEqual(validate_manifest_row(row), [])
        row = dict(self.good_row)
        row["inside_official_interval"] = 1
        self.assertTrue(validate_manifest_row(row))

    def test_teacher_roi_uses_higher_authority_label_source(self) -> None:
        row = dict(self.good_row)
        row["label_scope"] = "teacher_roi"
        row["label_source"] = "teacher_roi"
        self.assertIn("teacher_roi rows must use label_source=teacher", validate_manifest_row(row))
        row["label_source"] = "teacher"
        self.assertEqual(validate_manifest_row(row), [])

    def test_registry_keeps_media_and_annotations_separate(self) -> None:
        broken = {**self.access, "datasets": [dict(item) for item in self.access["datasets"]]}
        broken["datasets"][0] = dict(broken["datasets"][0])
        broken["datasets"][0]["components"] = [broken["datasets"][0]["components"][0]]
        self.assertTrue(validate_access_registry(broken))


if __name__ == "__main__":
    unittest.main()
