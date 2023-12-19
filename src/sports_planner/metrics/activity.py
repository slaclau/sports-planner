import types
import typing
from abc import ABC

import numpy as np
import pandas as pd
import sweat

from sports_planner.metrics.base import ActivityMetric
from sports_planner.utils import format


class TimerTime(ActivityMetric):
    name = "Total timer time"
    unit = "s"

    def applicable(self):
        return True

    def compute(self):
        try:
            return self.activity.details["total_timer_time"]
        except AttributeError:
            pass
        except TypeError:
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
    name = "Date"
    format = "%d-%m-%Y"

    def applicable(self):
        return True

    def compute(self):
        return self.activity.records_df.index[0].date()


class AverageSpeed(ActivityMetric):
    name = "Average speed"
    unit = "m/s"
    format = ".2f"

    deps = [TimerTime]

    def applicable(self):
        if "speed" in self.df.columns:
            return True
        return False

    def compute(self):
        time = self.get_metric(TimerTime)
        return self.df["distance"][-1] / time


class AveragePower(ActivityMetric):
    name = "Average power"
    unit = "W"
    format = ".0f"

    def applicable(self):
        if "power" in self.df.columns:
            return True
        return False

    def compute(self):
        return self.df["power"].replace(0, np.nan).mean(skipna=True)


class AverageHR(ActivityMetric):
    name = "Average heart rate"
    unit = "bpm"
    format = ".0f"

    def applicable(self):
        if "heartrate" in self.df.columns:
            return True
        return False

    def compute(self):
        return self.df["heartrate"].mean()


class CurveMeta(type):
    classes = {}

    @classmethod
    def __getitem__(cls, item):
        if item in cls.classes:
            return cls.classes[item]
        curve = type(
            f'Curve["{item}"]',
            (Curve,),
            {"column": item, "name": f"{item}-duration curve"},
        )
        cls.classes[item] = curve
        return curve


class Curve(ActivityMetric, metaclass=CurveMeta):
    column: str

    def applicable(self):
        return (
            self.column in self.df.columns and not self.df[self.column].isnull().any()
        )

    def compute(self):
        pc_df = self.df.sweat.mean_max(self.column, monotonic=True)
        x = pc_df.index.total_seconds()
        X = sweat.array_1d_to_2d(x)
        y = pc_df["mean_max_" + self.column]

        two_param = sweat.PowerDurationRegressor(model="2 param")
        two_param.fit(X, y)

        three_param = sweat.PowerDurationRegressor(model="3 param")
        three_param.fit(X, y)

        exponential = sweat.PowerDurationRegressor(model="exponential")
        exponential.fit(X, y)

        omni = sweat.PowerDurationRegressor(model="omni")
        omni.fit(X, y)

        data = pd.DataFrame(
            {
                "2 param": two_param.predict(X),
                "3 param": three_param.predict(X),
                "exponential": exponential.predict(X),
                "omni": omni.predict(X),
            }
        )

        return {"x": x, "y": y, "predictions": data}


class MeanMaxMeta(type):
    classes = {}

    @classmethod
    def __getitem__(cls, item):
        if item in cls.classes:
            return cls.classes[item]
        column = item[0]
        time = item[1]
        duration = format.time(time)
        mean_max = type(
            f'MeanMax["{column}", {time}]',
            (MeanMax,),
            {
                "column": column,
                "time": time,
                "deps": [Curve[column]],
                "name": f"{duration} max {column}",
            },
        )
        cls.classes[item] = mean_max
        return mean_max


class MeanMax(ActivityMetric, metaclass=MeanMaxMeta):
    column: str
    time: int

    def applicable(self):
        curve = self.get_metric(Curve[self.column])
        return max(curve["x"]) >= self.time

    def compute(self):
        curve = self.get_metric(Curve[self.column])
        return curve["y"][self.time]


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
