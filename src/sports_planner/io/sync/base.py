import datetime
from abc import ABC, abstractmethod

import pandas as pd


class SyncProvider(ABC):
    workouts: pd.DataFrame

    @abstractmethod
    def sync(self):
        pass

    @abstractmethod
    def get_workouts(self, start: datetime.date, end: datetime.date):
        pass
