from abc import ABC
import numpy as np
import pandas as pd

from sports_planner.metrics.base import ActivityMetric


class TimerTime(ActivityMetric):
    name = "Total timer time"

    def applicable(self):
        return True

    def compute(self):
        try:
            return self.activity.details["total_timer_time"]
        except AttributeError:
            pass
        return (
            self.activity.records_df.index[-1] - self.activity.records_df.index[0]
        ).total_seconds()


class Sport(ActivityMetric):
    name = "Sport"

    def applicable(self):
        if (
            "sports" in self.activity.summaries
            and len(self.activity.summaries["sports"].index) == 1
        ):
            return True
        elif (
            "sport" in self.activity.records_df.columns
            and len(self.activity.records_df["sport"].unique()) == 1
        ):
            return True
        return False

    def compute(self):
        if "sports" in self.activity.summaries:
            sports = self.activity.summaries["sports"]
            assert len(sports.index) == 1
            return {
                "sport": sports["sport"].iloc[0],
                "sub_sport": sports["sub_sport"].iloc[0],
                "name": sports["name"].iloc[0],
            }
        elif "sport" in self.activity.records_df.columns:
            assert len(self.activity.records_df["sport"].unique()) == 1
            return {"sport": self.activity.records_df["sport"].unique()[0]}


class ActivityDate(ActivityMetric):
    name = "date"

    def applicable(self):
        return True

    def compute(self):
        details = self.activity.details
        return details


class AveragePower(ActivityMetric):
    name = "Average power"

    def applicable(self):
        if "power" in self.df.columns:
            return True
        return False

    def compute(self):
        return self.df["power"].replace(0, np.nan).mean(skipna=True)


class AverageHR(ActivityMetric):
    name = "Average heart rate"

    def applicable(self):
        if "heartrate" in self.df.columns:
            return True
        return False

    def compute(self):
        return self.df["heartrate"].mean()


class RunningMetric(ActivityMetric, ABC):
    deps = [Sport]

    def applicable(self):
        try:
            sport = self.get_metric(Sport)["sport"]
        except KeyError:
            return False
        if sport == "running":
            return True
        return False


class CyclingMetric(ActivityMetric, ABC):
    deps = [Sport]

    def applicable(self):
        sport = self.get_metric(Sport)["sport"]
        if sport == "cycling":
            return True
        return False
