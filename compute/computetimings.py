#!/usr/bin/env python3
#
# Author: Theresa Enghardt (theresa@inet.tu-berlin.de)
# 2018
#
# Tools to compute and plot page load timings from Navigation Timings, Resource Timings, and HAR files as exported by webtimings.py
#
# Usage:
#           ./computetimings.py RUNFILTER WORKLOAD POLICY LOG_LEVEL
#                   RUNFILTER:  every run which contains this string will be considered (default: consider all runs)
#                   WORKLOAD:   supply multiple separated by comma, every page which contains one of these strings will be consider (default: "all")
#                   POLICY:     supply multiple separated by comma (default: "all")
#                   LOG_LEVEL:  set to "debug" or "info" to get more debug output

import os
import errno
import datetime
import time
import sys
import glob
import csv
import re
import logging
import json
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_pdf import PdfPages
import hartimings
import subprocess
import copy
import validate_object_size


RUNDIR = "../testdata/"

NAVTIMINGS_FILENAME = "navtimings.log"
RESTIMINGS_FILENAME = ".res.log"
LOGFILENAME = "final_timings.log"

# Fields of the CSV files
navtiming_fields = [ "page", "scenario", "starttime", "startunixtimestamp", "navigationStart", "redirectStart", "redirectEnd", "fetchStart", "domainLookupStart", "domainLookupEnd", "connectStart", "secureConnectionStart", "connectEnd", "requestStart", "responseStart", "responseEnd", "domLoading", "domInteractive", "domContentLoadedEventStart", "domContentLoadedEventEnd", "domComplete", "loadEventStart", "loadEventEnd", "firstPaint" ]

restiming_fields = [ 'name', "scenario", "initiatorType", "nextHopProtocol", "encodedBodySize", "decodedBodySize", "starttime", "redirectStart", "redirectEnd", "fetchStart", "domainLookupStart", "domainLookupEnd", "connectStart", "secureConnectionStart", "connectEnd", "requestStart", "responseStart", "responseEnd", "duration" ]

hartiming_fields = [ "name", "method", "httpVersion", "status", "mimeType", "scenario", "mahttpp_ip1", "mahttpp_port1", "mahttpp_ip2", "mahttpp_port2", "resptransfersize", "respheadersize", "respbodysize", "contentlengthheader", "contentsize", "startedDateTime", "start_delta", "blockedTime", "dnsTime", "connectTime", "sslTime", "sendTime", "waitTime", "receiveTime" ]


def createDirectory(path):
	logging.debug("Trying to create directory " + path)
	try:
		os.makedirs(path)
	except OSError as exception:
		if exception.errno != errno.EEXIST:
			raise

# Sum up the duration of timings
def sum_timings(timingslist):
	if timingslist is None or len(timingslist) < 1:
		return 0
	timingssum = 0
	for t in timingslist:
		try:
			if float(t) > 0:
				timingssum += float(t)
		except ValueError as err:
			logging.info("Could not convert to number: " + str(err))
	return timingssum

def filter_timings(timings, values, key="page"):
	if isinstance(values, str):
		values = [ values ]
	logging.debug("Filtering " + str(timings) + " by " + str(key) + ": " + str(values))

	filtered_timings = []
	for t in timings:
		if key:
			compare_item = t[key]
		else:
			compare_item = t
		if any(v in compare_item for v in values):
			filtered_timings.append(t)
	logging.debug("\n\t\tResult: " + str(filtered_timings))
	logging.debug("Filtered for " + str(key) + ": " + str(len(filtered_timings)) + "/" + str(len(timings)) + "\n")
	return filtered_timings

def sort_list(origlist, by="scenario"):
	if origlist is None:
		return None

	# Filter for everything that is not None
	returnlist = [item for item in origlist if (item is not None and item[by] is not None)]

	if any(v in by for v in ["time", "Time", "Start", "End", "dom", "duration"]):
		return sorted(returnlist, key=lambda k: float(k[by]))
	else:
		return sorted(returnlist, key=lambda k: k[by])

# Read a CSV file, return list of dicts of contents and the open file
def read_csvfile(csvfilename, fields):
	try:
		csvfile = open(csvfilename, 'r')
		csvreader = csv.DictReader(csvfile, fieldnames = fields)
		csvlist = list(csvreader)
		csvfile.close()
		return csvlist
	except Exception as e:
		print("Error with " + str(csvfilename) + ": " + str(e))
		return None


# Read logfile of HAR timings, create it first if it does not exist yet
def get_hartimings(run, pagelabel, navt):
	harfile = run + "har/" + pagelabel + ".har"
	hartimingslogfile = run + "har/" + pagelabel + ".har.log"
	har_timings = read_csvfile(hartimingslogfile, hartiming_fields)
	if har_timings is None and navt is not None:
		print("Trying to read " + harfile + " to create " + str(hartimingslogfile))
		try:
			hartimings.parsehartimings(harfile, hartimingslogfile, scenario = navt["scenario"])
			har_timings = read_csvfile(hartimingslogfile, hartiming_fields)
			if har_timings is None:
				har_timings=[]
		except Exception as err:
			print("Error getting HAR timings: " + str(err))
			return []
	return har_timings

def get_restimings(run, pagelabel):
	restimingslogfilename = run + "res/" + pagelabel + RESTIMINGS_FILENAME

	restimings = read_csvfile(restimingslogfilename, restiming_fields)
	return(restimings)

# Read all Navigation timings for a run, return as a list of dicts
def read_navtimings(run):
	navtimingslogfilename = run + NAVTIMINGS_FILENAME
	navtimings = read_csvfile(navtimingslogfilename, navtiming_fields)

	logging.debug("Navtimings: " + str(navtimings))
	return navtimings

