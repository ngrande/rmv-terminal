#!/usr/bin/env python

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

base_url = "https://www.rmv.de/hapi"
access_id_path = "./.access_id"
train_station_csv_path = "./RMV_Haltestellen.csv"

#logging.basicConfig(level=logging.DEBUG)


class query_cache():
	def __init__(self, cache_time_delta, base_url):
		self._cache_path = "/var/tmp/{}.cache".format(__file__)
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


def parse_response(departures):

	for departure in departures:
		
		if datetime.datetime.now() >= extract_datetime(departure):
			continue

		yield departure


def find_station_id(station_search_str):
	if station_search_str is None or station_search_str == "":
		return []

	logging.debug("searching for {}".format(station_search_str))
	with open(train_station_csv_path, "r", encoding="utf-8") as station_file:
		reader = csv.DictReader(station_file, delimiter=";")
		for row in reader:
			if station_search_str.lower() in row['HST_NAME'].lower():
				station_id = row['HAFAS_ID']
				logging.debug("{} - {}".format(station_search_str, row['HST_NAME']))
				yield station_id


def process_query(access_id, cache, station, direction=None, lines=None, n=None):
	query = dict()
	# api token
	query['accessId'] = access_id
	# train station id
	query['id'] = station
	query['format'] = 'json'
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

	for i, departure in enumerate(parse_response(json_data['Departure'])):
		if n and n <= i:
			break
		yield departure


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
	args = parser.parse_args()

	if args.debug:
		logging.basicConfig(level=logging.DEBUG)

	if args.i3:
		args.n = 1

	if args.train_stations_csv:
		train_station_csv_path = args.train_stations_csv
	
	cache = query_cache(datetime.timedelta(minutes=30), base_url)

	access_id = open(access_id_path, "r", encoding="utf-8").read().strip()
	if args.token:
		access_id = args.token

	for station in find_station_id(args.station):
		directions = list(find_station_id(args.direction))
		if len(directions) == 0:
			directions = [None]
		for direction in directions:
			if direction:
				logging.debug("looking for direction: {}".format(direction))
			for departure in process_query(access_id, cache, station, direction, args.lines, args.n):
				format_output(departure, args.i3)

	cache.dump()


#  vim: tabstop=4 shiftwidth=4 noexpandtab
