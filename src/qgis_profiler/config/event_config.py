#  Copyright (c) 2025 profiler-qgis-plugin contributors.
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
import enum
import logging
from abc import ABC, abstractmethod
from typing import (
    TYPE_CHECKING,
    Callable,
    NamedTuple,
    Optional,
    Protocol,
    Union,
    cast,
)

from qgis.PyQt import QtWidgets
from qgis.PyQt.QtCore import QEvent, QObject, QPoint, Qt, QTimer
from qgis.PyQt.QtGui import QMouseEvent
from qgis.utils import iface as iface_

if TYPE_CHECKING:
    from qgis.gui import QgisInterface

iface = cast("QgisInterface", iface_)

LOGGER = logging.getLogger(__name__)


_mouse_left_button_release = QMouseEvent(
    QEvent.MouseButtonRelease, QPoint(), Qt.LeftButton, Qt.NoButton, Qt.NoModifier
)

_mouse_middle_button_release = QMouseEvent(
    QEvent.MouseButtonRelease, QPoint(), Qt.MiddleButton, Qt.NoButton, Qt.NoModifier
)

_mouse_right_button_release = QMouseEvent(
    QEvent.MouseButtonRelease, QPoint(), Qt.RightButton, Qt.NoButton, Qt.NoModifier
)


def is_object_map_canvas(obj: QObject) -> bool:
    return obj == iface.mapCanvas().viewport()


class EventResponse(enum.Enum):
    START_PROFILING = enum.auto()
    STOP_PROFILING = enum.auto()
    STOP_PROFILING_DELAYED = enum.auto()
    START_AND_STOP_DELAYED = enum.auto()


class CustomEventFilter(NamedTuple):
    event: Union[QEvent, QEvent.Type]
    object_filter: Optional[Callable[[QObject], bool]] = None
    stop_after_responsive: bool = False

    def matches(self, event: QEvent, obj: QObject) -> bool:
        if not self._event_matches(event):
            return False

        return self.object_filter is None or self.object_filter(obj)

    def _event_matches(self, event: QEvent) -> bool:
        if isinstance(self.event, QEvent):
            if event.type() != self.event.type():
                return False

            if isinstance(event, QMouseEvent):  # noqa: SIM102
                if event.button() == cast("QMouseEvent", self.event).button():
                    # TODO: add support for buttons and modifiers
                    return True
            return False

        return event.type() == self.event


class CustomEventConfig(Protocol):
    class_name: str

    @property
    def name(self) -> str: ...

    def activate(self) -> None:
        """Activate the custom config when starting recording."""
        ...

    def matches(self, event: QEvent, obj: QObject) -> Optional[EventResponse]:
        """Check what to do with the event"""
        ...


class MapToolConfig(ABC):
    """
    Config for QGIS map tools.
    Implements the protocol CustomEventConfig.
    """

    def __init__(self, class_name: str, profile_name: Optional[str] = None) -> None:
        self.class_name = class_name
        self.profile_name = profile_name or class_name

    @property
    def name(self) -> str:
        return self.profile_name or self.class_name

    @abstractmethod
    def activate(self) -> None:
        pass

    @abstractmethod
    def matches(self, event: QEvent, obj: QObject) -> Optional[EventResponse]:
        pass


class SimpleMapToolConfig(MapToolConfig):
    """
    Measures the time between two events.
    """

    def __init__(
        self,
        class_name: str,
        start_event_filter: CustomEventFilter,
        stop_event_filter: CustomEventFilter,
        profile_name: Optional[str] = None,
    ) -> None:
        super().__init__(class_name, profile_name)
        self.start_event_filter = start_event_filter
        self.stop_event_filter = stop_event_filter
        self._profiling_started = False

    def activate(self) -> None:
        self._profiling_started = False

    def matches(self, event: QEvent, obj: QObject) -> Optional[EventResponse]:
        if not self._profiling_started and self.start_event_filter.matches(event, obj):
            self._profiling_started = True
            return EventResponse.START_PROFILING
        if self._profiling_started and self.stop_event_filter.matches(event, obj):
            self._profiling_started = False
            if self.stop_event_filter.stop_after_responsive:
                return EventResponse.STOP_PROFILING_DELAYED
            return EventResponse.STOP_PROFILING
        return None


