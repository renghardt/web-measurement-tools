#!/usr/bin/env python3
import json
import sys
import datetime
import logging

logger = logging.getLogger("main")
logging.disable(logging.DEBUG) # Comment this out to enable debug logging!

def get_mahttpp(headerlist, name_to_look_for):
	mahttpplabel = get_header(headerlist, name_to_look_for)
	if mahttpplabel is None or "":
		return (None, None)
	else:
		splitlabel = mahttpplabel.split(" ")
		if len(splitlabel) == 2:
			return (splitlabel[0], splitlabel[1].replace("(", "").replace(")", ""))
		else:
			print("Could not properly split mahttpplabel " + str(mahttpplabel))
			return (None, None)

# Match HTTP header (case insensitive)
def get_header(headerlist, name_to_look_for):
	for header in headerlist:
		if header["name"].lower() == name_to_look_for.lower():
			return header["value"]
	return None


def load_harfile(harfilename):
	print("Opening HAR file " + harfilename + " to parse timings")
	try:
		harfile = open(harfilename, 'r')
		hartext = harfile.read()
		run = harfilename.split('/')[-1]
		harfile.close()
	except IOError as e:
		print("Error opening HAR file " + harfilename + ": " + str(e))
		return None
	except Exception as e:
		print("Error parsing log file " + harfilename + ": " + str(e))
		return None

	return json.loads(hartext)

def get_number_of_objects_and_sum_of_object_sizes(harfilename):

	parsedhar = load_harfile(harfilename)
	if parsedhar is None:
		return None
	entries = parsedhar["log"]["entries"]

	sum_of_body_sizes = 0

	for entry in entries:
		respbodysize = entry["response"]["bodySize"]
		sum_of_body_sizes += respbodysize

	print("This one has " + str(len(entries)) + " objects with a total size of " + str(sum_of_body_sizes) + " bytes")
	return(len(entries), sum_of_body_sizes)

# Check if value is -1, provide useful error message otherwise
def check_and_error_if_present(value, label, entry):
	# This value should be -1 if we actually got no response
	if isinstance(value, int) and value != -1 or isinstance(value, list) and len(value) > 0:
		raise ValueError(label + " got logged as " + str(value) + " for " + str(entry["request"]["url"]) + " started at " + str(entry["startedDateTime"]))

# Check if we find a header indicating HTTP/2 Server push -- HAR entries are broken in this case
def is_server_push(respheaders, entry):
    push = False
    for header in respheaders:
        if "http2-push" in header["name"]:
            logging.debug("Got header indicating HTTP/2 push: " + str(header))
            push = True
    return push

