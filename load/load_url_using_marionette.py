#!/usr/bin/env python2

"""
Use Firefox with Marionette to load a URL and measure timings
using a freshly initialized Firefox profile, see firefox_prefs.js in this directory.

Exports Navigation Timings and Resource Timings

Arguments:
[1] URL to fetch
[2] Scenario (for logging)
[3] How many times to fetch the URL
[4] Log directory for Navigation Timings, Resource Timings, and HAR files

Dependencies:
    Firefox                   (tested with version 61.0.2 and 62.0.2)
    har-export-trigger-0.61.1 (.xpi needs to be in the same directory as this script)

"""

from marionette_driver.marionette import Marionette
from marionette_driver.addons import Addons
import datetime
import time
import os
import shutil
import signal
import sys
import json
import errno
import subprocess


TIMEOUT = 60

FIREFOX_PATH = "/opt/firefox/firefox"

def createDirectory(path):
	try:
		os.makedirs(path)
	except OSError as exception:
		if exception.errno != errno.EEXIST:
			raise


def getRelative(value, ref):
	try:
		result = value - ref
	except:
		result = value
	return result


def logNavigationTimings(client, source, formattedtimestamp, timestamp, logfilename="navtimings.log", scenario="NA"):
	try:
		navigationStart = client.execute_script("return window.performance.timing.navigationStart")
		redirectStart = getRelative(client.execute_script(" return window.performance.timing.redirectStart"), 0)
		redirectEnd = getRelative(client.execute_script("return window.performance.timing.redirectEnd") , 0)
		fetchStart = getRelative(client.execute_script("return window.performance.timing.fetchStart") , navigationStart)
		domainLookupStart = getRelative(client.execute_script("return window.performance.timing.domainLookupStart") , navigationStart)
		domainLookupEnd = getRelative(client.execute_script("return window.performance.timing.domainLookupEnd") , navigationStart)
		connectStart = getRelative(client.execute_script("return window.performance.timing.connectStart") , navigationStart)
		secureConnectionStart = getRelative(client.execute_script("return window.performance.timing.secureConnectionStart") , navigationStart)
		connectEnd = getRelative(client.execute_script("return window.performance.timing.connectEnd") , navigationStart)
		requestStart = getRelative(client.execute_script("return window.performance.timing.requestStart") , navigationStart)
		responseStart = getRelative(client.execute_script("return window.performance.timing.responseStart") , navigationStart)
		responseEnd = getRelative(client.execute_script("return window.performance.timing.responseEnd") , navigationStart)
		domLoading = getRelative(client.execute_script("return window.performance.timing.domLoading") , navigationStart)
		domInteractive = getRelative(client.execute_script("return window.performance.timing.domInteractive") , navigationStart)
		domContentLoadedEventStart = getRelative(client.execute_script("return window.performance.timing.domContentLoadedEventStart") , navigationStart)
		domContentLoadedEventEnd = getRelative(client.execute_script("return window.performance.timing.domContentLoadedEventEnd") , navigationStart)
		domComplete = getRelative(client.execute_script("return window.performance.timing.domComplete") , navigationStart)
		loadEventStart = getRelative(client.execute_script("return window.performance.timing.loadEventStart") , navigationStart)
		loadEventEnd  = getRelative(client.execute_script("return window.performance.timing.loadEventEnd") , navigationStart)

		firstPaint  = getRelative(client.execute_script("return window.performance.timing.timeToNonBlankPaint") , navigationStart)
		domContentFlushed  = getRelative(client.execute_script("return window.performance.timing.timeToDOMContentFlushed") , navigationStart)

	except Exception as err:
		print("Could not execute script on page, got Error " + str(err))
		return

	print("Navigation timings for page " + source + ":\n\t\tredirectStart:\t\t" + str(redirectStart) + " ms\n\t\tredirectEnd:\t\t" + str(redirectEnd) + " ms\n\t\tfetchStart:\t\t" + str(fetchStart) + " ms\n\t\tdomainLookupStart:\t" + str(domainLookupStart) + " ms\n\t\tdomainLookupEnd:\t" + str(domainLookupEnd) + " ms\n\t\tconnectStart:\t\t" + str(connectStart) + " ms\n\t\tsecureConnectionStart:\t" + str(secureConnectionStart) + " ms\n\t\tconnectEnd:\t\t" + str(connectEnd) + " ms\n\t\trequestStart:\t\t" + str(requestStart) + " ms\n\t\tresponseStart:\t\t" + str(responseStart) + " ms\n\t\tresponseEnd:\t\t" + str(responseEnd) + " ms\n\t\tdomLoading:\t\t" + str(domLoading) + " ms\n\t\tdomInteractive:\t\t" + str(domInteractive) + " ms\n\t\tdomContentLoadedEventStart:\t" + str(domContentLoadedEventStart) + " ms\n\t\tdomContentLoadedEventEnd:\t" + str(domContentLoadedEventEnd) + " ms\n\t\tdomComplete:\t\t" + str(domComplete) + " ms\n\t\tloadEventStart:\t\t" + str(loadEventStart) + " ms\n\t\tloadEventEnd:\t\t" + str(loadEventEnd) + " ms\n\n\t\tfirstPaint:\t\t" + str(firstPaint) + " ms\n\t\tdomContentFlushed:\t" + str(domContentFlushed) + " ms\n")

	try:
		logfile = open(logfilename, 'a', 1)

		logfile.write (str(source) + "," + str(scenario) + "," + str(formattedtimestamp) + "," + str(timestamp) + "," + str(round(navigationStart/1000, 3)) + "," + str(redirectStart) + "," + str(redirectEnd) + "," + str(fetchStart) + "," + str(domainLookupStart) + "," + str(domainLookupEnd) + "," + str(connectStart) + "," + str(secureConnectionStart) + "," + str(connectEnd) + "," + str(requestStart) + "," + str(responseStart) + "," + str(responseEnd) + "," + str(domLoading) + "," + str(domInteractive) + "," + str(domContentLoadedEventStart) + "," + str(domContentLoadedEventEnd) + "," + str(domComplete) + "," + str(loadEventStart) + "," + str(loadEventEnd) + "," + str(firstPaint) + "," + str(domContentFlushed) + "\n")

		logfile.close()
		print("Logged Navigation Timings and firstPaint to " + logfilename)
	except Exception as err:
		print("Error logging Navigation Timings: " + str(err))

