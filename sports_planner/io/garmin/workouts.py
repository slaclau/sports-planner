import datetime
import json
import logging

import garth
import garth.exc
import pandas as pd
from dateutil import rrule
from sports_planner.utils.logging import debug_time, info_time


def get_plans():
    resp = garth.connectapi(
        "/userpreference-service/AdaptiveTrainingPlan.Calendar.Preference"
    )
    return list([temp["id"] for temp in json.loads(resp["value"])])


def get_plan_info(planId):
    return garth.connectapi(
        "/atp/athlete/plan", params=dict(athletePlanId=planId, lang="en")
    )


def get_plan_active(planId):
    info = get_plan_info(planId)
    return not info["planCompleted"]


def get_current_plan():
    plans = get_plans()
    plans.sort(reverse=True)
    for plan in plans:
        if get_plan_active(plan):
            return plan


def get_plan_workouts(planId, start, end):
    return garth.connectapi(
        "/atp/athlete/calendar",
        params=dict(
            athletePlanId=planId,
            startDate=start,
            endDate=end,
            lang="en",
        ),
    )


@debug_time
def get_scheduled_workout(scheduleWorkoutId):
    try:
        return garth.connectapi(f"/workout-service/schedule/{int(scheduleWorkoutId)}")
    except garth.exc.GarthHTTPError:
        print(f"No workout found for id {scheduleWorkoutId}")
        return None
    except ValueError:
        pass


def get_workout(workoutId):
    workoutId = int(workoutId)
    try:
        return garth.connectapi(f"/workout-service/workout/{workoutId}")
    except garth.exc.GarthHTTPError:
        print(f"No workout found for id {workoutId}")


def get_calendar_items(year, month):
    path = f"/calendar-service/year/{year}/month/{month}"
    items = garth.connectapi(path)["calendarItems"]
    return items


def get_calendar_workouts(year, month):
    items = get_calendar_items(year, month)
    workouts = [item for item in items if item["itemType"] == "workout"]
    return workouts


@info_time
def get_all_workouts(start, end):
    if isinstance(start, datetime.date):
        start = start.strftime("%Y-%m-%d")
    if isinstance(end, datetime.date):
        end = end.strftime("%Y-%m-%d")
    plan_workouts = get_plan_workouts(get_current_plan(), start, end)
    workouts = {}
    for workout in plan_workouts:
        try:
            workouts[workout["scheduledWorkoutDate"]] = (
                workout["workout"]["workoutName"],
                workout["scheduleWorkoutId"],
            )
        except KeyError:
            workouts[workout["scheduledWorkoutDate"]] = (None, None)

    start_date = datetime.datetime.strptime(start, "%Y-%m-%d")
    end_date = datetime.datetime.strptime(end, "%Y-%m-%d")
    for dt in rrule.rrule(rrule.MONTHLY, dtstart=start_date, until=end_date):
        calendar_workouts = get_calendar_workouts(dt.year, dt.month - 1)
        for workout in calendar_workouts:
            logging.debug(f"Got {workout}")
            workouts[workout["date"]] = (workout["title"], workout["id"])

    workouts = dict(sorted(workouts.items()))
    rows = []
    for w in workouts:
        if not isinstance(w, datetime.datetime):
            date = datetime.datetime.strptime(w, "%Y-%m-%d")
            rows.append(
                {
                    "date": date,
                    "name": workouts[w][0],
                    "scheduleId": workouts[w][1],
                }
            )
    workouts = pd.DataFrame(rows)
    return workouts


def get_workout_id(scheduleId):
    try:
        return get_scheduled_workout(scheduleId)["workout"]["workoutId"]
    except TypeError:
        pass


def get_estimate_for_type(step_type, zones=None):
    if step_type in ["warmup", "cooldown", "recovery", "rest"]:
        return 3
    if step_type in ["interval"]:
        return 4


class Workout:
    def __init__(self, original):
        self.original = original
        self.segments = original["segments"]
        steps = []
        for segment in self.segments:
            steps += segment["workoutSteps"]


def to_data_frame(workout) -> pd.DataFrame:
    rows = []
    segments = workout["workoutSegments"]
    for segment in segments:
        sport = segment["sportType"]["sportTypeKey"]
        steps = segment["workoutSteps"]
        for step in steps:
            if step["stepType"]["stepTypeKey"] == "repeat":
                substeps = step["workoutSteps"]
                number = step["numberOfIterations"]
            else:
                substeps = [step]
                number = 1
            for i in range(0, number):
                for substep in substeps:
                    row = {
                        "type": substep["stepType"]["stepTypeKey"],
                        "description": substep["description"],
                        "sport": sport,
                    }
                    if substep["targetType"] is None:
                        target_type = "no.target"
                    else:
                        target_type = substep["targetType"]["workoutTargetTypeKey"]
                    row["target_type"] = target_type
                    if target_type == "pace.zone":
                        row["target_lower"] = substep["targetValueTwo"]
                        row["target_upper"] = substep["targetValueOne"]
                        row["speed"] = 0.5 * (row["target_lower"] + row["target_upper"])
                    elif target_type == "no.target":
                        row["target_type"] = "pace.estimate"
                        row["speed"] = get_estimate_for_type(row["type"])
                    elif target_type in [
                        "cadence",
                        "heart.rate.zone",
                        "power.zone",
                        "power.3s",
                    ]:
                        row["target_lower"] = substep["targetValueTwo"]
                        row["target_upper"] = substep["targetValueOne"]
                        row["speed"] = get_estimate_for_type(row["type"])
                    end_condition_type = substep["endCondition"]["conditionTypeKey"]
                    if end_condition_type == "time":
                        row["duration"] = substep["endConditionValue"]
                        try:
                            row["distance"] = row["duration"] * row["speed"]
                        except KeyError:
                            pass
                    elif end_condition_type == "distance":
                        row["distance"] = substep["endConditionValue"]
                        try:
                            row["duration"] = row["distance"] / row["speed"]
                        except KeyError:
                            pass
                    elif end_condition_type == "lap.button":
                        row["duration"] = 0
                    time = int(row["duration"])
                    row["duration"] = 1
                    if time > 0:
                        row["distance"] = row["distance"] / time
                        for i in range(0, time):
                            rows.append(row)
    df = pd.DataFrame(rows)
    df["distance"] = df["distance"].cumsum()
    df.index = pd.to_timedelta(df["duration"].cumsum(), "s")
    return df


# logging.basicConfig(level=logging.DEBUG)


# pd.set_option("display.max_rows", None)
# pd.set_option("display.max_columns", None)
# metrics = MetricsCalculator(activity, [GOVSS])
# print(metrics.metrics)
# garth.resume("~/sports-planner/seb.laclau@gmail.com")
# workouts = get_all_workouts("2023-12-1", "2023-12-31")
# workouts["workout"] = workouts["scheduleId"].apply(get_scheduled_workout)
# print(workouts)
