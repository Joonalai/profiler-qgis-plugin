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

import pytest

from qgis_profiler.meters.recovery_measurer import RecoveryMeasurer


@pytest.fixture
def recovery_measurer() -> RecoveryMeasurer:
    meter = RecoveryMeasurer.get()
    meter.reset_parameters()
    return meter


def test_recovery_measurer_should_measure_recovery(recovery_measurer: RecoveryMeasurer):
    assert recovery_measurer.measure() == pytest.approx(0.1, abs=1e-1)


def test_recovery_measurer_should_measure_recovery_if_disabled(
    recovery_measurer: RecoveryMeasurer,
):
    recovery_measurer.enabled = False
    assert not recovery_measurer.measure()
