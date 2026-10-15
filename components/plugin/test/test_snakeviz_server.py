#  Copyright (c) 2026 profiler-qgis-plugin contributors.
#
#
#  This file is part of profiler-qgis-plugin.
#
#  profiler-qgis-plugin is free software: you can redistribute it and/or
#  modify it under the terms of the GNU General Public License as published
#  by the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  profiler-qgis-plugin is distributed in the hope that it will be
#  useful, but WITHOUT ANY WARRANTY; without even the implied warranty
#  of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with profiler-qgis-plugin. If not, see <https://www.gnu.org/licenses/>.
import cProfile
import json
import re
import urllib.request
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.error import HTTPError, URLError
from urllib.parse import unquote

import pytest

from profiler_plugin.snakeviz_server import (
    SnakevizServer,
    path_from_url_path,
    url_path_for,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator


@pytest.fixture
def server() -> "Iterator[SnakevizServer]":
    server = SnakevizServer()
    yield server
    server.stop()


@pytest.fixture
def profile_path(tmp_path: Path) -> Path:
    return _write_profile(tmp_path / "test profile.prof", sorted)


def _write_profile(path: Path, function: "Callable[..., object]") -> Path:
    profile = cProfile.Profile()
    profile.runcall(function, range(100))
    profile.dump_stats(path)
    return path


def _base_url(url: str) -> str:
    return url.split("/snakeviz/", maxsplit=1)[0]


def _get(url: str, host: str | None = None) -> tuple[int, str]:
    request = urllib.request.Request(url)
    if host is not None:
        request.add_header("Host", host)
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, response.read().decode()
    except HTTPError as e:
        return e.code, ""


def test_url_for_should_start_server_and_serve_profile(
    server: SnakevizServer, profile_path: Path
) -> None:
    # Act
    url = server.url_for(profile_path)

    # Assert
    assert server.is_running()
    assert url.endswith(f"/snakeviz{profile_path.as_posix().replace(' ', '%20')}")
    status, body = _get(url)
    assert status == 200
    assert "<title>test profile</title>" in body
    assert "sorted" in body


def test_server_should_serve_snakeviz_static_files(
    server: SnakevizServer, profile_path: Path
) -> None:
    base_url = _base_url(server.url_for(profile_path))

    for path in ("snakeviz.js", "snakeviz.css", "vendor/d3.v3.min.js"):
        status, _ = _get(f"{base_url}/static/{path}")
        assert status == 200, path


def test_url_path_should_round_trip_to_path(tmp_path: Path) -> None:
    path = tmp_path / "dir with space" / "a#b.prof"

    url_path = url_path_for(path)

    assert url_path.startswith("/snakeviz/")
    # tornado passes the path to the handler URL-decoded
    decoded = unquote(url_path.removeprefix("/snakeviz/"))
    assert path_from_url_path(decoded) == path


def test_editing_url_path_should_open_another_profile(
    server: SnakevizServer, profile_path: Path, tmp_path: Path
) -> None:
    # Arrange
    other_dir = tmp_path / "other"
    other_dir.mkdir()
    other_path = _write_profile(other_dir / "other.prof", max)
    base_url = _base_url(server.url_for(profile_path))

    # Act
    status, body = _get(base_url + url_path_for(other_path))

    # Assert
    assert status == 200
    assert "<title>other</title>" in body


@pytest.mark.parametrize(
    ("file_name", "content"),
    [
        ("notes.txt", "not a profile"),
        ("invalid.prof", "not a profile"),
    ],
)
def test_server_should_serve_only_valid_profile_files(
    server: SnakevizServer,
    profile_path: Path,
    tmp_path: Path,
    file_name: str,
    content: str,
) -> None:
    file_path = tmp_path / file_name
    file_path.write_text(content)
    base_url = _base_url(server.url_for(profile_path))

    status, _ = _get(base_url + url_path_for(file_path))

    assert status == 404


def test_server_should_list_profiles_and_subdirectories(
    server: SnakevizServer, profile_path: Path, tmp_path: Path
) -> None:
    # Arrange
    (tmp_path / "subdir").mkdir()
    (tmp_path / "notes.txt").write_text("not a profile")
    _write_profile(tmp_path / ".hidden.prof", sorted)
    base_url = _base_url(server.url_for(profile_path))

    # Act
    status, body = _get(base_url + url_path_for(tmp_path))

    # Assert
    assert status == 200
    match = re.search(r"var dir_entries = (.*);", body)
    assert match is not None
    entries = {name: link for [[name, link]] in json.loads(match.group(1))}
    assert entries == {
        "..": url_path_for(tmp_path.parent),
        "subdir/": url_path_for(tmp_path / "subdir"),
        "test profile.prof": url_path_for(profile_path),
    }


def test_server_should_reject_other_hosts(
    server: SnakevizServer, profile_path: Path
) -> None:
    url = server.url_for(profile_path)

    status, _ = _get(url, host="attacker.example")

    assert status == 404


def test_server_should_not_serve_deleted_profile(
    server: SnakevizServer, profile_path: Path
) -> None:
    url = server.url_for(profile_path)
    profile_path.unlink()

    status, _ = _get(url)

    assert status == 404


def test_stop_should_stop_server(server: SnakevizServer, profile_path: Path) -> None:
    url = server.url_for(profile_path)

    # Act
    server.stop()

    # Assert
    assert not server.is_running()
    with pytest.raises(URLError):
        urllib.request.urlopen(url, timeout=5)


def test_server_should_restart_after_stop(
    server: SnakevizServer, profile_path: Path
) -> None:
    server.url_for(profile_path)
    server.stop()

    # Act
    url = server.url_for(profile_path)

    # Assert
    assert server.is_running()
    assert _get(url)[0] == 200