# Get data for plotting one bar of Navigation timings
def get_one_navtiming(navtiming):
	potentialfields = navtiming_fields[6:-1]
	timediffs = [ [float(navtiming[key])] for key in potentialfields if navtiming[key] != "None" ]
	timelabels = [ key for key in potentialfields if navtiming[key] != "None" ]
	colors = [ navtiming_colors[key] for key in timelabels ]
	logging.debug("\n\t" + "\n\t".join([ tl + " " + str(navtiming[tl]) for tl in timelabels ]) + "\n")

	return (timediffs, timelabels, colors)


def find_duplicates(orig_list):
	seen = set()
	uniq = []
	dups = []
	for item in orig_list:
		if item not in seen:
			uniq.append(item)
			seen.add(item)
		else:
			dups.append(item)
	return dups

def compare_har_to_resource(har_timings, res_timings, run, pagelabel, logfile=None):
	if logfile:
		csvwriter = csv.writer(logfile, delimiter=",")

	url = "http://" + pagelabel.split("+", 1)[0]
	starttime = pagelabel.split("+", 1)[1]

	page_startedDateTime = datetime.datetime.strptime(har_timings[0]["startedDateTime"], "%Y-%m-%d+%H-%M-%S.%f")
	restimings_lookup_list = copy.deepcopy(res_timings)
	hartimings_lookup_list = copy.deepcopy(har_timings)

	smart_total_page_size = 0

	# Go through HAR timings, find matching Resource Timing for each
	for hart in har_timings:
		har_url = hart["name"]
		har_timestamp = datetime.datetime.strptime(hart["startedDateTime"], "%Y-%m-%d+%H-%M-%S.%f")
		logging.debug("Looking up Resource timing for " + har_url + ", " + str(har_timestamp))

		rest = validate_object_size.get_matching_restiming(restimings_lookup_list, har_url, har_timestamp, page_startedDateTime, match_closest=True)
		if not rest:
			#if har_url not in dups_in_har:
			logging.info("In HAR, but not in Res (status " + str(hart["status"]) + "): " + str(har_url))

			# Add this object to total page size, using the "more accurate" metrics if they exist
			try:
				contentlength_from_header = int(hart["contentlengthheader"])
			except ValueError:
				contentlength_from_header = 0
			respbodysize = int(hart["respbodysize"])
			if contentlength_from_header > 0:
				smart_total_page_size += contentlength_from_header
			elif respbodysize > 0 and hart["status"][0] != "3":
				# Only count logged response body size if this is not a redirect (status 3xx)
				# because the logged response body size is often broken for redirects
				smart_total_page_size += respbodysize

			if logfile:
				csvwriter.writerow([url, starttime, hart["status"], hart["httpVersion"], "in_har_not_in_res", hart["resptransfersize"], hart["respbodysize"], hart["respheadersize"], hart["contentlengthheader"], hart["contentsize"], "NA", "NA", har_url.replace(",", "")])
		else:
			logging.debug("In both -- har sizes: " + str(hart["respbodysize"]) + " (" + str(int(hart["respbodysize"]) - int(hart["respheadersize"])) + " without header), " + str(hart["contentsize"]) + " -- resource sizes: " + str(rest["encodedBodySize"]) + ", " + str(rest["decodedBodySize"]) + " " + har_url)
			restimings_lookup_list.remove(rest)

			# Add this object to total page size, using the "more accurate" metrics if they exist
			try:
				contentlength_from_header = int(hart["contentlengthheader"])
			except ValueError:
				contentlength_from_header = 0
			respbodysize = int(hart["respbodysize"])
			resource_bodysize = int(rest["encodedBodySize"])
			if contentlength_from_header > 0:
				smart_total_page_size += contentlength_from_header
			elif resource_bodysize > 0 and hart["status"][0] != "3":
				smart_total_page_size += resource_bodysize
			elif respbodysize > 0 and hart["status"][0] != "3":
				smart_total_page_size += respbodysize

			if logfile:
				csvwriter.writerow([url, starttime, hart["status"], hart["httpVersion"], "in_both", hart["resptransfersize"], hart["respbodysize"], hart["respheadersize"], hart["contentlengthheader"], hart["contentsize"], rest["encodedBodySize"], rest["decodedBodySize"], har_url.replace(",", "")])

	for rest in res_timings:
		res_url = rest["name"]
		res_timestamp = page_startedDateTime + datetime.timedelta(milliseconds = float(rest["starttime"]))
		logging.debug("Looking up HAR timing for " + res_url + ", " + str(res_timestamp))
		hart = validate_object_size.get_matching_hartiming(hartimings_lookup_list, res_url, res_timestamp, statuscode_to_look_for="", use_starttime=True, match_closest=True)
		if not hart:
			logging.info("In Res, but not in HAR: " + str(res_url))

			# Add this object to total page size -- this is the only size we have in this case
			smart_total_page_size += int(rest["encodedBodySize"])

			if logfile:
				csvwriter.writerow([url, starttime, -123, ("http/2.0" if rest["nextHopProtocol"] == "h2" else rest["nextHopProtocol"]), "in_res_not_in_har", "NA", "NA", "NA", "NA", "NA", rest["encodedBodySize"], rest["decodedBodySize"], res_url.replace(",", "")])
		else:
			# Do not match the same HAR timing twice
			hartimings_lookup_list.remove(hart)

	return smart_total_page_size

