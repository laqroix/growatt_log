import argparse
import datetime
import hashlib
import json
import requests
import warnings
from enum import IntEnum
from random import randint
from typing import Any, Dict, Optional, Union

# Utility function to hash password as required by Growatt API
def hash_password(password: str) -> str:
    """
    Hash the password using MD5 and replace '0' with 'c' if a byte of the digest is less than 10.
    This is a Growatt-specific quirk.
    """
    password_md5 = hashlib.md5(password.encode('utf-8')).hexdigest()
    for i in range(0, len(password_md5), 2):
        if password_md5[i] == '0':
            password_md5 = password_md5[:i] + 'c' + password_md5[i + 1:]
    return password_md5

# Enum for timespan types used in API queries
class Timespan(IntEnum):
    hour = 0
    day = 1
    month = 2

# Main API wrapper for Growatt server
class GrowattApi:
    server_url: str = 'https://server-api.growatt.com/'
    agent_identifier: str = (
        "Dalvik/2.1.0 (Linux; U; Android 12; https://github.com/indykoning/PyPi_GrowattServer)"
    )

    def __init__(self, add_random_user_id: bool = False, agent_identifier: Optional[str] = None) -> None:
        # Optionally customize agent identifier and add random suffix
        if agent_identifier:
            self.agent_identifier = agent_identifier
        if add_random_user_id:
            random_number = ''.join(str(randint(0, 9)) for _ in range(5))
            self.agent_identifier += f" - {random_number}"
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': self.agent_identifier})

    def __get_date_string(self, timespan: Optional[Timespan] = None, date: Optional[Union[datetime.datetime, datetime.date]] = None) -> str:
        # Format date string for API requests based on timespan
        if timespan is not None:
            assert timespan in Timespan
        date = date or datetime.datetime.now()
        if timespan == Timespan.month:
            return date.strftime('%Y-%m')
        return date.strftime('%Y-%m-%d')

    def get_url(self, page: str) -> str:
        # Helper to build full API endpoint URL
        return self.server_url + page

    def login(self, username: str, password: str, is_password_hashed: bool = False) -> Dict[str, Any]:
        # Log in to Growatt API and return user data
        if not is_password_hashed:
            password = hash_password(password)
        response = self.session.post(self.get_url('newTwoLoginAPI.do'), data={
            'userName': username,
            'password': password,
            'NewLogin': 1
        })
        data = json.loads(response.content.decode('utf-8'))['back']
        if data['success']:
            data.update({
                'userId': data['user']['parentUserId'],
                'userLevel': data['user']['rightlevel']
            })
        return data

    def plant_list(self, user_id: str) -> Dict[str, Any]:
        # Get list of plants for the user
        response = self.session.get(self.get_url('PlantListAPI.do'),
                                    params={'userId': user_id},
                                    allow_redirects=False)
        return json.loads(response.content.decode('utf-8'))['back']

    def new_plant_list(self, user_id: str) -> Dict[str, Any]:
        # Get new format plant list for the user
        response = self.session.get(self.get_url('newPlantListAPI.do'),
                                    params={'userId': user_id},
                                    allow_redirects=False)
        return json.loads(response.content.decode('utf-8'))['back']

    def plant_detail(self, plant_id: str, timespan: Timespan, date: Optional[Union[datetime.datetime, datetime.date]] = None) -> Dict[str, Any]:
        # Get plant detail data for a given timespan and date
        date_str = self.__get_date_string(timespan, date)
        response = self.session.get(self.get_url('newPlantDetailAPI.do'), params={
            'plantId': plant_id,
            'type': timespan.value,
            'date': date_str
        })
        return json.loads(response.content.decode('utf-8'))['back']

    def inverter_data(self, inverter_id: str, date: Optional[Union[datetime.datetime, datetime.date]] = None) -> Dict[str, Any]:
        # Get inverter data for a specific date
        date = date or datetime.date.today()
        date_str = self.__get_date_string(Timespan.hour, date)
        response = self.session.get(self.get_url('newInverterAPI.do'), params={
            'op': 'getInverterData',
            'id': inverter_id,
            'type': 1,
            'date': date_str
        })
        return json.loads(response.content.decode('utf-8'))

    def inverter_detail(self, inverter_id: str) -> Dict[str, Any]:
        # Get detailed inverter data
        response = self.session.get(self.get_url('newInverterAPI.do'), params={
            'op': 'getInverterDetailData',
            'inverterId': inverter_id
        })
        return json.loads(response.content.decode('utf-8'))

    def inverter_detail_two(self, inverter_id: str) -> Dict[str, Any]:
        # Get alternative detailed inverter data
        response = self.session.get(self.get_url('newInverterAPI.do'), params={
            'op': 'getInverterDetailData_two',
            'inverterId': inverter_id
        })
        return json.loads(response.content.decode('utf-8'))

    def tlx_data(self, tlx_id: str, date: Optional[Union[datetime.datetime, datetime.date]] = None) -> Dict[str, Any]:
        # Get TLX device data
        date_str = self.__get_date_string(date=date)
        response = self.session.get(self.get_url('TlxApi.do'), params={
            'op': 'getTlxData',
            'id': tlx_id,
            'type': 1,
            'date': date_str
        })
        return json.loads(response.content.decode('utf-8'))

    def tlx_detail(self, tlx_id: str) -> Dict[str, Any]:
        # Get TLX device detail data
        response = self.session.get(self.get_url('TlxApi.do'), params={
            'op': 'getTlxDetailData',
            'id': tlx_id
        })
        return json.loads(response.content.decode('utf-8'))

    def mix_info(self, mix_id: str, plant_id: Optional[str] = None) -> Dict[str, Any]:
        # Get mix system info
        params = {'op': 'getMixInfo', 'mixId': mix_id}
        if plant_id:
            params['plantId'] = plant_id
        response = self.session.get(self.get_url('newMixApi.do'), params=params)
        return json.loads(response.content.decode('utf-8'))['obj']

    def mix_totals(self, mix_id: str, plant_id: str) -> Dict[str, Any]:
        # Get mix system totals (energy overview)
        response = self.session.post(self.get_url('newMixApi.do'), params={
            'op': 'getEnergyOverview',
            'mixId': mix_id,
            'plantId': plant_id
        })
        return json.loads(response.content.decode('utf-8'))['obj']

    def mix_system_status(self, mix_id: str, plant_id: str) -> Dict[str, Any]:
        # Get current system status for mix device
        response = self.session.post(self.get_url('newMixApi.do'), params={
            'op': 'getSystemStatus_KW',
            'mixId': mix_id,
            'plantId': plant_id
        })
        return json.loads(response.content.decode('utf-8'))['obj']

    def mix_detail(self, mix_id: str, plant_id: str, timespan: Timespan = Timespan.day, date: Optional[Union[datetime.datetime, datetime.date]] = None) -> Dict[str, Any]:
        # Get mix system detail data for a given timespan and date
        date_str = self.__get_date_string(timespan, date)
        response = self.session.post(self.get_url('newMixApi.do'), params={
            'op': 'getEnergyProdAndCons_KW',
            'plantId': plant_id,
            'mixId': mix_id,
            'type': timespan.value,
            'date': date_str
        })
        return json.loads(response.content.decode('utf-8'))['obj']

    def dashboard_data(self, plant_id: str, timespan: Timespan = Timespan.hour, date: Optional[Union[datetime.datetime, datetime.date]] = None) -> Dict[str, Any]:
        # Get dashboard data for plant (energy storage statistics)
        date_str = self.__get_date_string(timespan, date)
        response = self.session.post(self.get_url('newPlantAPI.do'), params={
            'action': "getEnergyStorageData",
            'date': date_str,
            'type': timespan.value,
            'plantId': plant_id
        })
        return json.loads(response.content.decode('utf-8'))

    def storage_detail(self, storage_id: str) -> Dict[str, Any]:
        # Get storage device details
        response = self.session.get(self.get_url('StorageAPI.do'), params={
            'op': 'getStorageInfo_sacolar',
            'storageId': storage_id
        })
        return json.loads(response.content.decode('utf-8'))

    def storage_params(self, storage_id: str) -> Dict[str, Any]:
        # Get storage device parameters
        response = self.session.get(self.get_url('StorageAPI.do'), params={
            'op': 'getStorageParams_sacolar',
            'storageId': storage_id
        })
        return json.loads(response.content.decode('utf-8'))

    def storage_energy_overview(self, plant_id: str, storage_id: str) -> Dict[str, Any]:
        # Get energy overview for storage device
        response = self.session.post(self.get_url('StorageAPI.do?op=getEnergyOverviewData_sacolar'), params={
            'plantId': plant_id,
            'storageSn': storage_id
        })
        return json.loads(response.content.decode('utf-8'))['obj']

    def inverter_list(self, plant_id: str) -> Any:
        # Deprecated: use device_list instead
        warnings.warn(
            "This function may be deprecated in the future because naming is not correct, use device_list instead",
            DeprecationWarning
        )
        return self.device_list(plant_id)

    def device_list(self, plant_id: str) -> Any:
        # Get list of devices for a plant
        return self.plant_info(plant_id)['deviceList']

    def plant_info(self, plant_id: str) -> Dict[str, Any]:
        # Get plant info including device list
        response = self.session.get(self.get_url('TwoPlantAPI.do'), params={
            'op': 'getAllDeviceList',
            'plantId': plant_id,
            'pageNum': 1,
            'pageSize': 1
        })
        return json.loads(response.content.decode('utf-8'))

    def get_plant_settings(self, plant_id: str) -> Dict[str, Any]:
        # Get plant settings
        response = self.session.get(self.get_url('PlantAPI.do'), params={
            'op': 'getPlant',
            'plantId': plant_id
        })
        return json.loads(response.content.decode('utf-8'))