def logResourceTimings(chrome, source, timestamp, printout=False, scenario = "NA"):

	resourcelogfile = None
	resourcelogfilename = LOGDIR + "res/" + source.split('/')[2] + "+" + timestamp + ".res.log"
	try:
		resourcelogfile = open(resourcelogfilename, 'a+')
	except IOError as e:
		print("Error opening logfile " + str(resourcelogfilename) + ": " + str(e))
		return
	except:
		resourcelogfile.close()
		print("Another error occured with " + str(resourcelogfilename))
		return

	try:
		numberofresources = client.execute_script("return window.performance.getEntriesByType(\"resource\").length", new_sandbox=False)
	except Exception as err:
		print("Could not get number of resources, got Error " + str(err))
		return

	for r in range(0, numberofresources):
		try:
			resource = client.execute_script("return window.performance.getEntriesByType(\"resource\")[" + str(r) + "]", new_sandbox=False)
		except Exception as err:
			print("Could not get resource timings for resource " + str(r) + "/" + str(numberofresources) + ", got Error " + str(err))
			resourcelogfile.close()
			os.remove(resourcelogfilename)
			return
		starttime = resource['startTime']
		if resource['redirectStart'] > 0:
			redirectStart = resource['redirectStart']
			redirectStart = resource['redirectEnd']
		else:
			redirectStart = "NA"
			redirectEnd = "NA"
		fetchStart = resource['fetchStart']
		domainLookupStart = resource['domainLookupStart']
		domainLookupEnd = resource['domainLookupEnd']
		connectStart = resource['connectStart']
		if resource['secureConnectionStart'] > 0:
			secureConnectionStart = resource['secureConnectionStart']
		else:
			secureConnectionStart = "NA"
		connectEnd = resource['connectEnd']
		requestStart = resource['requestStart']
		responseStart = resource['responseStart']
		responseEnd = resource['responseEnd']
		duration = resource['duration']
		initiatorType = resource['initiatorType']
		nextHopProtocol = resource['nextHopProtocol']
		encodedBodySize = resource['encodedBodySize']
		decodedBodySize = resource['decodedBodySize']

		if printout:
			print("Resource timings for " + resource['name'] + ":")
			print("(initiated by " + str(initiatorType) + ", fetched via " + str(nextHopProtocol) + ")")
			print("\t\tstartTime \t\t" + str(starttime))
			if redirectStart != "NA":
				print("\t\tredirectStart \t\t" + str(redirectStart - starttime))
				print("\t\tredirectEnd \t\t" + str(redirectEnd - starttime))
			print("\t\tfetchStart \t\t" + str(fetchStart - starttime))
			print("\t\tdomainLookupStart \t" + str(domainLookupStart - starttime))
			print("\t\tdomainLookupEnd \t" + str(domainLookupEnd - starttime))
			print("\t\tconnectStart \t\t" + str(connectStart - starttime))
			if secureConnectionStart != "NA":
				print("\t\tsecureConnectionStart \t" + str(secureConnectionStart - starttime))
			print("\t\tconnectEnd \t\t" + str(connectEnd - starttime))
			print("\t\trequestStart: \t\t" + str(requestStart - starttime))
			print("\t\tresponseStart: \t\t" + str(responseStart - starttime))
			print("\t\tresponseEnd: \t\t" + str(responseEnd - starttime))
			print("\t\tduration: \t\t" + str(duration) + "\n")
			print("\t\tencodedBodySize: \t\t" + str(encodedBodySize) + "\n")
			print("\t\tdecodedBodySize: \t\t" + str(decodedBodySize) + "\n")

		if resourcelogfile is not None:
			try:
				resourcelogfile.write(resource['name'].replace(",", "") + "," + str(scenario) + "," + str(initiatorType) + "," + str(nextHopProtocol) + "," + str(encodedBodySize) + "," + str(decodedBodySize) + "," + str(starttime) + "," + str(redirectStart) + "," + str(redirectEnd) + "," + str(fetchStart) + "," + str(domainLookupStart) + "," + str(domainLookupEnd) + "," + str(connectStart) + "," + str(secureConnectionStart) + "," + str(connectEnd) + "," + str(requestStart) + "," + str(responseStart) + "," + str(responseEnd) + "," + str(duration) + "\n")
			except Exception as err:
				print("Error: " + str(err))
	try:
		print("Logged all " + str(numberofresources) + " resource timings to " + str(resourcelogfilename))
		resourcelogfile.close()
	except Exception as err:
		print("Error: " + str(err))