# Object Index: Time-Integral metrics to capture page load over time
#
# Here we compute the integral of individual object load times and total numbers of objects
def compute_object_index(object_end_times, starttime):
	objectIndex = 0
	if starttime >= 0 and len(object_end_times) > 0:
		logging.debug("starttime = " + str(starttime))
		for obj in object_end_times:
			objectIndex += (obj - starttime) * (1 / len(object_end_times))
			logging.debug("Object Index += (" + str(round(obj, 3)) + " - " + str(round(starttime, 3)) + ") * (1 / " + str(len(object_end_times)) + ")")
	else:
		objectIndex = "NA"
	logging.debug("Final Object Index = " + str(objectIndex))
	return objectIndex

# Byte Index: Time-Integral metrics to capture page load over time
#
# Here we compute the integral of individual object load times and object sizes
def compute_byte_index(object_end_times, object_sizes, starttime):
	byteIndex = 0
	totalSize = sum(object_sizes)
	if starttime >= 0 and len(object_end_times) > 0 and totalSize > 0:
		logging.debug("starttime = " + str(starttime))
		for (i, obj) in enumerate(object_end_times):
			byteIndex += (obj - starttime) * (object_sizes[i] / totalSize)
			logging.debug("Byte Index += (" + str(round(obj, 3)) + " - " + str(round(starttime, 3)) + ") * (" + str(object_sizes[i]) + " / " + str(totalSize) + ")")
	else:
		byteIndex = "NA"
	logging.debug("Final Byte Index = " + str(byteIndex))
	return byteIndex



