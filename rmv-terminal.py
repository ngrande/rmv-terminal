#!/usr/bin/env python

import os
import csv
import xml.etree
import xml.etree.ElementTree
import argparse
import urllib
import urllib.request
import urllib.parse
import datetime

base_url = "https://www.rmv.de/hapi"
access_id_path = "./.access_id"
train_station_csv_path = "./RMV_Haltestellen.csv"

def parse_response(xml_f):
	tree = xml.etree.ElementTree.parse(xml_f)
	root = tree.getroot()

	for departure in root.iter('{hafas_rest}Departure'):

		date = departure.attrib['date']
		time = departure.attrib['time']
		dt = datetime.datetime.strptime(date + " " + time, "%Y-%m-%d %H:%M:%S")

		real_dt = None
		if 'rtDate' and 'rtTime' in departure.attrib:
			real_date = departure.attrib['rtDate']
			real_time = departure.attrib['rtTime']
			real_dt = datetime.datetime.strptime(real_date + " " + real_time, "%Y-%m-%d %H:%M:%S")

		name = departure.attrib['name']
		direction = departure.attrib['direction']
		print("{} -> {}: {} ({})".format(name, direction, dt, real_dt))


def find_station_id(station_search_str):
	with open(train_station_csv_path, "r", encoding="utf-8") as station_file:
		reader = csv.DictReader(station_file, delimiter=";")
		for row in reader:
			if args.station.lower() in row['HST_NAME'].lower():
				station_id = row['HAFAS_ID']
				return station_id

	return None


if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument("station", help="request information for a train station")
	args = parser.parse_args()

	station_id = find_station_id(args.station)

	api_func = "departureBoard"

	api_url = os.path.join(base_url, api_func)

	query = dict()
	# api token
	query['accessId'] = open(access_id_path, "r", encoding="utf-8").read().strip()
	# train station id
	query['id'] = station_id

	querystring = urllib.parse.urlencode(query)

	request_url = api_url + "?" + querystring

	print("requesting data from URL ", request_url)

	res = urllib.request.urlopen(request_url)
	parse_response(res)


#  vim: tabstop=4 shiftwidth=4 noexpandtab
