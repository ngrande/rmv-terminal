#!/usr/bin/env python3

import sys
import os
import csv
import argparse
import urllib
import urllib.request
import urllib.parse
import datetime
import logging
import json
import pickle
import operator
import shutil

base_url = "https://www.rmv.de/hapi"
access_id_path = "{}/.access_id".format(os.path.dirname(__file__))
# distributed in the git repository
train_station_csv_path = "{}/RMV_Haltestellen.csv".format(os.path.dirname(__file__))
register_link = "https://opendata.rmv.de/site/anmeldeseite.html"
tmp_path = "/tmp"

INVALID_ACCESS_ID_RETURN = 1


class query_cache():
	def __init__(self, cache_time_delta, base_url):
		self._cache_path = os.path.join(tmp_path, "{}.cache".format(os.path.basename(__file__)[:-3]))
		self.cache_time_delta = cache_time_delta
		self.base_url = base_url
		self.cache = dict()
		if os.path.isfile(self._cache_path):
			logging.debug("loading pickled object from '{}'".format(self._cache_path))
			with open(self._cache_path, "rb") as o:
				self.cache = pickle.load(o)

	def dump(self):
		logging.debug("writing cache pickled into file '{}'".format(self._cache_path))
		with open(self._cache_path, "wb") as o:
			pickle.dump(self.cache, o)


	def _generate_key_from_dict(self, d):
		d = self._clean_query_dict(d)
		ordered = []
		for k, v in d.items():
			ordered.append("{}: {}".format(k, v))

		ordered.sort()
		return ";".join(ordered)

	def _clean_query_dict(self, query_dict):
		query_dict_c = dict(query_dict)
		del query_dict_c['accessId']
		return query_dict_c

	def get_from_cache(self, method, query_dict):
		query_key = self._generate_key_from_dict(query_dict)

		if method in self.cache and query_key in self.cache[method]:
			cached_data = self.cache[method][query_key]
			if datetime.datetime.now() - cached_data['time'] > self.cache_time_delta:
				# data too old!
				logging.debug("data might be cached but too old anyway")
				del self.cache[method][query_key]
				return None
			# data still good!
			logging.debug("data in cache!")
			return cached_data['result']


	def add_to_cache(self, method, query_dict, result):
		query_key = self._generate_key_from_dict(query_dict)

		if method not in self.cache:
			self.cache[method] = {}
		self.cache[method][query_key] = {}
		self.cache[method][query_key]['time'] = datetime.datetime.now()
		self.cache[method][query_key]['result'] = result


	def query(self, method, query_dict):

		result = self.get_from_cache(method, query_dict)
		if result:
			return result

		querystring = urllib.parse.urlencode(query_dict)

		request_url = os.path.join(base_url, method) + "?" + querystring
		logging.debug("requesting data from URL {}".format(request_url))

		try:
			res = urllib.request.urlopen(request_url)
		except urllib.error.HTTPError as e:
			if e.getcode() == 403:
				logging.error("URL access forbidden: invalid access id (token)? You can register here: {}".format(register_link))
				sys.exit(INVALID_ACCESS_ID_RETURN)
			logging.debug("HTTP error code '{}': {}".format(e.getcode(), e.reason))
			return None

		logging.debug("request: {}".format(res.getcode()))

		json_data = json.load(res)

		self.add_to_cache(method, query_dict, json_data)

		return json_data


def extract_datetime(departure):
	date = departure['date']
	time = departure['time']
	dt = datetime.datetime.strptime(date + " " + time, "%Y-%m-%d %H:%M:%S")

	if 'rtDate' and 'rtTime' in departure:
		real_date = departure['rtDate']
		real_time = departure['rtTime']
		real_dt = datetime.datetime.strptime(real_date + " " + real_time, "%Y-%m-%d %H:%M:%S")
		return real_dt

	return dt


def format_output(departure, i3=None):
	dt = extract_datetime(departure)

	name = departure['name'].strip()
	direction = departure['direction']

	now = datetime.datetime.now()

	duration = dt - now
	minutes = round(float(duration.seconds / 60), 1)

	minute_str = str(minutes)
	if minute_str.endswith(".0") or minutes > 5:
		minute_str = str(int(minutes))

	if not i3:
		print("{} -> {}: {}m".format(name, direction, minute_str))
	else:
		minute_str = str(round(minutes))
		print("{}: {}m".format(name, minute_str))


