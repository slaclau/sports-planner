import json
import logging
import pickle
from pathlib import Path

import pandas as pd
import sweat
from sports_planner.io.garmin.workouts import get_workout, to_data_frame

records_column_name_map = {"unknown_90": "performance_condition"}
message_type_map = {140: "firstbeat"}


class Activity:
    def __init__(self, path):
        self.hrv_df = None
        self.sessions_df = None
        self.laps_df = None
        self.details = None
        if isinstance(path, pd.DataFrame):
            self.load_from_df(path)
            self.cache_path = None
            return

        path = Path(path)
        name = path.name
        base_name = path.stem
        self.cache_path = path.parent / "cache" / f"{base_name}.pkl"

        if name.endswith(".json"):
            with open(path) as f:
                details = json.load(f)
                assert "source" in details
                if details["source"] == "garmin":
                    path = path.parent / details["source_file"]
                    self.cache_path = path.parent / "cache" / f"{path.stem}.pkl"
                    self.load_activity(path, self.load_from_activity_file, details)
                elif details["source"] == "garmin_workout":
                    self.load_activity(path.stem, self.load_from_connect, details)

    def cache(self):
        if self.cache_path is not None:
            logging.debug(f"Caching to {self.cache_path}")
            with open(self.cache_path, "wb") as f:
                pickle.dump(self.summaries, f)

    def load_activity(self, path, not_cached_func, details):
        try:
            with open(self.cache_path, "rb") as f:
                logging.debug(f"Retrieving {self.cache_path} from cache")
                self.summaries = pickle.load(f)
        except FileNotFoundError:
            not_cached_func(path)
            self.cache()
        except EOFError:
            not_cached_func(path)
            self.cache()

        self.records_df = self.summaries["data"]

        try:
            self.metrics = self.summaries["metrics"]
        except KeyError:
            self.metrics = {}
            self.summaries["metrics"] = self.metrics
        self.meta_details = details
        try:
            self.details = self.summaries["activity"]
            self.laps_df = self.summaries["laps"]
            self.sessions_df = self.summaries["sessions"]
            self.hrv_df = self.summaries["hrv"].to_frame()
            self.hrv_df["timestamp"] = pd.to_timedelta(
                self.hrv_df["RR interval"].cumsum(), unit="s"
            )
        except KeyError:
            pass

    def load_from_activity_file(self, path):
        summaries = read_file(
            path,
            standardize=True,
        )
        self.summaries = summaries

    def load_from_connect(self, workout_id):
        workout = get_workout(workout_id)
        df = to_data_frame(workout)
        self.load_from_df(df)
        self.meta_details["activityName"] = workout["workoutName"]

    def load_from_df(self, df):
        self.meta_details = {"activityName": "From dataframe"}
        self.summaries = {"data": df}
        return


def read_file(path, standardize=True, *args, **kwargs):
    if path.name.endswith(".fit"):
        res = sweat.read_file(
            path,
            summaries=True,
            resample=True,
            interpolate=True,
            hrv=True,
            metadata=True,
            unknown_messages=True,
            *args,
            **kwargs,
        )
    else:
        res = sweat.read_file(
            path, resample=True, interpolate=True, metadata=True, *args, **kwargs
        )
    if standardize:
        res["data"] = standardize_df(
            res["data"], column_name_map=records_column_name_map
        )
        for field in ["sessions", "laps"]:
            try:
                res[field] = standardize_df(
                    res[field],
                    fractional=False,
                    column_name_map=records_column_name_map,
                )
            except KeyError:
                pass
        try:
            unknowns = res["unknown_messages"]
            for unknown in unknowns:
                if unknown["type"] in message_type_map:
                    unknown["type"] = message_type_map[unknown["type"]]

            res["unknown_messages"] = unknowns
        except KeyError:
            pass
        return res
    return res


def standardize_df(df, enhanced=True, fractional=True, column_name_map=None):
    for column in df.columns:
        if "enhanced_" in column and enhanced:
            base = column.replace("enhanced_", "")
            if base in df.columns:
                df.drop(columns=[base], inplace=True)
            df.rename(columns={column: base}, inplace=True)

        if "fractional_" in column and fractional:
            base = column.replace("fractional_", "")
            df[base] += df[column]
            df.drop(columns=[column], inplace=True)
        df.rename(columns=column_name_map, inplace=True)

    return df