def compute_timings(navtimings, run, log=False):

	compare_logfile = None

	if log:
		# Logfile for timings and per-page statistics
		try:
			if os.path.exists(run + LOGFILENAME):
				os.remove(run + LOGFILENAME)
				print("Deleted old " + run + LOGFILENAME)
		except Exception as err:
			print("Could not delete " + run + LOGFILENAME + ": " + str(err))
		try:
			csvfile = open(run + LOGFILENAME, "w", newline='')
		except TypeError as e:
			print("Error opening " + run + LOGFILENAME + ": " + str(e))
			csvfile = open(run + LOGFILENAME, 'wb')
		csvwriter = csv.writer(csvfile, delimiter=",")

		# Logfile for comparing HAR objects to Resource Timing objects
		logfilename = run + "compare_har_res.log"
		try:
			if os.path.exists(logfilename):
				os.remove(logfilename)
				print("Deleted old " + logfilename)
		except Exception as err:
			print("Could not delete " + logfilename + ": " + str(err))
		try:
			compare_logfile = open(logfilename, "w", newline='')
		except TypeError as e:
			print("Error opening " + logfilename + ": " + str(e))
			compare_logfile = open(logfilename, 'wb')


	# For each Navigation Timing, also get HAR file content and resource timings
	for navt in navtimings:
		pagelabel = str(navt["page"].split('/')[2] + "+" + navt["starttime"])
		print("\nLogging Timings for " + run + pagelabel + "...")

		# Open HAR file to read ContentLoadTime and OnLoadTime logged there

		harfilename = run + "har/" + pagelabel + ".har"
		try:
			harfile = open(harfilename, 'r')
			harfilecontents = json.loads(harfile.read())
		except Exception as err:
			print("Could not read " + harfilename + ":" + str(err))
			harfilecontents = None

		try:
			harStartTime = harfilecontents["log"]["pages"][0]["startedDateTime"]
		except ValueError as err:
			print("Could not get start time from " + harfilename + ": " + str(err))
			harStartTime = "NA"
		try:
			harContentLoadTime = float(harfilecontents["log"]["pages"][0]["pageTimings"]["onContentLoad"])
		except ValueError as err:
			print("Could not get onContentLoad time from " + harfilename + ": " + str(err))
			harContentLoadTime = "NA"
		try:
			harOnLoadTime = float(harfilecontents["log"]["pages"][0]["pageTimings"]["onLoad"])
		except ValueError as err:
			print("Could not get onLoad time from " + harfilename + ": " + str(err))
			harOnLoadTime = "NA"
		harfile.close()


		try:
			har_timings = get_hartimings(run, pagelabel, navt)
		except Exception as err:
			print("Could not get HAR timings: " + str(err))
			har_timings = []
			max_hartimings = "NA"

		# Process HAR timings
		if har_timings:

			harNumberOfRequests = len(har_timings)
			harFinishedAfterOnLoad = 0

			harNoReply = 0
			harStatus1xx = 0
			harStatus200 = 0
			harStatusOther2xx = 0
			harStatus3xx = 0
			harStatus4xx = 0
			harStatus5xx = 0
			harUnknownStatus = 0
			harNonFailedRequests = 0 	# between 100 and 399

			sum_of_respbodysize = 0
			sum_of_contentlength = 0
			sum_of_contentsize = 0
			sum_of_bodyorcontent = 0
			sum_of_transfersize = 0
			respbodysizes_counted = 0
			contentsizes_counted = 0

			harFirst200Starttime = -1
			harRedirectsBeforeFirst200 = 0
			harLastRequestStartBeforeOnLoad = 0
			harLastResourceEndBeforeOnLoad = 0

			object_finish_times = []
			object_finish_times_bodysize = []
			object_finish_times_bodyorcontent = []
			object_finish_times_transfersize = []
			object_sizes_har_bodysize = []
			object_sizes_bodyorcontent = []
			object_sizes_transfersize = []

			har_timings_before_onload = []
			for hart in har_timings:

				harStatus = int(hart["status"])

				# Compute finish time of this resource/object
				try:
					starttime = float(hart["start_delta"])
					endtime = sum_timings([starttime, hart["blockedTime"], hart["dnsTime"], hart["connectTime"], hart["sendTime"], hart["waitTime"], hart["receiveTime"]])
				except Exception as err:
					if harStatus == 0:
						logging.debug("Resource with no end time got no reply: " + str(hart["name"]))
						endtime = starttime
					elif harStatus < 0:
						logging.warn("Resource got an unknown status code and no timings: " + str(hart["name"]))
						endtime = starttime
					else:
						print("Error with " + str(hart))
						raise(err)

				if harOnLoadTime is None or harOnLoadTime == "NA":
					# The browser did not log an onLoad event -- every logged resource is before onLoad then
					har_timings_before_onload.append(hart)
				elif endtime > harOnLoadTime:
					harFinishedAfterOnLoad += 1
					logging.debug("Resource finished after onLoad -- skipping " + str(hart["name"]))
					continue
				else:
					har_timings_before_onload.append(hart)

				if harStatus == 0:
					harNoReply += 1
				elif harStatus >= 100 and harStatus < 200:
					harStatus1xx += 1
				elif harStatus == 200:
					harStatus200 += 1
					if harFirst200Starttime == -1:
						harFirst200Starttime = starttime
						harRedirectsBeforeFirst200 = harStatus3xx
				elif harStatus >= 201 and harStatus < 300:
					harStatusOther2xx += 1
				elif harStatus >= 300 and harStatus < 400:
					harStatus3xx += 1
				elif harStatus >= 400 and harStatus < 500:
					harStatus4xx += 1
				elif harStatus >= 500 and harStatus < 600:
					harStatus5xx += 1
				elif harStatus < 0:
					harUnknownStatus += 1
				else:
					raise ValueError("Invalid HTTP Status code " + str(harStatus))

				if starttime > harLastRequestStartBeforeOnLoad and harStatus != 0:
					harLastRequestStartBeforeOnLoad = starttime

				if endtime > harLastResourceEndBeforeOnLoad and harStatus != 0:
					harLastResourceEndBeforeOnLoad = endtime

				# If this is a successful object after the first 200 (or is the first 200)
				# add object finish time to list
				# so we can compute Object Index and Byte Index later
				if harFirst200Starttime >= 0 and harStatus >= 100 and harStatus < 400:
					object_finish_times.append(endtime)

				# Various possibilities for "object sizes":

				# What got logged as "response body size" in the HAR file (possibly compressed)
				respbodysize = int(hart["respbodysize"])
				if respbodysize <= 0:
					respbodysize = 0
				else:
					respbodysizes_counted += 1
					if harFirst200Starttime > 0 and harStatus >= 100 and harStatus < 400:
						# Count body size of successful objects to compute ByteIndex later
						object_sizes_har_bodysize.append(respbodysize)
						object_finish_times_bodysize.append(endtime)

				# What was in the HTTP response "Content-Length" header
				try:
					contentlength_from_header = int(hart["contentlengthheader"])
				except ValueError:
					contentlength_from_header = 0
				if contentlength_from_header == -1:
					contentlength_from_header = 0
				# What got logged as "content size" in the HAR file (possibly non-compressed)
				contentsize = int(hart["contentsize"])
				if contentsize == -1:
					contentsize = 0
				else:
					contentsizes_counted += 1

				try:
					# What got logged as "transfer size" in the HAR file (header + body)
					transfersize = int(hart["resptransfersize"])
					if transfersize > 0:
						if harFirst200Starttime > 0 and harStatus >= 100 and harStatus < 400:
							# Count transfer size of successful objects to compute ByteIndex later
							object_sizes_transfersize.append(transfersize)
							object_finish_times_transfersize.append(endtime)
				except ValueError:
					transfersize = 0

				# To compute "sum of object sizes", we can just sum up any of these...
				sum_of_respbodysize += respbodysize
				sum_of_contentlength += contentlength_from_header
				sum_of_contentsize += contentsize
				sum_of_transfersize += transfersize

				# ... or try to be smarter:
				# if content-length exists, use it, otherwise use respbodysize
				# Count Content-Length or body size of successful objects to compute ByteIndex later
				if contentlength_from_header > 0:
					sum_of_bodyorcontent += contentlength_from_header
					object_sizes_bodyorcontent.append(contentlength_from_header)
					object_finish_times_bodyorcontent.append(endtime)
				elif respbodysize > 0:
					sum_of_bodyorcontent += respbodysize
					object_sizes_bodyorcontent.append(respbodysize)
					object_finish_times_bodyorcontent.append(endtime)

			harNonFailedRequests = harStatus1xx + harStatus200 + harStatusOther2xx + harStatus3xx

			harObjectIndex = compute_object_index(object_finish_times, harFirst200Starttime)
			harByteIndexBodysize = compute_byte_index(object_finish_times_bodysize, object_sizes_har_bodysize, harFirst200Starttime)
			harByteIndexBodyorcontent = compute_byte_index(object_finish_times_bodyorcontent, object_sizes_bodyorcontent, harFirst200Starttime)
			harByteIndexTransfersize = compute_byte_index(object_finish_times_transfersize, object_sizes_transfersize, harFirst200Starttime)

			print("\nHAR file summary:\n\t\t" + str(harNumberOfRequests) + " Requests\n\t\t" + str(harFinishedAfterOnLoad) + " of which finished after onLoad\n\t\t" + str(harNoReply) + " of which had no reply\n\n\t\t" + str(harStatus1xx) + " Status 1xx\n\t\t" + str(harStatus200) + " Status 200\n\t\t" + str(harStatusOther2xx) + " Status 2xx other than 200\n\t\t" + str(harStatus3xx) + " Status 3xx\n\t\t" + str(harStatus4xx) + " Status 4xx\n\t\t" + str(harStatus5xx) + " Status 5xx\n\t\t" + str(harUnknownStatus) + " unknown status\n\n\t\t" + str(harNonFailedRequests) + " non-failed requests before onLoad (100 <= status < 400)")
			print("\n\t\tfirst200StartTime:\t\t\t" + str(harFirst200Starttime) + "\n\t\tRedirects before first 200:\t\t" + str(harRedirectsBeforeFirst200) + "\n\t\tLast Request Start Before OnLoad:\t" + str(harLastRequestStartBeforeOnLoad) + "\n\t\tLast Resource end before onLoad:\t" + str(harLastResourceEndBeforeOnLoad) + "\n\t\tonLoad:\t\t\t\t\t" + str(harOnLoadTime))
			print("\n\t\tSum of response body sizes:\t" + str(sum_of_respbodysize) + " (counted " + str(respbodysizes_counted) + ")\n\t\tSum of content lengths:\t\t" + str(sum_of_contentlength) + "\n\t\tSum of content size:\t\t" + str(sum_of_contentsize) + " (counted " + str(contentsizes_counted) + ")\n\t\tSum of body or contentlength:\t" + str(sum_of_bodyorcontent) + " (counted " + str(len(object_sizes_bodyorcontent)) + ")")
			print("\n\t\tObject Index:\t\t\t" + str(harObjectIndex) + " (counted " + str(len(object_finish_times)) + ")\n\t\tByte Index (body size):\t\t" + str(harByteIndexBodysize) + " (counted " + str(len(object_sizes_har_bodysize)) + ")\n\t\tByte Index (Content-Length or body): " + str(harByteIndexBodyorcontent) + " (counted " + str(len(object_sizes_bodyorcontent)) + ")\n\t\tByte Index (TransferSize):\t" + str(harByteIndexTransfersize) + " (counted " + str(len(object_sizes_transfersize)) + ")")

		else:
			# No HAR timings - no valid values
			harNumberOfRequests = "NA"
			harFinishedAfterOnLoad = "NA"
			harNoReply = "NA"
			harStatus1xx = "NA"
			harStatus200 = "NA"
			harStatusOther2xx = "NA"
			harStatus3xx = "NA"
			harStatus4xx = "NA"
			harStatus5xx = "NA"
			harUnknownStatus = "NA"
			harNonFailedRequests = "NA"

			sum_of_respbodysize = "NA"
			sum_of_contentlength = "NA"
			sum_of_contentsize = "NA"
			sum_of_bodyorcontent = "NA"

			harFirst200Starttime = "NA"
			harRedirectsBeforeFirst200 = "NA"
			harLastRequestStartBeforeOnLoad = "NA"
			harLastResourceEndBeforeOnLoad = "NA"

			harObjectIndex = "NA"
			harByteIndexBodysize = "NA"
			harByteIndexBodyorcontent = "NA"

			har_timings = []
			max_hartiming = "NA"


		# Process Resource Timings
		try:
			res_timings = read_csvfile(run + "res/" + pagelabel + RESTIMINGS_FILENAME, restiming_fields)
			if res_timings:

				resNumberOfResources = len(res_timings)
				resFinishedAfterOnLoad = 0
				resLastResourceEndBeforeOnLoad = 0

				sum_of_resource_encoded = 0
				sum_of_resource_decoded = 0

				resObjectIndex = 0
				resByteIndex = 0

				object_end_times_res = []
				res_timings_before_onload = []
				object_sizes_res = []

				for rest in res_timings:
					# Find last resource load end time before onLoad event
					endtime = float(rest["responseEnd"])
					if float(navt["loadEventStart"]) > 0 and endtime > float(navt["loadEventStart"]):
						logging.debug("Resource load ended after load Event started -- skipping " + str(rest["name"]))
						resFinishedAfterOnLoad += 1
						continue
					else:
						res_timings_before_onload.append(rest)
					if endtime > resLastResourceEndBeforeOnLoad:
						resLastResourceEndBeforeOnLoad = endtime
					# Sum resource sizes before onLoad
					sum_of_resource_encoded += int(rest["encodedBodySize"])
					sum_of_resource_decoded += int(rest["decodedBodySize"])

					# Object end times (for Object and Byte Index) and object sizes (for Byte Index)
					object_end_times_res.append(endtime)
					object_sizes_res.append(int(rest["encodedBodySize"]))

				resNumberOfResourcesFinishedBeforeOnLoad = resNumberOfResources - resFinishedAfterOnLoad
				resObjectIndex = compute_object_index(object_end_times_res, float(navt["fetchStart"]))
				resByteIndex = compute_byte_index(object_end_times_res, object_sizes_res, float(navt["fetchStart"]))

				print("\nResource timings summary:\n\t\t" + str(resNumberOfResources) + " Requests\n\t\t" + str(resFinishedAfterOnLoad) + " of which finished after onLoad\n\n\t\t" + str(resNumberOfResourcesFinishedBeforeOnLoad) + " Resources finished before OnLoad\n\t\tLast Resource end before onLoad:\t" + str(resLastResourceEndBeforeOnLoad) + "\n\n\t\tSum of encoded sizes:\t\t" + str(sum_of_resource_encoded) + "\n\t\tSum of decoded sizes:\t\t" + str(sum_of_resource_decoded))
				print("\n\t\tObject Index:\t\t\t" + str(resObjectIndex) + " (counted " + str(len(object_end_times_res)) + ")\n\t\tByte Index:\t\t\t" + str(resByteIndex))
			else:
				resNumberOfResources = "NA"
				resFinishedAfterOnLoad = "NA"
				resLastResourceBeforeOnLoad = "NA"

				resObjectIndex = "NA"
				resByteIndex = "NA"


			smart_total_page_size = compare_har_to_resource(har_timings_before_onload, res_timings_before_onload, run, pagelabel, logfile=compare_logfile)
			print("\n\t\tSmart total page size:\t\t" + str(smart_total_page_size))

		except Exception as err:
			print("Something went wrong with restimings: " + str(err))

			resNumberOfResources = "NA"
			resFinishedAfterOnLoad = "NA"
			resLastResourceBeforeOnLoad = "NA"
			resNumberOfResourcesFinishedBeforeOnLoad = "NA"
			smart_total_page_size = "NA"

			resObjectIndex = "NA"
			resByteIndex = "NA"

		if log:
			csvwriter.writerow([navt["page"], navt["scenario"], navt["starttime"], navt["fetchStart"], navt["responseStart"], navt["domInteractive"], navt["domContentLoadedEventStart"], navt["domContentLoadedEventEnd"], navt["domComplete"], navt["loadEventStart"], navt["loadEventEnd"], navt["firstPaint"],
			str(harNumberOfRequests), str(harFinishedAfterOnLoad), str(harNoReply), str(harStatus1xx), str(harStatus200), str(harStatusOther2xx), str(harStatus3xx), str(harStatus4xx), str(harStatus5xx), str(harUnknownStatus), str(harNonFailedRequests), str(harStartTime),
			str(harFirst200Starttime), str(harRedirectsBeforeFirst200), str(harLastRequestStartBeforeOnLoad), str(harLastResourceEndBeforeOnLoad), str(harOnLoadTime), str(harContentLoadTime),
			str(harObjectIndex), str(harByteIndexBodysize), str(harByteIndexBodyorcontent), str(harByteIndexTransfersize),
			str(sum_of_respbodysize), str(sum_of_contentlength), str(sum_of_contentsize), str(sum_of_bodyorcontent), str(sum_of_transfersize),
			str(resNumberOfResources), str(resFinishedAfterOnLoad), str(resNumberOfResourcesFinishedBeforeOnLoad), str(resLastResourceEndBeforeOnLoad),
			str(sum_of_resource_encoded), str(sum_of_resource_decoded),
			str(resObjectIndex), str(resByteIndex),
			str(smart_total_page_size)
			])

	if log:
		csvfile.close()

		print("Logged to " + logfilename)
		compare_logfile.close()