def logHAR(driver, source, timestamp):
	HARfile = None
	createDirectory(LOGDIR + "har/")
	HARfilename = LOGDIR + "har/" + source.split('/')[2] + "+" + timestamp + ".har"
	try:
		HARfile = open(HARfilename, 'w')
	except IOError as e:
		print("Error opening logfile " + str(HARfile) + ": " + str(e))
		return None
	except:
		HARfile.close()
		print("Another error occured with " + str(HARfilename))
		return None

	try:
        # No idea why, but the devtools have to be open for this to work.
        # Otherwise, the Promise returned in window.foo never resolves.
        # Also, this probably should be an async script.
		HARtext = driver.execute_script("window.foo = HAR.triggerExport().then(harLog => { return(harLog); }); return window.foo;", sandbox=None, new_sandbox=False)
	except Exception as err:
		print("Could not get HAR, got Error " + str(err))
		return None

	try:
		HARfile.write(json.dumps({"log": HARtext}, indent=4, sort_keys=True))
		print("Logged HAR to " + str(HARfilename))
		HARfile.close()
		return HARfilename

	except Exception as err:
		print("Could not log HAR to " + str(HARfilename) + ", got Error " + str(err))
		return None


try:
	if (sys.argv[1] == "--help"):
		print("Usage:\n\t\twebtimings.py <URL_TO_FETCH> <HOW_MANY_TIMES> <TIMINGS_LOG_DIRECTORY>")
		sys.exit(0)
	else:
		URL_TO_FETCH = str(sys.argv[1])
