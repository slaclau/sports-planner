import logging
from graphlib import TopologicalSorter
from time import time

import sports_planner.metrics
from sports_planner.io.files import Activity
from sports_planner.utils.logging import debug_time, info_time, logtime


class MetricsCalculator:
    def __init__(self, activity: Activity, desired_metrics, pre_ordered=False):
        self.activity = activity
        self.deps = desired_metrics if pre_ordered else self.order_deps(desired_metrics)
        self.metrics = activity.metrics
        self.compute()

    @staticmethod
    def order_deps(desired_metrics):
        required_metrics = set()
        i = 0

        while i < len(desired_metrics):
            metric = desired_metrics[i]
            required_metrics.add(metric)
            for _metric in metric.deps:
                if _metric not in desired_metrics:
                    desired_metrics.append(_metric)
            i += 1

        deps_dict = {metric: metric.deps for metric in required_metrics}
        deps = list(TopologicalSorter(deps_dict).static_order())
        return deps

    @debug_time
    def compute(self, recompute_all=False):
        # recompute_all = True
        computed = []
        retrieved = [metric.name for metric in self.metrics]
        recompute = []
        debug_string = ""
        try:
            debug_string += self.activity.meta_details["activityName"] + "\n"
        except TypeError:
            pass
        for metric in self.deps:
            try:
                metric_instance = metric(self.activity, self.metrics)
                if metric_instance.get_applicable() and (
                    metric not in self.metrics or metric in recompute or recompute_all
                ):
                    start = time()
                    self.metrics[metric] = metric_instance.compute()
                    logtime(start, f"Computing {metric.name} took")
                    computed.append(metric.name)
            except AssertionError as e:
                print(f"AssertionError: {e}")
                print(metric.name)
        if computed:
            self.activity.cache()
        debug_string += f"Retrieved {retrieved} from cache\n"
        debug_string += f"Computed and cached {computed}\n"
        logging.debug(debug_string)

    def __str__(self):
        string = f"{self.__class__.__name__}\n"
        for metric in self.metrics:
            string += f"{metric.name}: {self.metrics[metric]}\n"

        return string
