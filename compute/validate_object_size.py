#!/usr/bin/env python3
#
# Author: Theresa Enghardt (theresa@inet.tu-berlin.de)
# 2018

# This script computes object sizes from a packet capture trace
# and compare them to HAR and Resource Timings

import os
import sys
import glob
import subprocess
import logging
import csv
import re
import datetime
import computetimings

RUNDIR="../testdata/"

CAPTURE_FILE_NAME = "local\:any.pcap"

# For debugging
#ADDITIONAL_TSHARK_FILTER = " \"frame.number >= 0 and frame.number <= 1000\" "
ADDITIONAL_TSHARK_FILTER = ""

URI_TO_DEBUG=""
#URI_TO_DEBUG = "/c_fill,w_90,h_60,g_faces,q_70/images/20180918/2d02caf9d1a043f38ce843951318e2fa.jpeg"


# From list of HAR timings, as read from log file, get the one which matches this URI and timestamp
def get_matching_hartiming(hartimings, uri_to_look_for, timestamp_to_look_for, statuscode_to_look_for="", use_starttime=False, match_closest=False):
	if hartimings is None or len(hartimings) == 0:
		return None
	logging.debug("Looking for HAR timings for " + uri_to_look_for)
	candidates = []
	for hart in hartimings:
		har_uri = hart["name"]
		if har_uri == uri_to_look_for and (hart["status"] == statuscode_to_look_for or statuscode_to_look_for == ""):
			logging.debug("HAR: " + str(hart))
			startedDateTime = datetime.datetime.strptime(hart["startedDateTime"], "%Y-%m-%d+%H-%M-%S.%f")
			if not use_starttime:
				pre_send_duration = datetime.timedelta(milliseconds = 0)
				try:
					# See if this HAR timing is within timing range +- 1 ms (due to rounding)
					pre_send_duration = datetime.timedelta(milliseconds=computetimings.sum_timings([hart["blockedTime"], hart["dnsTime"], hart["connectTime"], hart["sslTime"]]) - 1)
					post_send_duration = datetime.timedelta(milliseconds=computetimings.sum_timings([hart["blockedTime"], hart["dnsTime"], hart["connectTime"], hart["sslTime"], hart["sendTime"]]) + 1)
				except ValueError:
					# No timings available - not taking this object
					logging.debug("No timings for " + str(hart))
					continue
				pre_send_time = startedDateTime + pre_send_duration
				post_send_time = startedDateTime + post_send_duration
			else:
				pre_send_time = startedDateTime - datetime.timedelta(milliseconds = 1)
				post_send_time = startedDateTime + datetime.timedelta(milliseconds = computetimings.sum_timings([hart["dnsTime"], hart["connectTime"], hart["sslTime"], hart["sendTime"], hart["waitTime"], hart["receiveTime"]]))
			logging.debug("\tchecking if timestamp_to_look_for " + str(timestamp_to_look_for) + " is between " + str(pre_send_time) + " and " + str(post_send_time))
			# Return the first HAR timing that falls into our timing range
			if timestamp_to_look_for >= pre_send_time and timestamp_to_look_for <= post_send_time:
				hart["timediff"] = 0
				candidates.append(hart)
				logging.debug("\t\tYes!\n")
			else:
				hart["timediff"] = min(abs((timestamp_to_look_for - pre_send_time).total_seconds()), abs((post_send_time - timestamp_to_look_for).total_seconds()))
				candidates.append(hart)
				logging.debug("\tTimediff " + str(hart["timediff"]))

	if len(candidates) == 1:
		return candidates[0]
	elif len(candidates) > 0 and match_closest:
		mincandidate = candidates[0]
		logging.debug("candidate with " + str(mincandidate["timediff"]))
		for candidate in candidates:
			if candidate["timediff"] < mincandidate["timediff"]:
				mincandidate = candidate
				logging.debug("new min candidate with " + str(mincandidate["timediff"]))
		return mincandidate
	else:
		logging.debug("\tFound none or too many!")
		return None

