#!/usr/bin/env python3

"""
Use Chrome to load a URL and measure timings

Exports Navigation Timings and Resource Timings

"""

import PyChromeDevTools
import datetime
import time
import os
import sys
import json
import errno
import subprocess
import shutil
import signal
import pyautogui


TIMEOUT = 60

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


def logNavigationTimings(chrome, source, formattedtimestamp, timestamp, logfilename="navtimings.log", scenario="NA"):
	try:
		navigationStart = chrome.Runtime.evaluate(expression="window.performance.timing.navigationStart")["result"]["result"]["value"]
		redirectStart = getRelative(chrome.Runtime.evaluate(expression=" window.performance.timing.redirectStart")["result"]["result"]["value"], 0)
		redirectEnd = getRelative(chrome.Runtime.evaluate(expression="window.performance.timing.redirectEnd")["result"]["result"]["value"] , 0)
		fetchStart = getRelative(chrome.Runtime.evaluate(expression="window.performance.timing.fetchStart")["result"]["result"]["value"] , navigationStart)
		domainLookupStart = getRelative(chrome.Runtime.evaluate(expression="window.performance.timing.domainLookupStart")["result"]["result"]["value"] , navigationStart)
		domainLookupEnd = getRelative(chrome.Runtime.evaluate(expression="window.performance.timing.domainLookupEnd")["result"]["result"]["value"] , navigationStart)
		connectStart = getRelative(chrome.Runtime.evaluate(expression="window.performance.timing.connectStart")["result"]["result"]["value"] , navigationStart)
		secureConnectionStart = getRelative(chrome.Runtime.evaluate(expression="window.performance.timing.secureConnectionStart")["result"]["result"]["value"] , navigationStart)
		connectEnd = getRelative(chrome.Runtime.evaluate(expression="window.performance.timing.connectEnd")["result"]["result"]["value"] , navigationStart)
		requestStart = getRelative(chrome.Runtime.evaluate(expression="window.performance.timing.requestStart")["result"]["result"]["value"] , navigationStart)
		responseStart = getRelative(chrome.Runtime.evaluate(expression="window.performance.timing.responseStart")["result"]["result"]["value"] , navigationStart)
		responseEnd = getRelative(chrome.Runtime.evaluate(expression="window.performance.timing.responseEnd")["result"]["result"]["value"] , navigationStart)
		domLoading = getRelative(chrome.Runtime.evaluate(expression="window.performance.timing.domLoading")["result"]["result"]["value"] , navigationStart)
		domInteractive = getRelative(chrome.Runtime.evaluate(expression="window.performance.timing.domInteractive")["result"]["result"]["value"] , navigationStart)
		domContentLoadedEventStart = getRelative(chrome.Runtime.evaluate(expression="window.performance.timing.domContentLoadedEventStart")["result"]["result"]["value"] , navigationStart)
		domContentLoadedEventEnd = getRelative(chrome.Runtime.evaluate(expression="window.performance.timing.domContentLoadedEventEnd")["result"]["result"]["value"] , navigationStart)
		domComplete = getRelative(chrome.Runtime.evaluate(expression="window.performance.timing.domComplete")["result"]["result"]["value"] , navigationStart)
		loadEventStart = getRelative(chrome.Runtime.evaluate(expression="window.performance.timing.loadEventStart")["result"]["result"]["value"] , navigationStart)
		loadEventEnd  = getRelative(chrome.Runtime.evaluate(expression="window.performance.timing.loadEventEnd")["result"]["result"]["value"] , navigationStart)

		firstPaint  = chrome.Runtime.evaluate(expression="performance.getEntriesByName('first-paint')[0]['startTime']")["result"]["result"]["value"]
		firstContentfulPaint  = chrome.Runtime.evaluate(expression="performance.getEntriesByName('first-contentful-paint')[0]['startTime']")["result"]["result"]["value"]
	except Exception as err:
		print("Could not execute script on page, got Error " + str(err))
		return

	print("Navigation timings for page " + source + ":\n\t\tredirectStart:\t\t" + str(redirectStart) + " ms\n\t\tredirectEnd:\t\t" + str(redirectEnd) + " ms\n\t\tfetchStart:\t\t" + str(fetchStart) + " ms\n\t\tdomainLookupStart:\t" + str(domainLookupStart) + " ms\n\t\tdomainLookupEnd:\t" + str(domainLookupEnd) + " ms\n\t\tconnectStart:\t\t" + str(connectStart) + " ms\n\t\tsecureConnectionStart:\t" + str(secureConnectionStart) + " ms\n\t\tconnectEnd:\t\t" + str(connectEnd) + " ms\n\t\trequestStart:\t\t" + str(requestStart) + " ms\n\t\tresponseStart:\t\t" + str(responseStart) + " ms\n\t\tresponseEnd:\t\t" + str(responseEnd) + " ms\n\t\tdomLoading:\t\t" + str(domLoading) + " ms\n\t\tdomInteractive:\t\t" + str(domInteractive) + " ms\n\t\tdomContentLoadedEventStart:\t" + str(domContentLoadedEventStart) + " ms\n\t\tdomContentLoadedEventEnd:\t" + str(domContentLoadedEventEnd) + " ms\n\t\tdomComplete:\t\t" + str(domComplete) + " ms\n\t\tloadEventStart:\t\t" + str(loadEventStart) + " ms\n\t\tloadEventEnd:\t\t" + str(loadEventEnd) + " ms\n\n\t\tfirstPaint:\t\t" + str(round(firstPaint, 3)) + " ms\n\t\tfirstContentfulPaint:\t" + str(round(firstContentfulPaint, 3)) + "\n")

	try:
		logfile = open(logfilename, 'a', 1)

		logfile.write (str(source) + "," + str(scenario) + "," + str(formattedtimestamp) + "," + str(timestamp) + "," + str(navigationStart/1000) + "," + str(redirectStart) + "," + str(redirectEnd) + "," + str(fetchStart) + "," + str(domainLookupStart) + "," + str(domainLookupEnd) + "," + str(connectStart) + "," + str(secureConnectionStart) + "," + str(connectEnd) + "," + str(requestStart) + "," + str(responseStart) + "," + str(responseEnd) + "," + str(domLoading) + "," + str(domInteractive) + "," + str(domContentLoadedEventStart) + "," + str(domContentLoadedEventEnd) + "," + str(domComplete) + "," + str(loadEventStart) + "," + str(loadEventEnd) + "," + str(firstPaint) + ",NA," + str(firstContentfulPaint) + "\n")

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
		numberofresources = chrome.Runtime.evaluate(expression="window.performance.getEntriesByType(\"resource\").length")["result"]["result"]["value"]
	except Exception as err:
		print("Could not get number of resources, got Error " + str(err))
		return

	for r in range(0, numberofresources):
		try:
			resource = json.loads(chrome.Runtime.evaluate(expression="JSON.stringify(window.performance.getEntriesByType(\"resource\")[" + str(r) + "].toJSON())")["result"]["result"]["value"])
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

