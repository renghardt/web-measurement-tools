#!/usr/bin/env python3

"""
Use Selenium to Measure Web Timing: 
- given a URL:
--- fetches the URL using a new browser instance
--- log Navigation Timings
--- log Resource Timings
--- export a HAR file

Arguments:
[1] URL to fetch
[2] Scenario (for logging)
[3] How many times to fetch the URL
[4] Log directory for resource timings


Navigation Timing Events

navigationStart -> redirectStart -> redirectEnd -> fetchStart -> domainLookupStart -> domainLookupEnd
-> connectStart -> connectEnd -> requestStart -> responseStart -> responseEnd
-> domLoading -> domInteractive -> domContentLoadedEventStart -> domContentLoadedEventEnd -> domComplete -> loadEventStart -> loadEventEnd

Dependencies: 
                Firefox     (tested with version 61.0.2, set FIREFOX_PATH accordingly below)
                selenium    (tested with version 3.14.0)
                geckodriver (tested with version 0.21.0)
                har-export-trigger-0.61.1 (.xpi needs to be in the same directory as this script)

"""

from selenium import webdriver
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary
from selenium.webdriver.firefox.firefox_profile import AddonFormatError
import socket
import os
import errno
import datetime
import time
import sys 
import re
import json

FIREFOX_PATH = "/opt/firefox-61.0.2/firefox"

SOCKETTIMEOUT = 30

def createDirectory(path):
	try:
		os.makedirs(path)
	except OSError as exception:
		if exception.errno != errno.EEXIST:
			raise

class FirefoxProfileWithWebExtensionSupport(webdriver.FirefoxProfile):
    def _addon_details(self, addon_path):
        try:
            return super()._addon_details(addon_path)
        except AddonFormatError:
            try:
                with open(os.path.join(addon_path, 'manifest.json'), 'r') as f:
                    manifest = json.load(f)
                    return {
                        'id': manifest['applications']['gecko']['id'],
                        'version': manifest['version'],
                        'name': manifest['name'],
                        'unpack': False,
                    }
            except (IOError, KeyError) as e:
                raise AddonFormatError(str(e), sys.exc_info()[2])


def getRelative(value, ref):
	try:
		result = value - ref
	except:
		result = value
	return result