def navtiming_exists(run, url, starttime, navtimings):
	if navtimings is None:
		return False
	for navt in navtimings:
		print("Looking for " + url + " and " + str(starttime) + " in navt with " + str(navt["page"]) + " and " + str(navt["starttime"]))
		if url == navt["page"] and navt["starttime"] == starttime:
			logging.debug("Found navtiming for " + str(url) + "! " + str(navt))
			return navt
	print("Did NOT find navtiming for " + str(url) + " in " + run + "!")
	return False

def hartimings_exist(run, url, navt):
	pagelabel = navt["page"].split('/')[2] + "+" + navt["starttime"]
	hartimings = get_hartimings(run, pagelabel, navt)

	if hartimings:
		logging.info("Got HAR file for " + str(url) + " with " + str(len(hartimings)) + " timings")
		return True
	else:
		logging.info("Did NOT get any HAR file for " + str(url))
		return False

def restimings_exist(run, url, navt):
	pagelabel = navt["page"].split('/')[2] + "+" + navt["starttime"]
	restimings = get_restimings(run, pagelabel)

	if restimings:
		logging.info("Got Resource Timings file for " + str(url) + " with " + str(len(restimings)) + " timings")
		return True
	else:
		logging.info("Did NOT get any Resource Timings for " + str(url))
		return False

