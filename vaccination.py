import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from io import StringIO

DATAFILE_URL = (
    "https://impfdashboard.de/static/data/germany_vaccinations_timeseries_v2.tsv"
)


def download_data():
    response = urllib.request.urlopen(DATAFILE_URL)
    data = response.read()
    return StringIO(data.decode("utf-8"))


@dataclass
class VaccinationDay:
    date: date
    total_doses: int
    doses_new: int

    def __init__(self, row):
        self.date = datetime.fromisoformat(row["date"]).date()
        self.total_doses = int(row["dosen_kumulativ"])
        self.doses_new = int(row["dosen_differenz_zum_vortag"])


class Container:
    def __init__(self):
        self.data = {}

    def __getitem__(self, date: date):
        return self.data[date.isoformat()]

    def add(self, item: VaccinationDay):
        self.data[item.date.isoformat()] = item

    def sevenDayAverage(self, last_day=None):
        if last_day is None:
            last_day = date.today() - timedelta(days=1)

        total_doses = 0

        for i in range(7):
            entry = self.data[(last_day - timedelta(days=i)).isoformat()]
            total_doses += entry.doses_new

        return total_doses / 7