# Parse command-line arguments for username, password, and mix serial number
parser = argparse.ArgumentParser(description="Growatt API script")
parser.add_argument("--username", required=True, help="Growatt username")
parser.add_argument("--password", required=True, help="Growatt password")
parser.add_argument("--mixsn", required=True, help="Mix serial number")
args = parser.parse_args()

# Assign parsed arguments to variables
username: str = args.username
password: str = args.password
mixsn: str = args.mixsn

# Initialize Growatt API and log in
api: GrowattApi = GrowattApi()
login_response: Dict[str, Any] = api.login(username, password)

# Get plant information and extract plant ID
plant_info: Dict[str, Any] = api.plant_list(login_response['userId'])
plant_id: str = str(plant_info["data"][0]["plantId"])

# Get plant detail data for the current hour
plant_detail: Dict[str, Any] = api.plant_detail(plant_id, Timespan.hour, datetime.date.today())

# Get mix system status and mix detail data for the current hour
mixinfo: Dict[str, Any] = api.mix_system_status(mixsn, plant_id)
plant_detail = api.mix_detail(mixsn, plant_id, Timespan.hour, datetime.date.today())

# Extract time-based chart data from plant detail
timedata: Dict[str, Any] = plant_detail["chartData"]

print("\n--- Timedata (non-zero sysOut) ---")
# Print time and value for entries where sysOut is not zero
for key in sorted(timedata):
    if timedata[key]["sysOut"] != '0':
        print(f"Time: {key} Val: {timedata[key]}")

print("\n--- Mix System Status ---")
# Print mix system status values
print(f"PV Power           : {mixinfo['ppv']} W")
print(f"From Grid          : {mixinfo['pactouser']} W")
print(f"House Consumption  : {mixinfo['pLocalLoad']} W")
print(f"From Battery       : {mixinfo['pdisCharge1']} W")

# Get mix info and print battery charge level and today's production
mix_info: Dict[str, Any] = api.mix_info(mixsn, plant_id)
print("\n--- Mix Info ---")
print(f"Battery Charge Level: {mix_info['soc']}%")
print(f"Production Today    : {plant_info['data'][0]['todayEnergy']} kWh")

# Get dashboard data and print power load statistics
mix_totals: Dict[str, Any] = api.dashboard_data(plant_id)
print("\n--- Dashboard Data ---")
print(f"Total Power Load      : {mix_totals['elocalLoad']} kWh")
print(f"PV Power Load Today   : {mix_totals['eChargeToday1']} kWh")
print(f"Grid Power Load Today : {mix_totals['etouser']} kWh")