def showMessages(messages):
	for m in messages:
		if "method" in m and m["method"] == "Network.responseReceived":
			try:
				url=m["params"]["response"]["url"]
				print (url + " - " + str(m["params"]["response"]["status"]) + " - " + str(m["params"]["response"]["timing"]))
			except:
				pass

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
		driver.Runtime.evaluate(expression = "HAR.triggerExport().then(harLog => { foo = harLog; }); ", contextId=1)
		print("executed1")
		time.sleep(1)
		HARtext = json.loads(driver.Runtime.evaluate(expression = "JSON.stringify(foo); ;", contextId=1)["result"]["result"]["value"])
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

	# Create a new profile directory and try to suppress "Welcome" messages and other nonsense
	timestamp = datetime.datetime.now().strftime("%Y-%m-%d+%H-%M-%S.%f")
	createDirectory("/tmp/foo" + str(timestamp))
	createDirectory("/tmp/foo" + str(timestamp) + "/Default")
	open("/tmp/foo" + str(timestamp) + "/First Run", 'a').close()
	shutil.copy("chrome_prefs.json", "/tmp/foo" + str(timestamp) + "/Default/Preferences")

    # Open Chrome, try to be as quiet as possible
    # see also https://stackoverflow.com/questions/5814334/how-to-disable-google-chromes-unrequested-connections
	p = subprocess.Popen(["google-chrome --user-data-dir=/tmp/foo" + str(timestamp) + " --remote-debugging-port=9222 --disable-background-networking --disable-component-extensions-with-background-pages --dns-prefetch-disable"], shell=True, preexec_fn=os.setsid)

    # We have to kill the new Chrome once and open it again
    # otherwise it does not display the page load on screen (???)
	print("Opened chrome! " + str(p.pid))
	time.sleep(2)
	os.killpg(os.getpgid(p.pid), signal.SIGTERM)
	print("Killed chrome! " + str(p.pid))

	p = subprocess.Popen(["google-chrome --user-data-dir=/tmp/foo" + str(timestamp) + " --remote-debugging-port=9222 --disable-background-networking --disable-component-extensions-with-background-pages --dns-prefetch-disable"], shell=True, preexec_fn=os.setsid)
	print("Opened new chrome! " + str(p.pid))

	time.sleep(1)

	chrome = PyChromeDevTools.ChromeInterface()

	chrome.Network.enable()


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
			# Press F12 to open DevTools console - otherwise we cannot export HAR
			pyautogui.press('f12')

			time.sleep(1)

			chrome.Page.navigate(url=URL_TO_FETCH)
			event,messages=chrome.wait_event("Page.loadEventFired", timeout=TIMEOUT)
			time.sleep(1)

		except Exception as e:
			print("Error fetching page " + URL_TO_FETCH + ": " + str(e) + "\n")
			try:
				logNavigationTimings(chrome, URL_TO_FETCH, timestamp, unixtimestamp, LOGDIR + "failed_navtimings.log", scenario = SCENARIO)
			except Exception as e:
				print("Could not even log Nav timings for failed page " + str(URL_TO_FETCH) + ": " + str(e))
			sys.exit(-1)
		createDirectory(LOGDIR + "res")

		try:
			logNavigationTimings(chrome, URL_TO_FETCH, timestamp, unixtimestamp, LOGDIR + "navtimings.log", scenario = SCENARIO)

		except Exception as e:
			print("Error logging Navigation timings: " + str(sys.exc_info()[0]) + ", " + str(e))
		try:
			logResourceTimings(chrome, URL_TO_FETCH, timestamp, printout=False, scenario = SCENARIO)
		except Exception as e:
			print("Error logging Resource timings: " + str(sys.exc_info()[0]) + ", " + str(e))
		try:
			logHAR(chrome, URL_TO_FETCH, timestamp)
		except Exception as e:
			print("Error logging HAR: " + str(sys.exc_info()[0]) + ", " + str(e))


	os.killpg(os.getpgid(p.pid), signal.SIGTERM)