def get_matching_navtiming(navtimings, page_to_look_for, timestamp_to_look_for):
	if navtimings is None:
		return None
	for navt in navtimings:
		if navt["page"] == page_to_look_for and navt["starttime"] == timestamp_to_look_for:
			return navt
	return None


# From a list of resources, give back the one expecting this tcp sequence number
def get_resource_for_packet(resourcelist, tcpseq):
	for resource in resourcelist:
		if resource["tcp.seq_to_expect"] == tcpseq:
			return resource
	return None


# From list of resource timings as read from log, get the one matching this URI and timestamp
def get_matching_restiming(restimings, uri_to_look_for, timestamp_to_look_for, page_startedDateTime, match_closest=False):
	if restimings is None:
		return None
	candidates = []
	for rest in restimings:
		res_uri = rest["name"]
		if res_uri == uri_to_look_for:
			startedDateTime = page_startedDateTime + datetime.timedelta(milliseconds = float(rest["starttime"]))
			duration = datetime.timedelta(milliseconds=float(rest["duration"]))
			endTime = startedDateTime + duration
			logging.debug("Is " + str(timestamp_to_look_for) + " between " + str(startedDateTime) + " and " + str(endTime) + "?")
			if not match_closest:
				if timestamp_to_look_for >= startedDateTime and timestamp_to_look_for <= endTime:
					return rest
			else:
				if timestamp_to_look_for >= startedDateTime and timestamp_to_look_for <= endTime:
					timediff = 0
				else:
					timediff = min(abs((timestamp_to_look_for - startedDateTime).total_seconds()), abs((endTime - timestamp_to_look_for).total_seconds()))
				rest["timediff"] = timediff
				candidates.append(rest)
	if not match_closest or len(candidates) < 1:
		return None
	else:
		mincandidate = candidates[0]
		logging.debug("candidate with " + str(mincandidate["timediff"]))
		for candidate in candidates:
			if candidate["timediff"] < mincandidate["timediff"]:
				mincandidate = candidate
				logging.debug("new min candidate with " + str(mincandidate["timediff"]))
		return mincandidate

