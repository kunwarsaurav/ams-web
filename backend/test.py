import urllib.request
from urllib.error import HTTPError
try:
    urllib.request.urlopen('http://127.0.0.1:8080/attendance/export?start_date=2026-06-30&end_date=2026-07-07')
except HTTPError as e:
    print(e.read().decode())