def get_packets(run, url, starttime):
	dump_packets(run, url, starttime)

	domainname = url.split('/')[2]
	filepath = run + "pcap/" + domainname + "+" + starttime + "_packets.log"

	try:
		packetsfile = open(filepath, 'r')
	except Exception as err:
		print("Could not open file " + str(filepath) + ": " + str(err))
		return None
	try:
		packets = [ p.rstrip() for p in packetsfile ]
	except Exception as err:
		print("Could not read packets file " + str(filepath) + ": " + str(err))
		packetsfile.close()
		return None

	packetsfile.close()
	return packets

def dump_packets(run, url, starttime):
	domainname = url.split('/')[2]

	filepath = run + "pcap/" + domainname + "+" + starttime + "_packets.log"
	print("Checking if path exists: " + filepath)
	if os.path.exists(filepath):
		print("File already exists for " + str(domainname) + "!")
		return()

	DUMP_TRACE_SCRIPT = "./get_trace_for_timestamps.sh"

	starttimings = read_starttimings(run)
	starttime_to_match = starttime.replace("+", " ").replace("-", ":").replace(":", "-", 2)

	for index, startt in enumerate(starttimings):
		if startt["url"] == url and startt["starttime"] == starttime_to_match:
			#print("Found " + url + " at index " + str(index) + ", started at " + str(startt["starttime"]))
			timestamp1 = startt["starttime"]
			try:
				nextpage = starttimings[index + 1]
				timestamp2 = nextpage["starttime"]
			except IndexError:
				# This is the last URL in starttimings - make the second timestamp 33 seconds later
				timestamp2 = datetime.datetime.strftime(datetime.datetime.strptime(timestamp1, "%Y-%m-%d %H:%M:%S.%f") + datetime.timedelta(seconds=33), "%Y-%m-%d %H:%M:%S.%f")
			#print("Next page " + nextpage["url"] + " at index " + str(index + 1) + ", started at " + str(nextpage["starttime"]))
			break

	print("Running " + str(DUMP_TRACE_SCRIPT) + " " + run + " " + domainname + " " + timestamp1 + " " + timestamp2)
	subprocess.run(DUMP_TRACE_SCRIPT + " "+ run + " " +  domainname + " \"" +  timestamp1 + "\" \"" + timestamp2 + "\"", shell=True)

