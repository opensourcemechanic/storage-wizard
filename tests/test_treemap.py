"""
Tests for the treemap plugin.
"""

import json
import os
import tempfile
from pathlib import Path

import pytest

from storage_wizard.treemap import (
    TreemapBuilder,
    TreeNode,
    find_duplicate_nodes,
    save_treemap,
    load_treemap,
    list_saved_treemaps,
    generate_printable_label,
    generate_qr_label,
    generate_qr_image,
    _qr_payload,
    _format_size,
    _hash_from_parts,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def simple_tree(tmp_path: Path) -> Path:
    """
    tmp_path/
        a/
            file1.txt  (10 bytes)
            file2.txt  (20 bytes)
        b/
            file3.txt  (30 bytes)
        root.txt       (5 bytes)
    """
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    (tmp_path / "a" / "file1.txt").write_bytes(b"x" * 10)
    (tmp_path / "a" / "file2.txt").write_bytes(b"y" * 20)
    (tmp_path / "b" / "file3.txt").write_bytes(b"z" * 30)
    (tmp_path / "root.txt").write_bytes(b"r" * 5)
    return tmp_path


@pytest.fixture()
def duplicate_tree(tmp_path: Path) -> tuple:
    """
    Two subtrees with identical structure and content so their hashes match.
    Returns (root_path, copy1_path, copy2_path).
    """
    for name in ("copy1", "copy2"):
        d = tmp_path / name
        d.mkdir()
        (d / "sub").mkdir()
        (d / "sub" / "data.txt").write_bytes(b"identical content")
        (d / "readme.txt").write_bytes(b"same readme")
    return tmp_path, tmp_path / "copy1", tmp_path / "copy2"


# ---------------------------------------------------------------------------
# Unit tests — TreemapBuilder
# ---------------------------------------------------------------------------

class TestTreemapBuilder:

    def test_basic_scan_returns_root_node(self, simple_tree):
        builder = TreemapBuilder()
        node = builder.build(str(simple_tree))
        assert isinstance(node, TreeNode)
        assert node.path == str(simple_tree)

    def test_file_count(self, simple_tree):
        builder = TreemapBuilder()
        node = builder.build(str(simple_tree))
        assert node.file_count == 4  # file1, file2, file3, root.txt

    def test_total_size(self, simple_tree):
        builder = TreemapBuilder()
        node = builder.build(str(simple_tree))
        assert node.size == 65  # 10+20+30+5

    def test_children_present(self, simple_tree):
        builder = TreemapBuilder()
        node = builder.build(str(simple_tree))
        child_names = {c.name for c in node.children}
        assert "a" in child_names
        assert "b" in child_names

    def test_hash_is_non_empty(self, simple_tree):
        builder = TreemapBuilder()
        node = builder.build(str(simple_tree))
        assert node.hash
        assert node.hash != "permission-denied"

    def test_identical_dirs_same_hash(self, duplicate_tree):
        root, copy1, copy2 = duplicate_tree
        builder = TreemapBuilder()
        root_node = builder.build(str(root))
        hashes = {c.name: c.hash for c in root_node.children}
        assert hashes["copy1"] == hashes["copy2"]

    def test_different_dirs_different_hash(self, simple_tree):
        builder = TreemapBuilder()
        node = builder.build(str(simple_tree))
        child_hashes = [c.hash for c in node.children]
        assert child_hashes[0] != child_hashes[1]

    def test_slow_mode_produces_hash(self, simple_tree):
        builder = TreemapBuilder(slow=True)
        node = builder.build(str(simple_tree))
        assert node.hash
        assert len(node.hash) > 0

    def test_slow_identical_dirs_same_hash(self, duplicate_tree):
        root, copy1, copy2 = duplicate_tree
        builder = TreemapBuilder(slow=True)
        root_node = builder.build(str(root))
        hashes = {c.name: c.hash for c in root_node.children}
        assert hashes["copy1"] == hashes["copy2"]

    def test_empty_directory(self, tmp_path):
        empty = tmp_path / "empty"
        empty.mkdir()
        builder = TreemapBuilder()
        node = builder.build(str(empty))
        assert node.file_count == 0
        assert node.size == 0
        assert node.hash  # still gets a hash ("empty" sentinel)

    def test_hidden_files_excluded_by_default(self, tmp_path):
        (tmp_path / ".hidden").write_bytes(b"secret")
        (tmp_path / "visible.txt").write_bytes(b"visible")
        builder = TreemapBuilder(include_hidden=False)
        node = builder.build(str(tmp_path))
        assert node.file_count == 1

    def test_hidden_files_included_when_requested(self, tmp_path):
        (tmp_path / ".hidden").write_bytes(b"secret")
        (tmp_path / "visible.txt").write_bytes(b"visible")
        builder = TreemapBuilder(include_hidden=True)
        node = builder.build(str(tmp_path))
        assert node.file_count == 2

    @pytest.mark.skipif(os.getuid() == 0, reason="root bypasses permission checks")
    def test_permission_denied_dir_recorded(self, tmp_path):
        locked = tmp_path / "locked"
        locked.mkdir()
        (locked / "secret.txt").write_bytes(b"secret")
        locked.chmod(0o000)
        try:
            builder = TreemapBuilder()
            node = builder.build(str(tmp_path))
            assert any(str(locked) in p for p in builder.permission_denied)
        finally:
            locked.chmod(0o755)

    @pytest.mark.skipif(os.getuid() == 0, reason="root bypasses permission checks")
    def test_permission_denied_node_hash(self, tmp_path):
        locked = tmp_path / "locked"
        locked.mkdir()
        locked.chmod(0o000)
        try:
            builder = TreemapBuilder()
            node = builder.build(str(tmp_path))
            locked_child = next((c for c in node.children if c.name == "locked"), None)
            assert locked_child is not None
            assert locked_child.hash == "permission-denied"
        finally:
            locked.chmod(0o755)

    @pytest.mark.skipif(os.getuid() == 0, reason="root bypasses permission checks")
    def test_permission_denied_does_not_stop_scan(self, tmp_path):
        locked = tmp_path / "locked"
        locked.mkdir()
        locked.chmod(0o000)
        (tmp_path / "accessible.txt").write_bytes(b"hello")
        try:
            builder = TreemapBuilder()
            node = builder.build(str(tmp_path))
            assert node.file_count >= 1  # accessible.txt counted
            assert len(builder.permission_denied) >= 1
        finally:
            locked.chmod(0o755)

    @pytest.mark.skipif(os.getuid() == 0, reason="root bypasses permission checks")
    def test_permission_denied_list_reset_between_builds(self, tmp_path):
        locked = tmp_path / "locked"
        locked.mkdir()
        locked.chmod(0o000)
        try:
            builder = TreemapBuilder()
            builder.build(str(tmp_path))
            first_count = len(builder.permission_denied)
            builder.build(str(tmp_path))
            assert len(builder.permission_denied) == first_count  # not doubled
        finally:
            locked.chmod(0o755)


# ---------------------------------------------------------------------------
# Unit tests — TreeNode serialisation
# ---------------------------------------------------------------------------

class TestTreeNodeSerialization:

    def test_round_trip(self, simple_tree):
        builder = TreemapBuilder()
        node = builder.build(str(simple_tree))
        d = node.to_dict()
        restored = TreeNode.from_dict(d)
        assert restored.hash == node.hash
        assert restored.size == node.size
        assert restored.file_count == node.file_count
        assert len(restored.children) == len(node.children)

    def test_children_depth_preserved(self, simple_tree):
        builder = TreemapBuilder()
        node = builder.build(str(simple_tree))
        d = node.to_dict()
        restored = TreeNode.from_dict(d)
        for orig, rest in zip(node.children, restored.children):
            assert orig.name == rest.name
            assert orig.hash == rest.hash


# ---------------------------------------------------------------------------
# Unit tests — find_duplicate_nodes
# ---------------------------------------------------------------------------

class TestFindDuplicateNodes:

    def test_finds_duplicates(self, duplicate_tree):
        root, copy1, copy2 = duplicate_tree
        builder = TreemapBuilder()
        node1 = builder.build(str(copy1))
        node2 = builder.build(str(copy2))
        dup_map = find_duplicate_nodes([("copy1", node1), ("copy2", node2)])
        assert len(dup_map) > 0

    def test_no_false_positives(self, simple_tree):
        builder = TreemapBuilder()
        node = builder.build(str(simple_tree))
        # Single tree — no cross-tree duplicates expected at root level
        dup_map = find_duplicate_nodes([("only", node)])
        # All entries in dup_map must have len > 1; with one tree that's impossible
        assert all(len(v) > 1 for v in dup_map.values())

    def test_root_hash_match_detected(self, duplicate_tree):
        root, copy1, copy2 = duplicate_tree
        builder = TreemapBuilder()
        node1 = builder.build(str(copy1))
        node2 = builder.build(str(copy2))
        dup_map = find_duplicate_nodes([("copy1", node1), ("copy2", node2)])
        all_hashes = set(dup_map.keys())
        assert node1.hash in all_hashes


# ---------------------------------------------------------------------------
# Unit tests — persistence
# ---------------------------------------------------------------------------

class TestPersistence:

    def test_save_and_load(self, simple_tree, tmp_path):
        store = tmp_path / "store"
        builder = TreemapBuilder()
        node = builder.build(str(simple_tree))
        dest = save_treemap(node, "TestDrive", str(simple_tree), slow=False, store_dir=store)
        assert dest.exists()

        meta, loaded = load_treemap("TestDrive", store_dir=store)
        assert meta["label"] == "TestDrive"
        assert loaded.hash == node.hash
        assert loaded.size == node.size

    def test_load_nonexistent_raises(self, tmp_path):
        store = tmp_path / "store"
        with pytest.raises(FileNotFoundError):
            load_treemap("NoSuchLabel", store_dir=store)

    def test_list_saved_treemaps(self, simple_tree, tmp_path):
        store = tmp_path / "store"
        builder = TreemapBuilder()
        node = builder.build(str(simple_tree))
        save_treemap(node, "DriveA", str(simple_tree), slow=False, store_dir=store)
        save_treemap(node, "DriveB", str(simple_tree), slow=True, store_dir=store)
        maps = list_saved_treemaps(store_dir=store)
        labels = {m["label"] for m in maps}
        assert "DriveA" in labels
        assert "DriveB" in labels

    def test_list_empty_store(self, tmp_path):
        store = tmp_path / "empty_store"
        maps = list_saved_treemaps(store_dir=store)
        assert maps == []

    def test_label_with_special_chars_saved(self, simple_tree, tmp_path):
        store = tmp_path / "store"
        builder = TreemapBuilder()
        node = builder.build(str(simple_tree))
        save_treemap(node, "My Drive/2024", str(simple_tree), slow=False, store_dir=store)
        maps = list_saved_treemaps(store_dir=store)
        assert len(maps) == 1


# ---------------------------------------------------------------------------
# Unit tests — printable label
# ---------------------------------------------------------------------------

class TestPrintableLabel:

    def test_label_contains_required_fields(self, simple_tree):
        builder = TreemapBuilder()
        node = builder.build(str(simple_tree))
        text = generate_printable_label(
            node, "TestDrive", str(simple_tree),
            "2026-02-18T00:00:00", slow=False, max_depth=3
        )
        assert "TestDrive" in text
        assert str(simple_tree) in text
        assert "2026-02-18" in text
        assert "metadata" in text  # fast mode description

    def test_slow_label_mentions_sha256(self, simple_tree):
        builder = TreemapBuilder(slow=True)
        node = builder.build(str(simple_tree))
        text = generate_printable_label(
            node, "SlowDrive", str(simple_tree),
            "2026-02-18T00:00:00", slow=True, max_depth=3
        )
        assert "SHA-256" in text

    def test_depth_limits_output(self, tmp_path):
        # Build a 5-level deep tree
        d = tmp_path
        for level in range(5):
            d = d / f"level{level}"
            d.mkdir()
            (d / "file.txt").write_bytes(b"x")
        builder = TreemapBuilder()
        node = builder.build(str(tmp_path))
        text3 = generate_printable_label(node, "L", str(tmp_path), "now", False, max_depth=3)
        text1 = generate_printable_label(node, "L", str(tmp_path), "now", False, max_depth=1)
        assert len(text3) >= len(text1)

    def test_label_has_separator_lines(self, simple_tree):
        builder = TreemapBuilder()
        node = builder.build(str(simple_tree))
        text = generate_printable_label(node, "X", str(simple_tree), "now", False)
        assert "=" * 20 in text


# ---------------------------------------------------------------------------
# Unit tests — helpers
# ---------------------------------------------------------------------------

class TestHelpers:

    def test_format_size_bytes(self):
        assert "B" in _format_size(500)

    def test_format_size_kb(self):
        assert "KB" in _format_size(2048)

    def test_format_size_mb(self):
        assert "MB" in _format_size(2 * 1024 * 1024)

    def test_hash_from_parts_deterministic(self):
        parts = [("a", 1, 100), ("b", 2, 200)]
        assert _hash_from_parts(parts) == _hash_from_parts(parts)

    def test_hash_from_parts_different_inputs(self):
        assert _hash_from_parts([("a",)]) != _hash_from_parts([("b",)])


# ---------------------------------------------------------------------------
# Unit tests — QR code label
# ---------------------------------------------------------------------------

class TestQRLabel:

    def test_qr_payload_is_valid_json(self, simple_tree):
        builder = TreemapBuilder()
        node = builder.build(str(simple_tree))
        payload = _qr_payload(node, "TestDrive", str(simple_tree), "2026-02-20T00:00:00", slow=False)
        import json
        data = json.loads(payload)
        assert data["label"] == "TestDrive"
        assert "children" in data
        assert isinstance(data["children"], list)

    def test_qr_payload_includes_first_level_children(self, simple_tree):
        builder = TreemapBuilder()
        node = builder.build(str(simple_tree))
        payload = _qr_payload(node, "TestDrive", str(simple_tree), "2026-02-20T00:00:00", slow=False)
        import json
        data = json.loads(payload)
        # simple_tree has subdir1 and subdir2
        assert len(data["children"]) >= 2

    def test_qr_label_contains_qr_header(self, simple_tree):
        builder = TreemapBuilder()
        node = builder.build(str(simple_tree))
        text = generate_qr_label(node, "TestDrive", str(simple_tree), "2026-02-20T00:00:00", slow=False)
        assert "DRIVE LABEL (with QR)" in text
        assert "Scan this QR code" in text

    def test_qr_label_contains_metadata(self, simple_tree):
        builder = TreemapBuilder()
        node = builder.build(str(simple_tree))
        text = generate_qr_label(node, "TestDrive", str(simple_tree), "2026-02-20T00:00:00", slow=False)
        assert "TestDrive" in text
        assert str(simple_tree) in text
        assert "2026-02-20" in text

    def test_qr_image_creates_png_file(self, simple_tree, tmp_path):
        builder = TreemapBuilder()
        node = builder.build(str(simple_tree))
        output_path = tmp_path / "test_qr.png"
        generate_qr_image(
            node, "TestDrive", str(simple_tree), "2026-02-20T00:00:00", slow=False,
            output_path=str(output_path), size_inches=1.0, dpi=300
        )
        assert output_path.exists()
        assert output_path.stat().st_size > 0

    def test_qr_image_has_correct_dimensions(self, simple_tree, tmp_path):
        from PIL import Image
        builder = TreemapBuilder()
        node = builder.build(str(simple_tree))
        output_path = tmp_path / "test_qr_300.png"
        generate_qr_image(
            node, "TestDrive", str(simple_tree), "2026-02-20T00:00:00", slow=False,
            output_path=str(output_path), size_inches=1.0, dpi=300
        )
        img = Image.open(output_path)
        assert img.size == (300, 300)  # 1 inch at 300 DPI
