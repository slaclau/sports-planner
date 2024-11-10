"""This module contains the :class:`Athlete` class."""

import datetime
import logging
import os
import typing
from pathlib import Path

import numpy as np
import numpy.typing
import pandas as pd

from sports_planner.io.files import Activity
from sports_planner.io.sync.base import SyncProvider
from sports_planner.metrics.base import Metric
from sports_planner.metrics.calculate import MetricsCalculator
from sports_planner.utils.logging import debug_time, info_time

logger = logging.getLogger(__name__)


class Callback(typing.Protocol):  # noqa PLR903
    """Class for type hinting callback functions."""

    def __call__(  # noqa: D102
        self, text: str, i: typing.Optional[int] = 0, n: typing.Optional[int] = 0
    ) -> None:
        pass


class Athlete:
    """This class represents an athlete.

    It provides methods to access activities and workouts as well as for
    aggregating metrics.
    """

    activities: pd.DataFrame
    workouts: pd.DataFrame
    days: pd.DataFrame
    seasons: list[tuple[datetime.date, datetime.date]]

    def __init__(
        self,
        email: str,
        callback_func: typing.Optional[Callback] = None,
        sync_providers: typing.Optional[list[SyncProvider]] = None,
    ) -> None:
        """Create an instance of the class."""
        self.email = email
        self.callback_func = callback_func
        self.activities_dir = Path.home() / "sports-planner" / self.email / "activities"
        self.workouts_dir = Path.home() / "sports-planner" / self.email / "workouts"
        self.sync_providers = sync_providers if sync_providers is not None else []

        self._load_activities()

        self.activities["date"] = pd.to_datetime(self.activities.index).date
        if self.callback_func is not None:
            self.callback_func("Grouping activities")
        self.days = pd.DataFrame()
        self.days["activities"] = (
            self.activities["activity"].groupby(self.activities["date"]).apply(list)
        )

    def get_workouts_and_seasons(self) -> None:
        """Load workouts and then split days into seasons.

        This is separated from :meth:`__init__` to avoid slowing it down
        when only activities are needed.
        """
        if self.callback_func is not None:
            self.callback_func("Loading scheduled workouts")
        self._load_workouts()

        if self.callback_func is not None:
            self.callback_func("Detecting seasons")
        self.seasons = self.find_seasons()

        if self.callback_func is not None:
            self.callback_func("Done")

    @info_time
    def _load_workouts(self) -> None:
        end = datetime.date.today() + datetime.timedelta(days=60)
        workouts = []
        for sync_provider in self.sync_providers:
            sync_provider.get_workouts(self.days.index[0], end)
            workouts.append(sync_provider.workouts)

        self.workouts = pd.concat(workouts)
        self.days = self.days.reindex(pd.date_range(self.days.index[0], end))
        n = len(self.workouts)
        i = 0

        def get_activity(row: pd.Series) -> Activity | float:  # type: ignore
            workoutId = row["workoutId"]
            nocache = row["date"].date() >= datetime.date.today()
            nonlocal i
            i += 1
            if self.callback_func is not None:
                self.callback_func(f"Loading workout {i} of {n}", i, n)
            try:
                workout_path = self.workouts_dir / f"{int(workoutId)}.json"
                return Activity(workout_path, nocache)
            # except TypeError:
            #     return np.nan
            except ValueError:
                return np.nan

        self.workouts["activities"] = self.workouts.apply(get_activity, axis=1)
        self.workouts.dropna(inplace=True)
        self.days["workouts"] = (
            self.workouts["activities"].groupby(self.workouts["date"]).apply(list)
        )

    def get_activities(self, date: datetime.date) -> list[Activity]:
        """Get a list of activities on a given date."""
        return typing.cast(
            list[Activity], self.days.iloc[date, "activities"]
        )  # type: ignore

    @info_time
    def _load_activities(self) -> None:
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
                self.callback_func(f"Loading activity {i} of {num}", i, num)
            logger.debug(f"Read in {file} (activity {i} of {num})")

        self.activities = pd.DataFrame(activities)
        self.activities.set_index("startTimeGMT", inplace=True)
        self.activities.sort_index(inplace=True)

    @info_time
    def aggregate_metric(  # type: ignore
        self,
        metric: Metric,
        how: str,
        callback_func: typing.Optional[Callback] = None,
        future: bool = False,
    ) -> pd.Series:  # type: ignore
        """Aggregate a metric across all days available."""
        i = 0
        col = "workouts" if future else "activities"
        n = len(self.days)

        desired_metrics = MetricsCalculator.order_deps([metric])
        print(desired_metrics)

        @debug_time
        def get_metrics(activities: list[Activity]) -> list:  # type: ignore
            nonlocal i
            i += 1

            if not isinstance(activities, list):
                return [0]
            if not activities:
                return [0]
            if callback_func is not None:
                callback_func(f"Getting metrics for day {i} of {n}", i, n)
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

        def _sum(activities: list[Activity]) -> float:
            return typing.cast(float, sum(get_metrics(activities)))

        def _max(activities: list[Activity]) -> float:
            return typing.cast(float, max(get_metrics(activities)))

        if how == "list":
            return self.days[col].apply(get_metrics)
        if how == "sum":
            return self.days[col].apply(_sum)
        if how == "max":
            return self.days[col].apply(_max)
        raise ValueError(f"Unknown 'how' parameter {how}")

    @info_time
    def find_seasons(self) -> list[tuple[datetime.date, datetime.date]]:
        """Separate :attr:`days` into seasons."""

        def season_size(season: numpy.typing.NDArray) -> int:  # type: ignore
            rtn = (season[-1] - season[0]).astype("timedelta64[D]") / np.timedelta64(
                1, "D"
            )
            return typing.cast(int, rtn)

        def split(season: numpy.typing.NDArray):  # type: ignore
            gaps = np.diff(season).astype("timedelta64[D]")
            idx = gaps.argmax()
            idx += 1
            logger.debug(f"Splitting {season[0]} - {season[-1]} at {season[idx]}")
            left = season[:idx]
            right = season[idx:]
            logger.debug(f"Returns {left[0]} - {left[-1]} and {right[0]} - {right[-1]}")
            return left, right

        days = self.days.copy()
        days["activities"] = days["activities"].apply(
            lambda d: d if isinstance(d, list) else []
        )
        days["workouts"] = days["workouts"].apply(
            lambda d: [d] if isinstance(d, Activity) else []
        )
        days["combined"] = days["activities"] + days["workouts"]
        days = days[days["combined"].map(len) > 0]
        days_array = np.array(days.index)

        biggest_season = season_size(days_array)
        season_limit = 2 * 365
        # gap_limit = 2 * 30
        seasons = []
        seasons.append(days_array)
        sizes = [biggest_season]
        i = 0

        while biggest_season > season_limit:
            i += 1
            logger.debug(f"Iteration {i}")
            idx = sizes.index(biggest_season)
            s = seasons[idx]
            logger.debug(f"Biggest season: {s[0]} - {s[-1]}")

            seasons.pop(idx)
            ss = split(s)
            seasons.append(ss[0])
            seasons.append(ss[1])

            sizes = [season_size(season) for season in seasons]
            biggest_season = max(sizes)

        rtn = [(season[0], season[-1]) for season in seasons]
        rtn.sort(key=lambda x: x[0])
        return rtn
