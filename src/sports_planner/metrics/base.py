from abc import abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sports_planner.io.files import Activity


class Metric:
    name: str
    description: str
    value: float
    deps: list = []
    format = ""
    unit = ""
    last_changed = None

    def __init__(self, activity: "Activity", results=None):
        self.activity = activity
        self.df = activity.records_df
        self.results = results

    @abstractmethod
    def compute(self):
        pass

    def get_metric(self, metric):
        assert metric in self.deps
        from sports_planner.metrics.activity import CurveMeta, MeanMaxMeta
        if metric.__class__ not in [CurveMeta, MeanMaxMeta]:
            return self.results[metric]
        return self.results[metric.name]

    def get_applicable(self):
        rtn = self.applicable()
        # for dep in self.deps:
        #     rtn = rtn and dep(self.activity).get_applicable()
        return rtn

    @abstractmethod
    def applicable(self):
        pass

    def add_dep(self, dep):
        self.deps.append(dep)


class ActivityMetric(Metric):
    """Metric computed for a specific activity."""