def parse_response(departures, threshold=None):

	for departure in departures:
		departure['datetime'] = extract_datetime(departure)

	departures = sorted(departures, key=operator.itemgetter('datetime'))

	for departure in departures:
		
		departure_time = departure['datetime']
		delta_till_departure = (departure_time - datetime.datetime.now()).seconds / 60
		now = datetime.datetime.now()
		if now >= departure_time:
			logging.debug("train is already departed (now: {}): {}".format(now, departure))
			continue
		elif threshold and delta_till_departure <= threshold:
			logging.debug("train is filtered due to threshold ({}): {}".format(threshold, departure))
			continue

		if not departure['reachable']:
			logging.debug("train is not reachable: {}".format(threshold, departure))
			continue

		yield departure


def find_station_id(csv_dict_data, station_search_str):
	if station_search_str is None or station_search_str == "":
		return []

	logging.debug("searching for {}".format(station_search_str))
	for row in csv_dict_data:
		if station_search_str.lower() in row['HST_NAME'].lower():
			station_id = row['HAFAS_ID']
			logging.debug("{} - {}".format(station_search_str, row['HST_NAME']))
			yield station_id


def process_query(access_id, cache, station, direction=None, lines=None, n=None, threshold=None, duration=None):
	query = dict()
	# api token
	query['accessId'] = access_id
	# train station id
	query['id'] = station
	query['lang'] = 'de' # 'en' is also possible
	query['format'] = 'json'
	if duration:
		query['duration'] = duration
	if direction:
		query['direction'] = direction
	if lines:
		query['lines'] = lines

	api_func = "departureBoard"
	json_data = cache.query(api_func, query)

	if json_data is None:
		return

	if 'Departure' not in json_data:
		return

	for i, departure in enumerate(parse_response(json_data['Departure'], threshold)):
		if n and n <= i:
			break
		yield departure


def cache_csv_file(csv_path):
	mtime = os.stat(csv_path).st_mtime_ns
	csv_name = os.path.basename(csv_path)

	cache_file = "{}.{}".format(csv_name, mtime)
	cache_file_path = os.path.join(tmp_path, cache_file)

	is_in_cache = False

	# find actual file in cache
	for f in os.listdir(tmp_path):
		if csv_name in f and f != cache_file:
			# cleanup old csv files
			outdated_file = os.path.join(tmp_path, f)
			logging.debug("removing old cached csv file '{}'".format(outdated_file))
			os.remove(outdated_file)
		elif f == cache_file:
			# file is up to date
			is_in_cache = True
			logging.debug("csv file is still in cache '{}'".format(cache_file_path))

	if not is_in_cache:
		shutil.copyfile(csv_path, cache_file_path)
		logging.debug("updating cached csv file '{}' -> '{}'".format(csv_path, cache_file_path))

	return cache_file_path


if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument("station", help="request information for a train station")
	parser.add_argument("--direction", help="direction of the trains")
	parser.add_argument("--lines", help="list of lines (separated by comma and negated by !)")
	parser.add_argument("-n", type=int, help="(maximum) number of trains to display")
	parser.add_argument("--debug", help="enable debug logging", action="store_true")
	parser.add_argument("--i3", help="i3 mode", action="store_true")
	parser.add_argument("--train_stations_csv", help="path to the train stations csv file (expected to be UTF-8)", default=train_station_csv_path)
	parser.add_argument("--token", help="API token")
	parser.add_argument("--threshold", help="a threshold (in minutes) to filter the trains", type=int)
	parser.add_argument("--duration", help="specify a duration in minutes for which to query the trains")
	parser.add_argument("--cache-duration", help="minutes of cache time (before requesting new data)", type=int, default=15)
	args = parser.parse_args()

	if args.debug:
		logging.basicConfig(level=logging.DEBUG)

	if args.i3:
		args.n = 1

	cache = query_cache(datetime.timedelta(minutes=args.cache_duration), base_url)

	assert os.path.isfile(access_id_path) or args.token, "file required: {} OR --token=<access_id>".format(access_id_path)
	access_id = None
	if args.token:
		access_id = args.token
	else:
		access_id = open(access_id_path, "r", encoding="utf-8").read().strip()
	assert access_id, "No access id set - bug!"

	csv_dict_data = None
	cached_csv_file_path = cache_csv_file(args.train_stations_csv)
	with open(cached_csv_file_path, "r", encoding="utf-8") as station_file:
		csv_dict_data = []
		for row in csv.DictReader(station_file, delimiter=";"):
			csv_dict_data.append(row)
	assert csv_dict_data is not None and len(csv_dict_data) > 0, "could not read csv station file"

	for station in find_station_id(csv_dict_data, args.station):
		directions = list(find_station_id(csv_dict_data, args.direction))
		if len(directions) == 0:
			directions = [None]
		for direction in directions:
			if direction:
				logging.debug("looking for direction: {}".format(direction))
			for departure in process_query(access_id, cache, station, direction, args.lines, args.n, args.threshold, args.duration):
				format_output(departure, args.i3)

	cache.dump()


#  vim: tabstop=4 shiftwidth=4 noexpandtab