def logNavigationTimings(driver, source, formattedtimestamp, timestamp, logfilename="navtimings.log", scenario="NA"):
	try:
		navigationStart = driver.execute_script("return window.performance.timing.navigationStart")
		redirectStart = getRelative(driver.execute_script("return window.performance.timing.redirectStart") , 0)
		redirectEnd = getRelative(driver.execute_script("return window.performance.timing.redirectEnd") , 0)
		fetchStart = getRelative(driver.execute_script("return window.performance.timing.fetchStart") , navigationStart)
		domainLookupStart = getRelative(driver.execute_script("return window.performance.timing.domainLookupStart") , navigationStart)
		domainLookupEnd = getRelative(driver.execute_script("return window.performance.timing.domainLookupEnd") , navigationStart)
		connectStart = getRelative(driver.execute_script("return window.performance.timing.connectStart") , navigationStart)
		secureConnectionStart = getRelative(driver.execute_script("return window.performance.timing.secureConnectionStart") , navigationStart)
		connectEnd = getRelative(driver.execute_script("return window.performance.timing.connectEnd") , navigationStart)
		requestStart = getRelative(driver.execute_script("return window.performance.timing.requestStart") , navigationStart)
		responseStart = getRelative(driver.execute_script("return window.performance.timing.responseStart") , navigationStart)
		responseEnd = getRelative(driver.execute_script("return window.performance.timing.responseEnd") , navigationStart)
		domLoading = getRelative(driver.execute_script("return window.performance.timing.domLoading") , navigationStart)
		domInteractive = getRelative(driver.execute_script("return window.performance.timing.domInteractive") , navigationStart)
		domContentLoadedEventStart = getRelative(driver.execute_script("return window.performance.timing.domContentLoadedEventStart") , navigationStart)
		domContentLoadedEventEnd = getRelative(driver.execute_script("return window.performance.timing.domContentLoadedEventEnd") , navigationStart)
		domComplete = getRelative(driver.execute_script("return window.performance.timing.domComplete") , navigationStart)
		loadEventStart = getRelative(driver.execute_script("return window.performance.timing.loadEventStart") , navigationStart)
		loadEventEnd  = getRelative(driver.execute_script("return window.performance.timing.loadEventEnd") , navigationStart)
		firstPaint  = getRelative(driver.execute_script("return window.performance.timing.timeToNonBlankPaint") , navigationStart)
	except Exception as err:
		print("Could not execute script on page, got Error " + str(err))
		return
	
	print("Navigation timings for page " + source + ":\n\t\tredirectStart:\t\t" + str(redirectStart) + " ms\n\t\tredirectEnd:\t\t" + str(redirectEnd) + " ms\n\t\tfetchStart:\t\t" + str(fetchStart) + " ms\n\t\tdomainLookupStart:\t" + str(domainLookupStart) + " ms\n\t\tdomainLookupEnd:\t" + str(domainLookupEnd) + " ms\n\t\tconnectStart:\t\t" + str(connectStart) + " ms\n\t\tsecureConnectionStart:\t" + str(secureConnectionStart) + " ms\n\t\tconnectEnd:\t\t" + str(connectEnd) + " ms\n\t\trequestStart:\t\t" + str(requestStart) + " ms\n\t\tresponseStart:\t\t" + str(responseStart) + " ms\n\t\tresponseEnd:\t\t" + str(responseEnd) + " ms\n\t\tdomLoading:\t\t" + str(domLoading) + " ms\n\t\tdomInteractive:\t\t" + str(domInteractive) + " ms\n\t\tdomContentLoadedEventStart:\t" + str(domContentLoadedEventStart) + " ms\n\t\tdomContentLoadedEventEnd:\t" + str(domContentLoadedEventEnd) + " ms\n\t\tdomComplete:\t\t" + str(domComplete) + " ms\n\t\tloadEventStart:\t\t" + str(loadEventStart) + " ms\n\t\tloadEventEnd:\t\t" + str(loadEventEnd) + " ms\n\n\t\tfirstPaint:\t\t" + str(firstPaint) + " ms\n")
	
	try:
		logfile = open(logfilename, 'a', 1)

		logfile.write (str(source) + "," + str(scenario) + "," + str(formattedtimestamp) + "," + str(timestamp) + "," + str(round(navigationStart/1000, 3)) + "," + str(redirectStart) + "," + str(redirectEnd) + "," + str(fetchStart) + "," + str(domainLookupStart) + "," + str(domainLookupEnd) + "," + str(connectStart) + "," + str(secureConnectionStart) + "," + str(connectEnd) + "," + str(requestStart) + "," + str(responseStart) + "," + str(responseEnd) + "," + str(domLoading) + "," + str(domInteractive) + "," + str(domContentLoadedEventStart) + "," + str(domContentLoadedEventEnd) + "," + str(domComplete) + "," + str(loadEventStart) + "," + str(loadEventEnd) + "," + str(firstPaint) + "\n")

		logfile.close()
		print("Logged Navigation Timings and firstPaint to " + logfilename)
	except Exception as err:
		print("Error logging Navigation Timings: " + str(err))

def logResourceTimings(driver, source, timestamp, printout=False, scenario = "NA"):

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
		numberofresources = driver.execute_script("return window.performance.getEntriesByType(\"resource\").length")
	except Exception as err:
		print("Could not get number of resources, got Error " + str(err))
		return

	for r in range(0, numberofresources):
		try:
			resource = driver.execute_script("return window.performance.getEntriesByType(\"resource\")["+str(r)+"]")
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

		if resourcelogfile is not None:
			try:
				resourcelogfile.write(resource['name'].replace(",", "") + "," + str(scenario) + "," + str(initiatorType) + "," + str(nextHopProtocol) + "," + str(starttime) + "," + str(redirectStart) + "," + str(redirectEnd) + "," + str(fetchStart) + "," + str(domainLookupStart) + "," + str(domainLookupEnd) + "," + str(connectStart) + "," + str(secureConnectionStart) + "," + str(connectEnd) + "," + str(requestStart) + "," + str(responseStart) + "," + str(responseEnd) + "," + str(duration) + "\n")
			except Exception as err:
				print("Error: " + str(err))
	try:
		print("Logged all resource timings to " + str(resourcelogfilename))
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
		HARtext = driver.execute_script("foo = HAR.triggerExport().then( result => { return result;}); return foo;")
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

