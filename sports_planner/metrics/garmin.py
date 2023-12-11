from abc import ABC

import numpy as np

from sports_planner.metrics.activity import RunningMetric
from sports_planner.metrics.base import ActivityMetric


class Firstbeat(ActivityMetric, ABC):
    field_name: str
    scale: float
    allow_zero: bool

    def applicable(self):
        if "unknown_messages" in self.activity.summaries:
            for unknown in self.activity.summaries["unknown_messages"]:
                if unknown["type"] == "firstbeat":
                    return True
        return False

    def compute(self):
        if "unknown_messages" in self.activity.summaries:
            for unknown in self.activity.summaries["unknown_messages"]:
                if unknown["type"] == "firstbeat":
                    rtn = unknown["record"][self.field_name] * self.scale
                    if rtn == 0 and not self.allow_zero:
                        rtn = np.nan
                    return rtn


class VO2Max(Firstbeat):
    name = "VO2Max (Garmin)"
    field_name = "unknown_7"
    scale = 3.5 / 65536
    allow_zero = False


class RunningVO2Max(RunningMetric):
    name = "Running VO2Max (Garmin)"
    deps = RunningMetric.deps + [VO2Max]

    def compute(self):
        return self.get_metric(VO2Max)