except Exception as e:
	URL_TO_FETCH = "http://www.debian.org"

try:
	SCENARIO = str(sys.argv[2])
except Exception as e:
	SCENARIO = "unknown"

try:
	TIMES = int(sys.argv[3])
except:
	TIMES = 1

try:
	LOGDIR = str(sys.argv[4])
except:
	LOGDIR = "./log/"


createDirectory(LOGDIR)

if __name__ == "__main__":

	# Create new Firefox profile, copy preferences there
	timestamp = datetime.datetime.now().strftime("%Y-%m-%d+%H-%M-%S.%f")
	subprocess.call(FIREFOX_PATH + " -CreateProfile \"foo" + str(timestamp) + " /tmp/foo" + str(timestamp) + "\"", shell=True)
	shutil.copy("firefox_prefs.js", "/tmp/foo" + str(timestamp) + "/prefs.js")

	time.sleep(1)

	# Launch Firefox with the new profile
	p = subprocess.Popen([FIREFOX_PATH + " -profile /tmp/foo" + str(timestamp) + " -marionette -devtools"], shell=True, preexec_fn=os.setsid)

	client = Marionette('localhost', port=2828)
	client.start_session()

	addons = Addons(client)
	addons.install(os.getcwd() + "/har-export-trigger-0.6.1.xpi", temp=True)

	for run in range(1, TIMES+1):
		timestamp = datetime.datetime.now().strftime("%Y-%m-%d+%H-%M-%S.%f")
		unixtimestamp = int(time.time())
		try:
			hostname = URL_TO_FETCH.split('/')[2]
		except IndexError:
			hostname = URL_TO_FETCH
			URL_TO_FETCH = "http://" + hostname

		print("Run " +  str(run) + "/" + str(TIMES) + " - Fetching " + URL_TO_FETCH + " at " + timestamp)
		time.sleep(1)
		event = None
		messages = None

		try:
			time.sleep(1)

			client.navigate(URL_TO_FETCH)

		except Exception as e:
			print("Error fetching page " + URL_TO_FETCH + ": " + str(e) + "\n")
			try:
				logNavigationTimings(client, URL_TO_FETCH, timestamp, unixtimestamp, LOGDIR + "failed_navtimings.log", scenario = SCENARIO)
			except Exception as e:
				print("Could not even log Nav timings for failed page " + str(URL_TO_FETCH) + ": " + str(e))
			sys.exit(-1)
		createDirectory(LOGDIR + "res")

		try:
			logNavigationTimings(client, URL_TO_FETCH, timestamp, unixtimestamp, LOGDIR + "navtimings.log", scenario = SCENARIO)
		except Exception as e:
			print("Error logging Navigation timings: " + str(sys.exc_info()[0]) + ", " + str(e))
		try:
			logResourceTimings(client, URL_TO_FETCH, timestamp, printout=False, scenario = SCENARIO)
		except Exception as e:
			print("Error logging Resource timings: " + str(sys.exc_info()[0]) + ", " + str(e))
		try:
			logHAR(client, URL_TO_FETCH, timestamp)
		except Exception as e:
			print("Error logging HAR: " + str(sys.exc_info()[0]) + ", " + str(e))

	client.close()
	time.sleep(1)
	os.killpg(os.getpgid(p.pid), signal.SIGTERM)