def parsehartimings(harfilename, logfilename="hartimings.log", scenario="unknown"):

	logfile = None
	if logfilename is not None:
		try:
			logfile = open(logfilename, 'a')
		except IOError as e:
			print("Error opening log file " + logfilename + ": " + str(e))
			logfile = None
	else:
		print("There is no log file.")
		logfile = None

	parsedhar = load_harfile(harfilename)
	if parsedhar is None:
		return

	entries = parsedhar["log"]["entries"]
	if parsedhar["log"]["creator"]["name"] == "WebInspector":
		startedTime = datetime.datetime.strptime(parsedhar['log']['pages'][0]['startedDateTime'][:-1], "%Y-%m-%dT%H:%M:%S.%f")
	else:
		startedTime = datetime.datetime.strptime(parsedhar['log']['pages'][0]['startedDateTime'][:-6], "%Y-%m-%dT%H:%M:%S.%f")
	logger.debug("Logging time from HAR for page " + entries[0]['request']['url'] + " started at " + startedTime.strftime("%Y-%m-%dT%H:%M:%S.%f"))

	for entry in entries:
		if parsedhar["log"]["creator"]["name"] == "WebInspector":
			startedObjectTime = datetime.datetime.strptime(entry['startedDateTime'][:-1], "%Y-%m-%dT%H:%M:%S.%f")
		else:
			startedObjectTime = datetime.datetime.strptime(entry['startedDateTime'][:-6], "%Y-%m-%dT%H:%M:%S.%f")
		startDelta = startedObjectTime - startedTime
		startDelta_milliseconds = startDelta.total_seconds() * 1000.0

		mahttpp1 = get_mahttpp(entry["response"]["headers"], "x-mahttpp-source")
		mahttpp2 = get_mahttpp(entry["response"]["headers"], "x-mahttpp-source2")

		# Look for request method, response body size, and response status -- they need to be there
		try:
			requestMethod = entry["request"]["method"]
			respbodysize = entry["response"]["bodySize"]
			status = entry["response"]["status"]
		except KeyError as err:
			print("Did not find " + str(err) + " for " + str(entry["request"]["url"]) + " -- This HAR file seems broken")
			raise(err)

		if respbodysize is None:
			# It got logged as "null" -- same as -1 (invalid)
			respbodysize = -1


		# Look for more response fields: content size (number of bytes after decompressing), header, header size
		# These are allowed to be missing, e.g., if there was no reply
		# Sometimes they are missing even though there was a reply.
		# As we ignore them in the rest of our evaluation, here we only care if they have a valid value or not.
		# If missing, they are invalid, so here we can set them to -1 or empty list safely.

		try:
			respContentSize = entry["response"]["content"]["size"]
		except KeyError as err:
			logging.info("Did not find response content size for " + str(entry["request"]["url"]) + " -- setting to -1")
			respContentSize = -1
		if respContentSize == 0:
			# It got logged as 0 - might still be no response
			respContentSize = -1


		try:
			respheaders = entry["response"]["headers"]
		except KeyError as err:
			logging.info("Did not find response headers for " + str(entry["request"]["url"]) + " -- setting to empty list")
			respheaders = []

		try:
			respheadersize = entry["response"]["headersSize"]
		except KeyError as err:
			logging.info("Did not find response headersSize for " + str(entry["request"]["url"]) + " -- setting to -1")
			respheadersize = -1

		# Log response Content-Length header
		respcontentlength = get_header(respheaders, "Content-Length")
		if not respcontentlength:
			respcontentlength = "NA"

		try:
			resptransfersize = entry["response"]["_transferSize"]
		except KeyError as err:
			logging.info("Did not find response transferSize for " + str(entry["request"]["url"]) + " -- setting to NA")
			resptransfersize = "NA"

		try:
			httpversion = entry["request"]["httpVersion"]
		except KeyError as err:
			logging.info("Did not find HTTP version for " + str(entry["request"]["url"]) + " -- setting to NA")
			httpversion = "NA"

		# Perform consistency check:
		# Status code 0 means there was no HTTP response - Was there actually no response?
		# This may be inconsistent in case of HTTP/2 server push.
		# There are also cases in which we got an actual HTTP 200 over HTTP/1.1, but still Status 0 was logged
		if status == 0:

			try:
				check_and_error_if_present(respbodysize, "Got Status Code 0, which indicates no response, but response body size", entry)
				check_and_error_if_present(respContentSize, "Got Status Code 0, which indicates no response, but response content size", entry)
				check_and_error_if_present(respcontentlength, "Got Status Code 0, which indicates no response, but response content length", entry)
				check_and_error_if_present(respheadersize, "Got Status Code 0, which indicates no response, but response header size", entry)
				check_and_error_if_present(respheaders, "Got Status Code 0, which indicates no response, but response headers", entry)
			except ValueError as err:
				print("HAR file is inconsistent: " + str(err))
				if is_server_push(respheaders, entry):
					print("This was an HTTP/2 Server Push -- logging status -2")
					status = -2
				else:
					# We probably did get a reply, but the correct status code was not logged - invalidate status
					print("Found no header indicating HTTP/2 Server Push - we cannot know the actual code, logging -1")
					status = -1


		try:
			mimetype = entry["response"]["content"]["mimeType"]
		except:
			mimetype = get_header(respheaders, "mimeType")
			if not mimetype:
				mimetype = "NA"

		try:
			sendTime = entry["timings"]["send"]
			waitTime = entry["timings"]["wait"]
			receiveTime = entry["timings"]["receive"]
		except KeyError as err:
			logging.debug("Did not find timing " + str(err) + " for " + str(entry["request"]["url"]) + " -- that's okay if there was no reply.")
			if status <= 0:
				sendTime = "NA"
				waitTime = "NA"
				receiveTime = "NA"
			else:
				print("No timings for " + str(entry["request"]["url"]) + ", but there was a reply -- something went wrong!")
				raise(err)
		try:
			blockedTime = entry["timings"]["blocked"]
			dnsTime = entry["timings"]["dns"]
			connectTime = entry["timings"]["connect"]
			sslTime = entry["timings"]["ssl"]
		except KeyError as err:
			logging.debug("Did not find timing " + str(err) + " for " + str(entry["request"]["url"]) + ", but it is optional -- setting to 0")
			blockedTime = 0
			dnsTime = 0
			connectTime = 0
			sslTime = 0
		try:
			logfile.write(entry["request"]["url"].replace(",", "") + "," + str(requestMethod) + "," + str(httpversion) + "," + str(status) + "," + str(mimetype) + "," + str(scenario) + "," + str(mahttpp1[0]) + "," + str(mahttpp1[1]) + "," + str(mahttpp2[0]) + "," + str(mahttpp2[1]) + "," + str(resptransfersize) + "," + str(respheadersize) + "," + str(respbodysize) + "," + str(respcontentlength) + "," + str(respContentSize) + "," + str(datetime.datetime.strftime(startedObjectTime, "%Y-%m-%d+%H-%M-%S.%f")) + "," + str(startDelta_milliseconds) + "," + str(blockedTime) + "," + str(dnsTime) + "," + str(connectTime) + "," + str(sslTime) + "," + str(sendTime) + "," + str(waitTime) + "," + str(receiveTime) + "\n")
		except Exception as err:
			print("Error: " + str(err))
	logfile.close()
	print("Logged to " + str(logfilename))

if __name__ == "__main__":
	try:
		HARFILE = sys.argv[1]
	except:
		print("No harfile given - cannot parse")
	
	try:
		scenario = sys.argv[2]
	except:
		scenario = "unknown"

	print("Called parsehartimings directly")
	parsehartimings(HARFILE, scenario=scenario)
