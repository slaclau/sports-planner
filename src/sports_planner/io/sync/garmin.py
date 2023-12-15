import datetime
import json
import logging
import os
import zipfile
from pathlib import Path

import garth
import numpy as np
import pandas as pd
from garth.exc import GarthException

from sports_planner.io.garmin.workouts import get_all_workouts, get_scheduled_workout
from sports_planner.io.sync.base import SyncProvider
from sports_planner.utils.logging import info_time


class Garmin(SyncProvider):
    def __init__(self, email, password=None):
        self.email = email
        if password is not None:
            garth.login(email, password)
            garth.save(f"~/sports-planner/{email}")
        else:
            try:
                garth.resume(f"~/sports-planner/{email}")
            except FileNotFoundError:
                raise LoginException
        try:
            garth.client.username
        except GarthException:
            raise LoginException

    def sync(self):
        """Synchronize downloaded information with Garmin connect."""
        activities = self.get_activities(0, 2000)
        path = Path.home() / "sports-planner" / self.email / "activities"
        downloaded = [os.path.splitext(filename)[0] for filename in os.listdir(path)]

        ids = []
        for activity in activities:
            ids.append(str(activity["activityId"]))
            activity["source"] = "garmin"
            json_path = path / f"{activity['activityId']}.json"
            if Path.is_file(json_path):
                continue
            with open(
                json_path,
                "w",
            ) as f:
                json.dump(activity, f)

        ids = list(set(ids) - set(downloaded))
        num = len(ids)
        i = 0
        for activity in ids:
            i += 1
            self.download_activity(activity)
            logging.info(f"({i} of {num})")

        logging.info("Synced")

    def get_activities(self, start, limit):
        """Return available activities."""

        url = "/activitylist-service/activities/search/activities"

        params = {"start": str(start), "limit": str(limit)}

        return garth.connectapi(url, params=params)

    def download_activity(self, activityId):
        """Download activity"""

        url = f"/download-service/files/activity/{activityId}"
        file = garth.download(url)
        path = Path.home() / "sports-planner" / self.email / "activities"
        zip_path = path / f"{activityId}.zip"
        json_path = path / f"{activityId}.json"
        with open(zip_path, "wb+") as f:
            f.write(file)
        logging.info(f"Downloaded {activityId}.zip")

        with zipfile.ZipFile(path / f"{activityId}.zip", "r") as zip_ref:
            activity_file = zip_ref.namelist()[0]
            with open(json_path, "r") as f:
                details = json.load(f)
                details["source_file"] = activity_file
            with open(json_path, "w") as f:
                json.dump(details, f)
            zip_ref.extractall(path)

        logging.info(f"Extracted {activity_file}")

    @info_time
    def get_schedule(self, start, end):
        path = Path.home() / "sports-planner" / self.email / "schedule" / "garmin.json"

        try:
            with open(path, "r") as f:
                schedule = pd.read_json(f)
                last_scheduled = schedule["date"].iloc[-1]
                logging.debug(f"Retrieved stored schedule up to {last_scheduled}")
        except FileNotFoundError:
            schedule = pd.DataFrame()
            last_scheduled = start
        except ValueError:
            schedule = pd.DataFrame()
            last_scheduled = start

        new_schedule = get_all_workouts(last_scheduled, end)

        schedule = pd.concat([schedule, new_schedule], ignore_index=True)
        schedule.drop_duplicates(subset="scheduleId", inplace=True)

        temp_schedule = schedule[schedule["date"].dt.date < datetime.date.today()]

        with open(path, "w+") as f:
            temp_schedule.to_json(f)

        return schedule

    @info_time
    def get_workouts(self, start, end):
        workouts = self.get_schedule(start, end)
        path = Path.home() / "sports-planner" / self.email / "workouts" / "garmin.json"

        try:
            with open(path, "r") as f:
                schedule_dict = json.load(f)
        except FileNotFoundError:
            schedule_dict = {}

        def get_workout(row):
            scheduleId = row["scheduleId"]
            if np.isnan(scheduleId):
                return
            try:
                scheduledWorkout = schedule_dict[str(int(scheduleId))]
                logging.debug(f"Loaded workout {int(scheduleId)} from schedule")
            except KeyError:
                scheduledWorkout = get_scheduled_workout(scheduleId)["workout"]
                logging.debug(f"Loaded workout {int(scheduleId)} from garmin connect")
            return scheduledWorkout

        workouts["workout"] = workouts.apply(get_workout, axis=1)

        def get_workout_id(workout):
            if workout is not None:
                try:
                    return workout["workoutId"]
                except KeyError:
                    return None

        workouts["workoutId"] = workouts["workout"].apply(get_workout_id)

        temp_workouts = workouts[workouts["date"].dt.date < datetime.date.today()]

        schedule_dict = dict(
            zip(temp_workouts["scheduleId"].astype(int), temp_workouts["workout"])
        )

        with open(path, "w+") as f:
            json.dump(schedule_dict, f)

        self.workouts = workouts
        self.save_workout_jsons()

    @info_time
    def save_workout_jsons(self):
        path = Path.home() / "sports-planner" / self.email / "workouts"
        for workout in self.workouts["workout"]:
            if workout is not None:
                id = workout["workoutId"]
                workout_path = path / f"{id}.json"
                with open(workout_path, "w+") as f:
                    workout_dict = {
                        "activityName": workout["workoutName"],
                        "source": "garmin_workout",
                        "source_file": None,
                    }
                    json.dump(workout_dict, f)


class LoginException(Exception):
    """Not logged in"""