"""
Main code starts here!
"""

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
	if re.search('mobile', SCENARIO):
		USERAGENT = "Mozilla/5.0 (Linux; Android 4.2.2; SOL22 Build/10.3.1.D.0.220) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/38.0.2125.102 Mobile Safari/537.36"
		print("Setting user agent to mobile.")
	else:
		USERAGENT = ""
except:
	USERAGENT = ""


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
	profile = FirefoxProfileWithWebExtensionSupport()
	profile.set_preference("app.update.enabled", "false")

	# disable caching
	profile.set_preference("browser.cache.disk.enable", False)
	profile.set_preference("browser.cache.memory.enable", False)
	profile.set_preference("browser.cache.offline.enable", False)
	profile.set_preference("network.http.use-cache", False)

    # try to disable ocsp stuff
	profile.set_preference("security.ssl.enable_ocsp_stapling", False)
	profile.set_preference("security.OCSP.enabled", 0)
	profile.set_preference("security.OCSP.require", False)
	profile.set_preference("security.ssl.enable_ocsp_must_staple", False)
	profile.set_preference("security.ssl.enable_ocsp_stapling", False)
	profile.set_preference("services.sync.prefs.sync.security.OCSP.enabled", False)
	profile.set_preference("services.sync.prefs.sync.security.OCSP.require", False)

	# disable some Firefox features that make it generate additional traffic
	profile.set_preference("browser.newtabpage.directory.source", "")
	profile.set_preference("browser.newtabpage.directory.ping", "")
	profile.set_preference("browser.newtabpage.enabled", False)
	profile.set_preference("browser.newtabpage.enhanced", False)
	profile.set_preference("browser.newtabpage.introShown", False)
	profile.set_preference("browser.newtab.preload", False)
	profile.set_preference("browser.aboutHomeSnippets.updateUrl", "")
	profile.set_preference("browser.send_pings", False)
	profile.set_preference("geo.enabled", False)
	profile.set_preference("browser.search.geoip.url", "")
	profile.set_preference("extensions.getAddons.cache.enabled", False)
	profile.set_preference("social.remote-install.enabled", False)
	profile.set_preference("social.toast-notifications.enabled", False)
	profile.set_preference("media.gmp-manager.certs.1.commonName", "")
	profile.set_preference("media.gmp-manager.certs.2.commonName", "")
	profile.set_preference("media.gmp-manager.url", "")
	profile.set_preference("media.peerconnection.enabled", "")
    # props to https://www.wilderssecurity.com/threads/firefox-quiet.375074/
	profile.set_preference("network.captive-portal-service.enabled", False)
    # Disable tracking protection
	profile.set_preference("privacy.trackingprotection.annotate_channels", False)
	profile.set_preference("privacy.trackingprotection.enabled", False)
	profile.set_preference("privacy.trackingprotection.pbmode.enabled", False)
	profile.set_preference("plugins.flashBlock.enabled", False)
	profile.set_preference("plugins.safebrowsing.blockedURIs.enabled", False)
	profile.set_preference("plugins.safebrowsing.downloads.remote.enabled", False)
    # Disable telemetry
	profile.set_preference("datareporting.policy.dataSubmissionEnabled", False)
	profile.set_preference("datareporting.healthreport.service.enabled", False)
	profile.set_preference("datareporting.healthreport.uploadEnabled", False)
	profile.set_preference("toolkit.telemetry.archive.enabled", False)
	profile.set_preference("toolkit.telemetry.enabled", False)
	profile.set_preference("toolkit.telemetry.rejected", True)
	profile.set_preference("toolkit.telemetry.server", "")
	profile.set_preference("toolkit.telemetry.unified", False)
	profile.set_preference("toolkit.telemetry.unifiedIsOptIn", False)
	profile.set_preference("toolkit.telemetry.prompted", 2)
	profile.set_preference("toolkit.telemetry.rejected", True)

	profile.set_preference("browser.chrome.favicon", False)
	profile.set_preference("browser.chrome.site_icons", False)
    # disable favicons, hopefully now the won't get fetched
	profile.set_preference("media.gmp-provider.enabled", False)
	profile.set_preference("media.gmp-gmpopenh264.enabled", False)

	profile.set_preference("dom.performance.time_to_non_blank_paint.enabled", True)
	# enable firstPaint timing

	profile.set_preference("dom.enable_resource_timing", True)

	try:
		for f in os.listdir("./"):
			if re.match('har-export-trigger-0.6.1.xpi', f) is not None:
				print("Adding extension " + str(f))
				profile.add_extension(f)

		if (USERAGENT != ""):
			profile.set_preference("general.useragent.override", USERAGENT)
		profile.set_preference("devtools.netmonitor.enabled", True)
		profile.set_preference("devtools.netmonitor.har.includeResponseBodies", False)

        # This seems to not work with Firefox 61.0.2 :(
		#profile.set_preference("devtools.netmonitor.har.enableAutoExportToFile", True)
		#profile.set_preference("devtools.netmonitor.har.forceExport", True)
		#profile.set_preference("devtools.netmonitor.responseBodyLimit", 100)
		#profile.set_preference("devtools.toolbar.enabled", True)
		#profile.set_preference("devtools.toolbar.visible", False)
		#profile.set_preference("devtools.toolbox.selectedTool", "netmonitor")
		#profile.set_preference("extensions.netmonitor.har.autoConnect", True)
		#profile.set_preference("extensions.netmonitor.har.contentAPIToken", "test")
		#profile.set_preference("devtools.netmonitor.har.defaultLogDir", HARDIR)
		#profile.set_preference("devtools.netmonitor.har.pageLoadedTimeout", 500)
	except Exception as err:
		print("Failed to load HAR Export Trigger extension:" + str(err) + " - Is it in the same directory?")
	firefox_options = webdriver.FirefoxOptions()
	firefox_options.add_argument("-devtools")


	socket.setdefaulttimeout(SOCKETTIMEOUT) # Sadly, this seems to be the only thing that works to actually get a timeout
	try:
		driver = webdriver.Firefox(firefox_profile=profile, firefox_binary=FirefoxBinary(FIREFOX_PATH), options=firefox_options)
	except FileNotFoundError:
		print("Could not find firefox binary at " + FIREFOX_PATH + " -- trying to use default")
		driver = webdriver.Firefox(firefox_profile=profile, options=firefox_options)

	time.sleep(1)

	successfulruns = []

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

		try:
			time.sleep(1)
			driver.get(URL_TO_FETCH)
		except socket.timeout:
			sys.stderr.write("Socket timeout for " + URL_TO_FETCH + " - not retrying\n")
		except Exception as e:
			print("Error fetching page " + URL_TO_FETCH + ": " + str(e) + "\n")
			try:
				logNavigationTimings(driver, URL_TO_FETCH, timestamp, unixtimestamp, LOGDIR + "failed_navtimings.log", scenario = SCENARIO)
			except Exception as e:
				print("Could not even log Nav timings for failed page " + str(URL_TO_FETCH) + ": " + str(e))
			sys.exit(-1)
		createDirectory(LOGDIR + "res")

		try:
			logNavigationTimings(driver, URL_TO_FETCH, timestamp, unixtimestamp, LOGDIR + "navtimings.log", scenario = SCENARIO)

		except Exception as e:
			print("Error logging Navigation timings: " + str(sys.exc_info()[0]) + ", " + str(e))
		try:
			logResourceTimings(driver, URL_TO_FETCH, timestamp, printout=False, scenario = SCENARIO)
		except Exception as e:
			print("Error logging Resource timings: " + str(sys.exc_info()[0]) + ", " + str(e))
		try:
			harfile_to_process = logHAR(driver, URL_TO_FETCH, timestamp)
		except Exception as e:
			print("Error logging HAR: " + str(sys.exc_info()[0]) + ", " + str(e))


	print("\nFetched " + URL_TO_FETCH + " " + str(TIMES) + " times, logged to " + LOGDIR)
	driver.close()