def log_validation(run, log=True):
	HTTP_PCAP_FILE = run + "pcap/http_and_not_ssl.pcap"
	print("Logging validation object sizes for " + HTTP_PCAP_FILE)

	if not os.path.exists(HTTP_PCAP_FILE):
		print("Filtering pcap for only http traffic, this may take a while...")
		subprocess.run("tshark -r " + run + "pcap/" + CAPTURE_FILE_NAME + " -w " + HTTP_PCAP_FILE + " -Y \"(tcp.srcport == 80 or tcp.dstport == 80 and not ssl) and tcp.len > 0\"", shell=True)

	csv.register_dialect('sepbyhash', delimiter='#')

	process_headers = subprocess.run("tshark -r " + HTTP_PCAP_FILE + (" -Y" + ADDITIONAL_TSHARK_FILTER if ADDITIONAL_TSHARK_FILTER else "") + " -T fields -E separator=# -e frame.time_epoch -e tcp.stream -e tcp.srcport -e tcp.seq -e tcp.ack -e http.host -e http.request.uri -e http.response.code -e tcp.len", shell=True, stdout=subprocess.PIPE, universal_newlines=True)
	# Process trace once more to get raw TCP data - this only works if data has not been analyzed by HTTP dissector
	process_data = subprocess.run("tshark -r " + HTTP_PCAP_FILE + (" -Y" + ADDITIONAL_TSHARK_FILTER if ADDITIONAL_TSHARK_FILTER else "") + " --disable-protocol http -T fields -e data", shell=True, stdout=subprocess.PIPE, universal_newlines=True)

	headers = process_headers.stdout.splitlines()
	data = process_data.stdout.splitlines()

	reader = csv.DictReader(headers, dialect='sepbyhash', fieldnames=["timestamp", "tcp.stream", "tcp.srcport", "tcp.seq", "tcp.ack", "http.host", "http.request.uri", "http.response.code", "tcp.len"])

	packetlist = list(reader)

	tcpstreams = {}
	tcpstream_to_debug = ""

	for (index, packet) in enumerate(packetlist):

		tcpstream = packet["tcp.stream"]

		if tcpstream == tcpstream_to_debug:
			print("Packet in tcpstream_to_debug " + str(tcpstream_to_debug) + ": " + str(packet))

		# If this packet contains an HTTP request URI as parsed by tshark:
		# Create an entry for the new resource and add it to this tcpstream's dict
		if packet["http.request.uri"]:
			uri = packet["http.host"] + packet["http.request.uri"]
			newresource = { "host" : packet["http.host"], "uri" : packet["http.request.uri"], "requesttimestamp": packet["timestamp"], "response": None, "tcp.seq_to_expect": int(packet["tcp.ack"])}

			# Is there a pending HTTP transfer (that is expecting data on this tcp.seq)? Invalidate it.
			resource = None
			try:
				resource = get_resource_for_packet(tcpstreams[tcpstream], int(packet["tcp.ack"]))
			except KeyError:
				logging.debug("No resources yet -- everything is fine")
			if resource:
				logging.debug("Already expecting a non-finished resource here: " + str(resource["uri"]) + " -- invalidating")
				resource["tcp.seq_to_expect"] = -1
			try:
				tcpstreams[tcpstream].append(newresource)
			except KeyError:
				tcpstreams[tcpstream] = [newresource]

			logging.debug("\tLogged request for " + uri + " - awaiting reply at tcp.seq " + str(packet["tcp.ack"]))
			#if URI_TO_DEBUG == uri:
			#	#print("Request: " + str(packet) + " - logged: " + str(tcpstreams[tcpstream][-1]))
			#	tcpstream_to_debug = tcpstream

		else:
			# Not an HTTP request - see if we already have HTTP requests on this tcpstream
			# and if so, try to get an HTTP request expecting this packet's sequence number
			try:
				resource = get_resource_for_packet(tcpstreams[tcpstream], int(packet["tcp.seq"]))
				if not resource:
					logging.debug("Could not get resource expecting this tcp.seq " + packet["tcp.seq"] + " -- not using it")
					continue
			except KeyError as err:
				# Did not find an HTTP request logged for this tcpstream
				logging.debug("Got KeyError " + str(err) + " -- continuing")
				continue

			# We got a resource -- analyze how this packet relates to it
			resource["tcp.seq_to_expect"] += int(packet["tcp.len"])
			logging.debug("Got a resource in tcpstream " + str(tcpstream) + " at tcp.seq " + packet["tcp.seq"] + ": " + resource["host"] + resource["uri"])

			# If this packet contains an HTTP response code as parsed by tshark:
			# Look if the last entry of the resources for this tcpstream matches.
			# Matching means that the requests's tcp.ack matches this packet's tcp_seq,
			# so we can assume that this is a response to that request
			if packet["http.response.code"]:
				tcpdata = data[index]
				if len(tcpdata) / 2 != int(packet["tcp.len"]):
					# length of our tcpdata does not match tcp.len header field -- invalidating this resource
					logging.debug("Data length " + str(int(len(tcpdata) / 2)) + " does not match tcp.len " + packet["tcp.len"])
					resource["tcp.seq_to_expect"] = -1
					continue

				resource["status"] = packet["http.response.code"]

				uri = resource["host"] + resource["uri"]
				if URI_TO_DEBUG == uri:
					print("Computing stuff for " + uri + ": ")

				resource["response"] = True

				# Calculate length of header and body by splitting raw data on \r\n\r\n
				resource["tcplen"] = packet["tcp.len"]
				if "startofresponse" in resource.keys():
					tcpdata = resource["startofresponse"] + data[index]
				else:
					tcpdata = data[index]
				if "0d0a0d0a" in tcpdata:
					header, body = tcpdata.split("0d0a0d0a", 1)
					# Split raw TCP data between HTTP header and body based on "0d0a0d0a", then count bytes
					# Every byte got logged as two ascii characters - have to add 0d0a0d0a for headers again
					resource["headerlen"] = int(len(header) / 2 + 4)
					resource["bodylen"] = int(len(body) / 2)
				else:
					logging.debug("Found no 0x0d0a0d0a for " + uri + " in " + str(len(tcpdata)) + " bytes")
					if "0a0a" in tcpdata:
						logging.debug("This might be one of those rare cases with LFLF insteaf of CRLFCRLF... that is not standards compliant to HTTP/1.1. I can't take that.")
						continue
					else:
						# No delimiter - assume it's all headers
						resource["headerlen"] = int(len(tcpdata) / 2)
						resource["bodylen"] = 0
				logging.debug("\tComputed resource header length " + str(resource["headerlen"]) + " and body length " + str(resource["bodylen"]) + " for " + uri)
				# Do not expect a tcp.seq anymore
				resource["tcp.seq_to_expect"] = -1
				if uri == URI_TO_DEBUG:
					logging.debug("Added packet to end of list " + str(tcpstreams[tcpstream]))


			# This packet contains neither an http.request.uri nor an http.response.code
			# but it might be a continuation of a previous response
			# or it might actually be an HTTP response, just not decoded by tshark
			else:
				tcpdata = data[index]
				if len(tcpdata) / 2 != int(packet["tcp.len"]):
					# length of our tcpdata does not match tcp.len header field -- invalidating this resource
					logging.debug("Data length " + str(int(len(tcpdata) / 2)) + " does not match tcp.len " + packet["tcp.len"])
					resource["tcp.seq_to_expect"] = -1
					continue

				# No HTTP request and no HTTP response code but TCP stream continues
				# --> Might be HTTP continuation of a previous response
				if resource["response"]:
					resource["bodylen"] += len(tcpdata)
				else:
					# Is this actually an HTTP response, but tshark was just too stupid to dissect it?
					if tcpdata[:18] == "485454502f312e3120" or tcpdata[:18] == "485454502f312e3020":
						# Start of data says "HTTP/1.1" or 1.0 ... this is a response. Store data for later analysis
						tcpstreams[tcpstream][-1]["startofresponse"] = tcpdata
						logging.debug("This is the start of a not-yet-parsed HTTP response... storing " + str(int(len(tcpdata)/2)) + " bytes")
					elif "startofresponse" in tcpstreams[tcpstream][-1].keys():
						# We have a start of a response, but did not actually parse the complete response yet
						# -- add this to startofresponse
						tcpstreams[tcpstream][-1]["startofresponse"] += tcpdata
						logging.debug("This is the continuation of a not-yet-parsed HTTP response... storing " + str(int(len(tcpdata)/2)) + " bytes")
					else:
						# Got something, but not the start of an HTTP reply... invalidating this resource
						resource["tcp.seq_to_expect"] = -1

	logfilename = run + "object_sizes_trace.log"

	if log:
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

	starttimings = computetimings.read_starttimings(run)
	navtimings = computetimings.read_navtimings(run)
	hartimings = {}
	restimings = {}
	resources_per_page_load = {}

	max_tcpstream = max([ int(streamid) for streamid in tcpstreams.keys() ])
	logging.debug("Max tcpstream: " + str(max_tcpstream))

	# Go through TCP streams, match them to page loads (pagelabel) based on timestamps
	for i in list(range(0, max_tcpstream)):
		tcpstream = str(i)
		try:
			resources = tcpstreams[tcpstream]
		except KeyError:
			logging.debug("No resources for TCP stream " + str(tcpstream))
			continue

		# Find out which page load the first resource belongs to
		requesttimestamp = datetime.datetime.fromtimestamp(float(resources[0]["requesttimestamp"]))
		(pageurl, starttime) = computetimings.find_first_url_in_starttimings(starttimings, requesttimestamp)
		if not pageurl:
			# Did not find which page load this belongs to - cannot do anything
			continue
		else:
			logging.debug("Found page url " + pageurl)
		starttimestamp = starttime.replace(" ", "+").replace(":", "-")
		pagelabel = pageurl.replace("http://", "") + "+" + starttimestamp

		try:
			resources_per_page_load[pagelabel].extend(resources)
		except KeyError:
			resources_per_page_load[pagelabel] = resources

	for (pagelabel, resources) in resources_per_page_load.items():
		print("Page load: " + pagelabel)
		# Sort resources in this page load by requesttimestamp, then match them to HAR and resource timings
		for r in sorted(resources, key=lambda k: float(k["requesttimestamp"])):
			try:
				uri = "http://" + r["host"] + r["uri"]
				requesttimestamp = datetime.datetime.fromtimestamp(float(r["requesttimestamp"]))
				bodylen = r["bodylen"]
			except KeyError:
				logging.info("\t\t" + "no reply for " + str(r["uri"]))
				continue

			(pageurl, starttimestamp) = pagelabel.split("+", 1)
			pageurl = "http://" + pageurl
			logging.debug("URI: " + uri)
			navt = get_matching_navtiming(navtimings, pageurl, starttimestamp)
			if navt is None:
				print("Did not get navtiming for " + pageurl + "+" + str(starttimestamp))
				continue

			#print("Resource: " + str(r))
			# Get a HAR timing matching this specific resource from the HAR timings
			try:
				hart = get_matching_hartiming(hartimings[pagelabel], uri, requesttimestamp, r["status"])
			except KeyError:
				hartimings[pagelabel] = computetimings.get_hartimings(run, pagelabel, navt)
				hart = get_matching_hartiming(hartimings[pagelabel], uri, requesttimestamp, r["status"])

			if not hart:
				har_headerlen = "NA"
				har_bodylen = "NA"
				har_contentlengthheader = "NA"
				har_transfersize = "NA"
				logging.debug("No HAR timing :(")
			else:
				har_headerlen = hart["respheadersize"]
				har_bodylen = hart["respbodysize"]
				har_contentlengthheader = hart["contentlengthheader"]
				har_transfersize = hart["resptransfersize"]
				# remove the found HAR timing from the list - don't want to match it twice
				hartimings[pagelabel].remove(hart)

			if not navt:
				# No nav timing for this page -- cannot match a resource timing!
				rest = None
			else:
				# Get a resource timing matching this specific resource
				try:
					rest = get_matching_restiming(restimings[pagelabel], uri, requesttimestamp, datetime.datetime.fromtimestamp(float(navt["navigationStart"])))
				except KeyError:
					restimings[pagelabel] = computetimings.get_restimings(run, pagelabel)
					rest = get_matching_restiming(restimings[pagelabel], uri, requesttimestamp, datetime.datetime.fromtimestamp(float(navt["navigationStart"])))

			if not rest:
				res_bodylen = "NA"
			else:
				res_bodylen = rest["encodedBodySize"]
				# Remove the found resource timing from list - don't want to match it twice
				restimings[pagelabel].remove(rest)

			# For this resource, log all header and body sizes from trace, HAR, and resource timings
			if ADDITIONAL_TSHARK_FILTER:
				if r["uri"] in URI_TO_DEBUG:
					print("\t\t" + r["status"] + " " + r["host"] + r["uri"] + "\n\t\t" + str(r["headerlen"]) + " + " + str(r["bodylen"]) + " = " + str(r["tcplen"]) + " bytes (HTTP headers + body)")

			if log:
				csvwriter.writerow([pageurl, starttimestamp, r["requesttimestamp"], uri, r["status"], r["tcplen"], r["headerlen"], r["bodylen"], har_transfersize, har_headerlen, har_bodylen, har_contentlengthheader, res_bodylen])

	if log:
		csvfile.close()


def main(argv=[]):
	log = True
	if ADDITIONAL_TSHARK_FILTER:
		log = False

	runs = glob.glob(RUNDIR + "run-*")
	if (len(argv) > 1):
		runfilter = argv[1]
		runs = [ r for r in runs if runfilter in r ]

	print("Running for " + str(runs))
	for run in runs:
		if run[-1] != "/":
			run = run + "/"
		log_validation(run, log)

if __name__ == "__main__":
	main(sys.argv)