def analyze_failed_page_load(run, url, starttime, plotlabel, navt):
	print("Analyzing failed page load for " + plotlabel)
	if not navt:
		# Does navtiming exist in failed_navtimings.log?
		navtimingslogfilename = run + "failed_" + NAVTIMINGS_FILENAME
		try:
			navtimings = read_csvfile(navtimingslogfilename, navtiming_fields)
		except Exception as err:
			print("File " + navtimingslogfilename + " does not exist!")
			navtimings = None

		navt = navtiming_exists(run, url, starttime, navtimings)
		if navt:
			print("Yes, found failed navtimings: " + str(navt))
		else:
			print("No, did not find navtimings")

	latest_event = None
	if navt:
		for event in navtiming_fields[6:-1]:
			if float(navt[event]) > 0:
				latest_event = event
		print("Latest event: " + str(latest_event))

	packets = get_packets(run, url, starttime)
	if packets is not None:
		print("Got " + str(len(packets)) + " packets")

		ipv4addr = re.compile("[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}")
		ipv6part = re.compile("[0-9a-e]{1,4}\:[0-9a-e]{1,4}")

		# Look for DNS replies in the trace - excluding known replies that do not belong to this page load
		dnsreplies = [ p for p in packets if ("eth:ethertype:ip:udp:dns" in p and ipv4addr.search(p[75:]) or ipv6part.search(p[75:])) and not "search.services.mozilla.com" in p ]
		print("\tDNS replies:\t\t" + str(len(dnsreplies)))

		httppackets = [ p for p in packets if ("eth:ethertype:ip:tcp:http," in p or "eth:ethertype:ip:tcp:ssl:http," in p) and not "firefox" in p ]
		https_packets = [ p for p in httppackets if "eth:ethertype:ip:tcp:ssl:http," in p ]
		ssl_packets = [ p for p in packets if "eth:ethertype:ip:tcp:ssl" in p ]

		print("\tHTTP packets:\t\t" + str(len(httppackets)))
		print("\tof which HTTPS:\t\t" + str(len(https_packets)))
		http200packets = [ p for p in httppackets if ",200," in p ]
		http301or302packets = [ p for p in httppackets if ",301," in p or ",302," in p ]
		httpGETpackets = [ p for p in httppackets if ",GET," in p ]
		print("\tHTTP GET:\t\t" + str(len(httpGETpackets)))
		print("\tHTTP 301 or 302:\t" + str(len(http301or302packets)))
		print("\tHTTP 200:\t\t" + str(len(http200packets)))
		num_dnsreplies = len(dnsreplies)
		num_ssl = len(ssl_packets)
		num_http = len(httppackets)
		num_https = len(https_packets)
		num_httpGET = len(httpGETpackets)
		num_http301or302 = len(http301or302packets)
		num_http200 = len(http200packets)
	else:
		print("Could not read packets for " + str(url) + " at " + str(starttime) + "!")
		num_dnsreplies = "NA"
		num_ssl = "NA"
		num_http = "NA"
		num_https = "NA"
		num_httpGET = "NA"
		num_http301or302 = "NA"
		num_http200 = "NA"

	return [ latest_event, num_dnsreplies, num_ssl, num_http, num_https, num_httpGET, num_http301or302, num_http200 ]

def read_workloadfile(run):
	workloadfilename = glob.glob(run + "urlfile-*")[0]
	if workloadfilename:
		print("Original workload file(s): " + str(workloadfilename))
		try:
			workloadfile = open(workloadfilename, 'r')
		except Exception as err:
			print("Could not open workload file " + str(workloadfilename) + ": " + str(err))
			return None
		try:
			orig_workload = [ url.rstrip() for url in workloadfile ]
		except Exception as err:
			print("Could not read workload file " + str(workloadfilename) + ": " + str(err))
			workloadfile.close()
			return None

# Try to read the log file of URLs and timestamp when their page load started
# If this file does not exist yet, try to create it using a shell script
# If this fails, try to read the original workload URL file from the same dir
def read_starttimings(run):
	starttimingsfilename = run + "starttimings.log"

	if not os.path.exists(starttimingsfilename):
		try:
			GET_STARTTIMESTAMP_SCRIPT = "get_starttimestamp_from_workload_output.sh"
			print("Getting starttimings for " + run)
			subprocess.run(["./" + GET_STARTTIMESTAMP_SCRIPT, run])
		except Exception as err:
			print("Could not run " + GET_STARTTIMESTAMP_SCRIPT + ": " + str(err))

	starttimings = []
	if os.path.exists(starttimingsfilename):
		print("Starttimings file: " + str(starttimingsfilename))
		starttimings = read_csvfile(starttimingsfilename, ["url", "starttime"])

	if not starttimings:
		# Fall back to just reading the original workload file
		orig_workload = read_workloadfile(run)
		if orig_workload:
			starttimings = [{ "url": u, "starttime" : "" } for u in orig_workload ]
			print("Got URLs without starttimestamps from workload file")

	return starttimings

def find_first_url_in_starttimings(starttimings, timestamp):
	for (index, startt) in enumerate(starttimings):
		if timestamp >= datetime.datetime.strptime(startt["starttime"], "%Y-%m-%d %H:%M:%S.%f") and index == len(starttimings)-1 or timestamp < datetime.datetime.strptime(starttimings[index+1]["starttime"], "%Y-%m-%d %H:%M:%S.%f"):
			return (startt["url"], startt["starttime"])
	return (None, None)

