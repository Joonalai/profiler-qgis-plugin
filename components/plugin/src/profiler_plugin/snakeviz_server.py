#  Copyright (c) 2025-2026 profiler-qgis-plugin contributors.
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
"""Serve profile files with snakeviz from a background thread.

snakeviz.main is not used: importing it creates a tornado application in
debug mode, which starts tornado's autoreloader inside QGIS. Only the
templates, static files and stats helpers of snakeviz are reused.
"""

import asyncio
import json
import logging
import os
import re
import threading
from pathlib import Path
from pstats import Stats
from urllib.parse import quote

import snakeviz
from snakeviz.stats import json_stats, table_rows
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from tornado.netutil import bind_sockets
from tornado.web import Application, HTTPError, RequestHandler

LOGGER = logging.getLogger(__name__)

HOST = "127.0.0.1"
PROFILE_SUFFIX = ".prof"
SNAKEVIZ_DIR = Path(snakeviz.__file__).parent
STOP_TIMEOUT_S = 5
URL_PREFIX = "/snakeviz/"


def url_path_for(path: Path) -> str:
    """Return the readable URL path showing the file or directory.

    E.g. /home/user/a.prof is shown at /snakeviz/home/user/a.prof
    and C:/Users/a.prof on Windows at /snakeviz/C:/Users/a.prof.
    """
    return URL_PREFIX + quote(path.as_posix().removeprefix("/"), safe="/:")


def path_from_url_path(url_path: str) -> Path:
    """Return the path of the URL path without the /snakeviz/ prefix."""
    if os.name == "nt":
        # A leading slash is left only from UNC paths (//server/share)
        return Path("/" + url_path if url_path.startswith("/") else url_path)
    return Path("/" + url_path)


def _is_profile(path: Path) -> bool:
    return path.suffix.lower() == PROFILE_SUFFIX and path.is_file()


class _ProfileHandler(RequestHandler):
    """Render a profile file, or list profiles and subdirectories of a directory.

    Other files are not served to limit what the server exposes.
    """

    def get(self, url_path: str) -> None:  # ty: ignore[invalid-method-override]
        path = path_from_url_path(url_path)
        if not path.is_absolute():
            raise HTTPError(404)
        if path.is_dir():
            self._list_dir(path)
        elif _is_profile(path):
            self._show_profile(path)
        else:
            raise HTTPError(404)

    def _show_profile(self, path: Path) -> None:
        try:
            stats = Stats(str(path))
        except (OSError, TypeError, ValueError, EOFError) as e:
            raise HTTPError(404, f"Could not read {path}") from e
        self.render(
            "viz.html",
            profile_name=path.as_posix(),
            table_rows=table_rows(stats),
            callees=json_stats(stats),
        )

    def _list_dir(self, path: Path) -> None:
        try:
            children = sorted(path.iterdir())
        except OSError as e:
            raise HTTPError(404, f"Could not list {path}") from e
        entries = [
            [[f"{child.name}/" if child.is_dir() else child.name, url_path_for(child)]]
            for child in children
            if not child.name.startswith(".") and (child.is_dir() or _is_profile(child))
        ]
        if path.parent != path:
            entries.insert(0, [["..", url_path_for(path.parent)]])
        self.render(
            "dir.html", dir_name=path.as_posix(), dir_entries=json.dumps(entries)
        )


class SnakevizServer:
    """Show profile files in snakeviz served from a background thread.

    URLs contain the file path, so other profiles can be opened by editing
    the URL, and directories list their profiles. Only profile files and
    directory listings are served, and only for the loopback host to prevent
    DNS rebinding.
    """

    def __init__(self) -> None:
        """Initialize a stopped server."""
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._port: int | None = None

    def is_running(self) -> bool:
        """Return whether the server thread is running."""
        return self._thread is not None and self._thread.is_alive()

    def url_for(self, path: Path) -> str:
        """Return a URL showing the profile, starting the server if needed."""
        if not self.is_running():
            self.start()
        return f"http://{HOST}:{self._port}{url_path_for(path.resolve())}"

    def start(self) -> None:
        """Start serving on a free port of the loopback interface."""
        if self.is_running():
            return
        sockets = bind_sockets(0, HOST)
        self._port = sockets[0].getsockname()[1]
        # Selector loop works with tornado on all platforms without
        # the helper thread tornado needs for the Windows proactor loop
        self._loop = asyncio.SelectorEventLoop()
        self._thread = threading.Thread(
            target=self._serve,
            args=(self._loop, sockets),
            name="snakeviz-server",
            daemon=True,
        )
        self._thread.start()
        LOGGER.debug("Started snakeviz server on port %s", self._port)

    def stop(self) -> None:
        """Stop the server."""
        if self._loop is not None and self._thread is not None:
            self._loop.call_soon_threadsafe(self._loop.stop)
            self._thread.join(STOP_TIMEOUT_S)
            LOGGER.debug("Stopped snakeviz server")
        self._loop = None
        self._thread = None
        self._port = None

    def _serve(self, loop: asyncio.AbstractEventLoop, sockets: list) -> None:
        asyncio.set_event_loop(loop)
        io_loop = IOLoop.current()
        server = HTTPServer(self._create_application())
        server.add_sockets(sockets)
        try:
            loop.run_forever()
        finally:
            server.stop()
            io_loop.close(all_fds=True)

    def _create_application(self) -> Application:
        application = Application(
            static_path=str(SNAKEVIZ_DIR / "static"),
            template_path=str(SNAKEVIZ_DIR / "templates"),
            gzip=True,
        )
        application.add_handlers(
            re.escape(HOST),
            [(rf"{URL_PREFIX}(.*)", _ProfileHandler)],
        )
        return application
