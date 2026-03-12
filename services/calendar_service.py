
import requests
from datetime import date, timedelta

API="https://isdayoff.ru/api/getdata"

def fetch_year(year:int):
    r=requests.get(f"{API}?year={year}",timeout=20)
    r.raise_for_status()
    data=r.text.strip()
    days=[]
    d=date(year,1,1)
    for c in data:
        days.append({
            "date":d.isoformat(),
            "is_workday": c=="0"
        })
        d+=timedelta(days=1)
    return days