def check_which_were_successful(run, plotlabel, navtimings, workload_filter=None, log=False):
	if log:
		logfilename = run + "success_or_fail.log"
		try:
			if os.path.exists(logfilename):
				os.remove(logfilename)
				print("Deleted old " + logfilename)
		except Exception as err:
			print("Could not delete " + logfilename + ": " + str(err))
		try:
			csvfile = open(logfilename, "w", newline='')
		except TypeError as e:
			print("Error opening " + logfilename + ": " + str(e))
			csvfile = open(logfilename, 'wb')
		csvwriter = csv.writer(csvfile, delimiter=",")
		# Write header fields
		csvfile.write("page,starttime,does_navtiming_exist,does_restiming_exist,does_harfile_exist,last_event_in_failed_navtiming,num_dnsreplies,num_ssl,num_http,num_https,num_httpGET,num_http301or302,num_http200\n")

	starttimings = read_starttimings(run)

	try:
		if workload_filter:
			starttimings = filter_timings(starttimings, workload_filter, key = "url")

		logging.debug("\tOriginal URLs: " + str([w["url"] for w in starttimings]))
		no_navtiming = []
		no_restiming = []
		no_hartiming = []
		navtiming_but_no_onload = []
		successful_workload = []

		# For each original workload, figure out it load successful
		for st in starttimings:
			url = st["url"]
			starttime = st["starttime"].replace(" ", "+").replace(":", "-")
			logging.debug("URL: " + url + ", starttime: " + str(starttime))

			pagelabel = url + "+" + starttime

			navt = navtiming_exists(run, url, starttime, navtimings)
			rest = True
			har = True
			analysis_of_failed = []

			if navt:
				if not restimings_exist(run, url, navt):
					no_restiming.append(pagelabel)
					rest = False
				if not hartimings_exist(run, url, navt):
					no_hartiming.append(pagelabel)
					har = False
			else:
				rest = False
				har = False
				no_navtiming.append(pagelabel)

			if not navt or not rest or not har:
				analysis_of_failed = analyze_failed_page_load(run, url, starttime, plotlabel, navt)
				print("Failed " + str(pagelabel))
			elif float(navt["loadEventEnd"]) < 0:
				navtiming_but_no_onload.append(pagelabel)
				latest_event = None
				for event in navtiming_fields[6:-1]:
					if float(navt[event]) > 0:
						latest_event = event
				print("No onLoad -- latest event: " + str(latest_event))
				analysis_of_failed = [ latest_event ]
			else:
				successful_workload.append(pagelabel)

			if log:
				csvwriter.writerow([url, starttime,
					( ("navtiming" if float(navt["loadEventEnd"]) > 0 else "navtiming_but_no_onload") if navt else "no_navtiming"),
					( "restiming" if rest else "no_restiming"),
					( "harfile" if har else "no_harfile")] +
					analysis_of_failed
				)
			#print("")

		print("No Navtiming for " + str(len(no_navtiming)) + ": " + str(no_navtiming))
		print("Navtiming, but no Resource Timings for " + str(len(no_restiming)) + ": " + str(no_restiming))
		print("Navtiming, but no HAR for " + str(len(no_hartiming)) + ": " + str(no_hartiming))
		print("Navtiming, but no onLoad for " + str(len(navtiming_but_no_onload)) + ": " + str(navtiming_but_no_onload))
		print("Successful: " + str(len(successful_workload)) + "/" + str(len(starttimings)) )

		if log:
			csvfile.close()
		return successful_workload
	except Exception as err:
		raise(err)

# Process runs, call plotting functions on each of them
def main(argv=[]):
	runfilter=None
	logtofile = True
	if (len(argv) > 1):
		runfilter = argv[1]
	if (len(argv) > 2 and argv[2] != "None" and argv[2] != "all"):
		workload = argv[2].split(",")
	else:
		workload = None
	if (len(argv) > 3):
		print("Trying to set log level to " + argv[4])
		root = logging.getLogger()
		if "debug" in argv[3]:
			root.setLevel(logging.DEBUG)
			logging.debug("Log level: Debug")
		elif "info" in argv[3]:
			root.setLevel(logging.INFO)
			logging.info("Log level: Info")
		elif "pleaselog" in argv[3]:
			logtofile = True

	print("Getting runs in " + RUNDIR + "run-*")
	runs = glob.glob(RUNDIR + "run-*")
	if runfilter is not None:
		runs = [ r for r in runs if runfilter in r ]
	print("Runs: " + str(runs) + "\n")
	for run in runs:
		if run[-1] != "/":
			run = run + "/"

		createDirectory(run + "plots/")
		runlabel= list(filter(None, run.split('/')))[-1]
		plotlabel = runlabel

		# Get all Navigation Timings as list of dicts
		navtimings = read_navtimings(run)

		if workload is not None:
			navtimings = filter_timings(navtimings, workload, key="page")
			plotlabel = '_'.join(workload) + '_' + plotlabel

		if navtimings is None or len(navtimings) < 1:
			print("Could not get navtimings for " + run + '...' + ("" if workload is None else ", " + str(workload)))
			#continue

		successful_workload = check_which_were_successful(run, plotlabel, navtimings, workload_filter = workload, log=logtofile)

		# Only plot and log timings for successful runs, i.e.:
		# There exist Navigation Timings, Resource Timings, and a HAR file
		successful_timestamps = [ s.split("+", 1)[1] for s in successful_workload ]
		navtimings = filter_timings(navtimings, successful_timestamps, "starttime")

		compute_timings(navtimings, run, log=logtofile)
		if logtofile:
			print("!!! Logged " + run + "!!!")

if __name__ == "__main__":
	main(sys.argv)
