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

base_url = "https://www.rmv.de/hapi"
access_id_path = "./.access_id"
train_station_csv_path = "./RMV_Haltestellen.csv"

#logging.basicConfig(level=logging.DEBUG)


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


def process_query(station, direction=None, lines=None, n=None):
	query = dict()
	# api token
	query['accessId'] = open(access_id_path, "r", encoding="utf-8").read().strip()
	# train station id
	query['id'] = station
	query['format'] = 'json'
	if direction:
		query['direction'] = direction
	if lines:
		query['lines'] = lines

	querystring = urllib.parse.urlencode(query)

	request_url = api_url + "?" + querystring

	logging.debug("requesting data from URL {}".format(request_url))

	try:
		res = urllib.request.urlopen(request_url)
	except urllib.error.HTTPError as e:
		logging.debug("HTTP error code '{}': {}".format(e.getcode(), e.reason))
		return

	logging.debug("request: {}".format(res.getcode()))

	json_data = json.load(res)
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
	parser.add_argument("-n", type=int, help="number of trains to display")
	parser.add_argument("--debug", help="enable debug logging", action="store_true")
	parser.add_argument("--i3", help="i3 mode", action="store_true")
	args = parser.parse_args()

	if args.debug:
		logging.basicConfig(level=logging.DEBUG)

	if args.i3:
		args.n = 1

	api_func = "departureBoard"

	api_url = os.path.join(base_url, api_func)

	for station in find_station_id(args.station):
		directions = list(find_station_id(args.direction))
		if len(directions) == 0:
			directions = [None]
		for direction in directions:
			if direction:
				logging.debug("looking for direction: {}".format(direction))
			for departure in process_query(station, direction, args.lines, args.n):
				format_output(departure, args.i3)


#  vim: tabstop=4 shiftwidth=4 noexpandtab
