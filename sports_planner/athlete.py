import datetime
import logging
import os
from pathlib import Path

import garth
import numpy as np
import pandas as pd

from sports_planner.io.files import Activity
from sports_planner.io.garmin.workouts import (get_all_workouts,
                                               get_scheduled_workout)
from sports_planner.metrics.calculate import MetricsCalculator
from sports_planner.utils.logging import debug_time, info_time


class Athlete:
    activities: pd.DataFrame

    def __init__(self, email, callback_func=None, sync_providers=None):
        self.email = email
        self.callback_func = callback_func
        self.activities_dir = Path.home() / "sports-planner" / self.email / "activities"
        self.workouts_dir = Path.home() / "sports-planner" / self.email / "workouts"
        self.sync_providers = sync_providers if sync_providers is not None else []

        self._load_activities()

        self.activities["date"] = pd.to_datetime(self.activities.index).date
        if self.callback_func is not None:
            self.callback_func("text", "Grouping activities")
        self.days = pd.DataFrame()
        self.days["activities"] = (
            self.activities["activity"].groupby(self.activities["date"]).apply(list)
        )

    def get_workouts_and_seasons(self):
        if self.callback_func is not None:
            self.callback_func("text", "Loading scheduled workouts")
        self._load_workouts()

        if self.callback_func is not None:
            self.callback_func("text", "Detecting seasons")
        self.seasons = self.find_seasons()

        if self.callback_func is not None:
            self.callback_func("text", "Done")

    @info_time
    def _load_workouts(self):
        end = datetime.date.today() + datetime.timedelta(days=60)
        workouts = []
        for sync_provider in self.sync_providers:
            sync_provider.get_workouts(self.days.index[0], end)
            workouts.append(sync_provider.workouts)

        self.workouts = pd.concat(workouts)
        self.days = self.days.reindex(pd.date_range(self.days.index[0], end))
        n = len(self.days)
        i = 0

        def get_activity(workoutId):
            nonlocal i
            i += 1
            if self.callback_func is not None:
                self.callback_func("load", i, n)
            try:
                workout_path = self.workouts_dir / f"{int(workoutId)}.json"
                return [Activity(workout_path)]
            except TypeError:
                pass
            except ValueError:
                pass

        self.workouts["activities"] = self.workouts["workoutId"].apply(get_activity)
        print(self.workouts)
        self.days["workouts"] = self.workouts["activities"]
        print(self.days)

    def get_activities(self, date):
        return self.days.iloc[date, "activities"]

    @info_time
    def _load_activities(self):
        files = [
            file
            for file in os.listdir(path=self.activities_dir)
            if file.endswith(".json")
        ]
        num = len(files)
        i = 0
        activities = []
        for file in files:
            i += 1
            activity = Activity(self.activities_dir / file)
            startTimeGMT = activity.meta_details["startTimeGMT"]
            activities.append({"startTimeGMT": startTimeGMT, "activity": activity})
            if self.callback_func is not None:
                self.callback_func("load", i, num)
            logging.debug(f"Read in {file} (activity {i} of {num})")

        self.activities = pd.DataFrame(activities)
        self.activities.set_index("startTimeGMT", inplace=True)
        self.activities.sort_index(inplace=True)

    @info_time
    def aggregate_metric(self, metric, how, callback_func=None, future=False):
        i = 0
        n = len(self.days.index)

        desired_metrics = MetricsCalculator.order_deps([metric])

        @debug_time
        def get_metrics(activities):
            if not isinstance(activities, list):
                return [0]
            if not activities:
                return [0]

            nonlocal i
            i += 1
            if callback_func is not None:
                callback_func("load", i, n)
            rtn = []
            for activity in activities:
                try:
                    rtn.append(
                        MetricsCalculator(
                            activity, desired_metrics, pre_ordered=True
                        ).metrics[metric]
                    )
                except KeyError:
                    rtn.append(0)
            return rtn

        def _sum(activities):
            return sum(get_metrics(activities))

        def _max(activities):
            return max(get_metrics(activities))

        col = "workouts" if future else "activities"
        if how == "list":
            return self.days[col].apply(get_metrics)
        if how == "sum":
            return self.days[col].apply(_sum)
        if how == "max":
            return self.days[col].apply(_max)
        raise ValueError(f"Unknown 'how' parameter {how}")

    @info_time
    def find_seasons(self):
        def season_size(season):
            rtn = (season[-1] - season[0]).astype("timedelta64[D]") / np.timedelta64(
                1, "D"
            )
            return rtn

        def split(season):
            gaps = np.diff(season).astype("timedelta64[D]")
            idx = gaps.argmax()
            idx += 1
            logging.debug(f"Splitting {season[0]} - {season[-1]} at {season[idx]}")
            left = season[:idx]
            right = season[idx:]
            logging.debug(
                f"Returns {left[0]} - {left[-1]} and {right[0]} - {right[-1]}"
            )
            return left, right

        days = self.days.copy()
        days["activities"] = days["activities"].apply(
            lambda d: d if isinstance(d, list) else []
        )
        days["workouts"] = days["workouts"].apply(
            lambda d: [d] if isinstance(d, Activity) else []
        )
        days["combined"] = days["activities"] + days["workouts"]
        days = days[days["combined"].map(lambda d: len(d)) > 0]
        days = np.array(days.index)

        biggest_season = season_size(days)
        season_limit = 2 * 365
        gap_limit = 2 * 30
        seasons = []
        seasons.append(days)
        sizes = [biggest_season]
        i = 0

        while biggest_season > season_limit:
            i += 1
            logging.debug(f"Iteration {i}")
            idx = sizes.index(biggest_season)
            s = seasons[idx]
            logging.debug(f"Biggest season: {s[0]} - {s[-1]}")

            seasons.pop(idx)
            ss = split(s)
            seasons.append(ss[0])
            seasons.append(ss[1])

            sizes = [season_size(season) for season in seasons]
            biggest_season = max(sizes)

        rtn = [(season[0], season[-1]) for season in seasons]
        rtn.sort(key=lambda x: x[0])
        return rtn
