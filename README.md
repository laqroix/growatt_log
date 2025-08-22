# Growatt Log

Small Python script to fetch recent statistics from a Growatt inverter / Mix (hybrid) device using the unofficial Growatt mobile API endpoints.

## Features
* Logs in with (obfuscated) Growatt password hashing quirk
* Retrieves plant list and selects the first plant automatically
* Fetches:
  * Per‑timeframe production/consumption chart data (hour mode)
  * Current system status (PV power, grid import, local load, battery discharge)
  * Battery State of Charge (SoC)
  * Today energy production and consumption split
  * Dashboard energy storage overview
* Prints only non‑zero time slots for clearer quick inspection

## Requirements
* Python 3.8+
* `requests` library

Install dependency (if not already available):
```bash
pip install requests
```

## Usage
Run the script from the `growatt_log` directory:
```bash
python growatt.py --username YOUR_EMAIL --password YOUR_PASSWORD --mixsn YOUR_MIX_SERIAL
```

Arguments:
| Argument | Required | Description |
|----------|----------|-------------|
| `--username` | yes | Your Growatt portal login (email / username) |
| `--password` | yes | Your Growatt portal password (sent then hashed internally) |
| `--mixsn` | yes | Serial number of the Mix / storage device |

## Sample Output (abridged)
```
--- Timedata (non-zero sysOut) ---
Time: 07:05 Val: {'sysOut': '1540', 'load': '820', ...}
...
--- Mix System Status ---
PV Power           : 2140 W
From Grid          : 0 W
House Consumption  : 980 W
From Battery       : 0 W

--- Mix Info ---
Battery Charge Level: 82%
Production Today    : 5.43 kWh

--- Dashboard Data ---
Total Power Load      : 9.12 kWh
PV Power Load Today   : 7.34 kWh
Grid Power Load Today : 1.78 kWh
```

## Cron / Automation Example
Append to crontab (collect every 15 minutes and append to a log file):
```bash
*/15 * * * * /usr/bin/python3 /path/to/growatt_log/growatt.py --username NAME --password PASS --mixsn MIXSN >> /var/log/growatt.log 2>&1
```

## Output Fields (quick notes)
* `ppv` – Instant PV array output power (W)
* `pactouser` – Grid import power to user (W)
* `pLocalLoad` – Current house/local load (W)
* `pdisCharge1` – Battery discharge power (W)
* `soc` – Battery state of charge (%)
* `todayEnergy` – Today’s total PV production (kWh)
* Chart `sysOut` – Interval PV output (unit from API, typically W or Wh depending on endpoint granularity)

## Security Notes
* Credentials are sent to Growatt’s official server over HTTPS.
* Avoid committing real credentials; use environment variables or a wrapper script for automation.
* Consider creating a low‑privilege read‑only user (if supported) for logging.

## Limitations / Caveats
* Relies on undocumented (reverse‑engineered) mobile endpoints – they may change without notice.
* Script currently selects the first plant; adapt if you manage multiple plants.
* No built‑in retry / backoff logic yet.

## Extending
The `GrowattApi` class in `growatt.py` exposes many helper methods (plant detail, inverter detail, mix detail, storage, etc.). You can import and reuse it in other scripts instead of running the CLI section.

Example library usage:
```python
from growatt import GrowattApi, Timespan
import datetime

api = GrowattApi()
session = api.login(USER, PASS)
plants = api.plant_list(session['userId'])
plant_id = plants['data'][0]['plantId']
detail = api.plant_detail(plant_id, Timespan.hour, datetime.date.today())
print(detail['back'] if 'back' in detail else detail)
```

## Troubleshooting
| Problem | Hint |
|---------|------|
| Login fails | Verify credentials via web portal; ensure no 2FA / region block |
| Empty device list | Confirm `mixsn` matches device; check account ownership |
| All zeros in output | Nighttime or device asleep; try during daylight |
| HTTP errors | Temporary API issue; add retries or wait |

## License
Add a license file (e.g. MIT) if you plan to share/distribute. (Currently unspecified.)

## Disclaimer
This project is not affiliated with or endorsed by Growatt. Use at your own risk; API stability is not guaranteed.