class SimpleMapToolClickConfig(MapToolConfig):
    """
    Measures the time it takes for the UI to become
    responsive after a click on a canvas
    """

    def __init__(
        self,
        class_name: str,
        event: Optional[CustomEventFilter] = None,
        profile_name: Optional[str] = None,
    ) -> None:
        super().__init__(class_name, profile_name)
        self.event = event or CustomEventFilter(
            event=_mouse_left_button_release,
            object_filter=is_object_map_canvas,
        )

    def activate(self) -> None:
        pass

    def matches(self, event: QEvent, obj: QObject) -> Optional[EventResponse]:
        if self.event.matches(event, obj):
            return EventResponse.START_AND_STOP_DELAYED
        return None


class AdvancedDigitizingMapToolClickConfig(SimpleMapToolClickConfig):
    def __init__(
        self,
        class_name: str,
        event: Optional[CustomEventFilter] = None,
        profile_name: Optional[str] = None,
    ) -> None:
        super().__init__(class_name, event, profile_name)
        self.initial_canvas_scene_item_count = 0

    def activate(self) -> None:
        def _set_initial_count() -> None:
            self.initial_canvas_scene_item_count = len(
                iface.mapCanvas().scene().items()
            )

        # Wait a bit before setting the initial rubberband count
        # to avoid false positives because the map canvas
        # is not yet fully initialized when this function is called.
        QTimer.singleShot(100, _set_initial_count)

    def matches(self, event: QEvent, obj: QObject) -> Optional[EventResponse]:
        if (
            self.event.matches(event, obj)
            and len(iface.mapCanvas().scene().items())
            > self.initial_canvas_scene_item_count
        ):
            return EventResponse.START_AND_STOP_DELAYED
        return None


DEFAULT_MAP_TOOLS_CONFIG: dict[str, CustomEventConfig] = {
    config.class_name: config
    for config in [
        # Measures the time it takes to end digitizing and QGIS
        # to show the feature action dialog in a responsive state
        SimpleMapToolConfig(
            class_name="QgsMapToolDigitizeFeature",
            start_event_filter=CustomEventFilter(event=_mouse_right_button_release),
            stop_event_filter=CustomEventFilter(
                event=QEvent.Show,
                object_filter=lambda obj: (
                    isinstance(obj, QtWidgets.QDialog)
                    and obj.objectName().startswith("featureactiondlg")
                ),
                stop_after_responsive=True,
            ),
        ),
        SimpleMapToolClickConfig(
            class_name="QgsMapToolPan",
        ),
        SimpleMapToolClickConfig(
            class_name="QgsMapToolZoom",
        ),
        SimpleMapToolClickConfig(
            class_name="QgsMapToolIdentify",
        ),
        AdvancedDigitizingMapToolClickConfig(
            class_name="QgsMapToolAdvancedDigitizing",
            profile_name="QgsMapToolAdvancedDigitizing (vertex tool, etc.)",
        ),
    ]
}

# These functionalities are always active with every map tool
GENERAL_MAP_TOOL_FUNCTIONALITIES = [
    SimpleMapToolClickConfig(
        class_name="QgsMapToolPan",
        event=CustomEventFilter(
            event=_mouse_middle_button_release,
            object_filter=is_object_map_canvas,
        ),
    ),
    SimpleMapToolClickConfig(
        class_name="QgsMapToolZoom",
        event=CustomEventFilter(
            event=QEvent.Wheel,
            object_filter=is_object_map_canvas,
        ),
    ),
]
