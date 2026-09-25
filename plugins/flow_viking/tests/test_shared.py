"""flow_viking 共享层测试：路径、虚拟文件系统、分层与检索。"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _shared import (  # noqa: E402
    L0,
    L1,
    L2,
    VirtualFS,
    find,
    grep,
    join,
    normalize,
    parse,
    resolve,
)
from _shared.errors import ConflictError, NotFoundError, PathError  # noqa: E402
from _shared.layers import demote  # noqa: E402
from _shared.store import load, save  # noqa: E402


def test_path_parse_and_normalise() -> None:
    assert normalize("/projects/acme") == "viking://projects/acme"
    assert normalize("viking://projects/acme/") == "viking://projects/acme"
    assert parse("viking://").segments == ()
    assert parse("viking://").is_root

def test_path_rejects_traversal_and_empty_segments() -> None:
    # 尾斜杠是合法的，会被归一化掉。
    assert normalize("viking://a/") == "viking://a"
    for bad in ("viking://../escape", "viking://a//b", "viking://a/b/c/../../d"):
        try:
            normalize(bad)
        except PathError:
            continue
        raise AssertionError(f"accepted invalid path {bad!r}")

def test_join_and_resolve_stay_inside_the_root() -> None:
    assert join("viking://projects", "acme", "readme") == "viking://projects/acme/readme"
    assert resolve("viking://memory", "user") == "viking://memory/user"
    assert resolve("viking://memory", "viking://skills/x") == "viking://skills/x"

def test_relative_to_rejects_outside_paths() -> None:
    base = parse("viking://projects/acme")
    try:
        parse("viking://projects").relative_to(base)
    except PathError:
        return
    raise AssertionError("relative_to accepted an outside path")

def test_mkdir_creates_intermediate_directories() -> None:
    fs = VirtualFS()
    fs.mkdir("viking://memory/sessions/2026")
    assert fs.require_dir("viking://memory/sessions/2026").names() == []

def test_write_generates_summaries() -> None:
    fs = VirtualFS()
    node = fs.write("viking://projects/acme/readme", "Acme deploy pipeline.\nStage then prod.")
    assert node.summary == "Acme deploy pipeline."
    assert "Stage then prod." in node.abstract

def test_writing_over_a_directory_is_a_conflict() -> None:
    fs = VirtualFS()
    fs.mkdir("viking://projects/acme")
    try:
        fs.write("viking://projects/acme", "x")
    except ConflictError:
        return
    raise AssertionError("overwriting a directory was allowed")

def test_reading_a_missing_path_is_not_found() -> None:
    fs = VirtualFS()
    try:
        fs.require("viking://nope")
    except NotFoundError:
        return
    raise AssertionError("reading a missing path did not raise")

def test_root_cannot_be_removed() -> None:
    fs = VirtualFS()
    try:
        fs.remove("viking://")
    except ConflictError:
        return
    raise AssertionError("removing the root was allowed")

def test_layers_return_increasing_detail() -> None:
    fs = VirtualFS()
    fs.write("viking://a", "first line\nsecond line\nthird line")
    node = fs.require_file("viking://a")
    assert node.layer(L0).summary == "first line"
    assert "second line" in node.layer(L1).summary
    assert "third line" in node.layer(L2).content

def test_demote_respects_the_layer_limits() -> None:
    long_line = "x" * 900
    assert len(demote(long_line, target_layer=L0)) == 120
    assert len(demote(long_line, target_layer=L1)) == 600

def test_search_scopes_and_ranks() -> None:
    fs = VirtualFS()
    fs.write("viking://projects/acme/readme", "Acme deploy pipeline runs nightly.")
    fs.write("viking://memory/user", "User prefers short answers in Chinese.")
    hits = find(fs, "deploy pipeline", scope="viking://projects")
    assert [hit.path for hit in hits] == ["viking://projects/acme/readme"]

    scoped = find(fs, "answers", scope="viking://memory")
    assert [hit.path for hit in scoped] == ["viking://memory/user"]

    assert find(fs, "answers", scope="viking://projects") == []

def test_grep_find_matching_lines() -> None:
    fs = VirtualFS()
    fs.write("viking://memory/user", "User prefers short answers in Chinese.")
    matches = grep(fs, "Chinese")
    assert matches and matches[0]["line"] == 1

def test_tree_respects_depth() -> None:
    fs = VirtualFS()
    fs.mkdir("viking://a/b/c/d")
    shallow = fs.tree("viking://", max_depth=1)
    deep = fs.tree("viking://", max_depth=4)
    assert len(deep) > len(shallow)

def test_tree_degrades_to_a_single_file() -> None:
    fs = VirtualFS()
    fs.write("viking://a", "x")
    assert [entry["path"] for entry in fs.tree("viking://a")] == ["viking://a"]

def test_round_trip_through_disk() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        fs = VirtualFS()
        fs.write("viking://memory/user", "Prefers short answers.", tags=("user",))
        fs.mkdir("viking://memory/sessions")
        assert save(fs, Path(tmp))

        restored = load(Path(tmp))
        assert [file.path for file in restored.all_files()] == ["viking://memory/user"]
        assert restored.require_file("viking://memory/user").tags == ("user",)
        assert restored.require_dir("viking://memory/sessions").names() == []

def test_load_survives_a_corrupt_file() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "viking.json").write_text("{not json", encoding="utf-8")
        assert load(Path(tmp)).all_files() == []
