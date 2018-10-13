This repository contains some scripts to automatically download web pages and analyze page loads, e.g., extracting performance metrics such as Page Load Time.

These scripts were tested on Debian stable, using Firefox 62.0.2 and har-export-trigger-0.6.1 (the latter is provided with this repository).

To make a packet capture, your local user needs permissions to use tcpdump.
See capture.sh script for instructions for Linux.


How to load pages
=================

`cd load`

With default list of URLs and packet capture (if your current user can use tcpdump):

`./capture.sh`

Without packet capture:

`./run.sh`

With custom list of URLs, more than once per URL, and/or custom scenario log string:

1. Provide a list of URLs in a file, one URL per line
2. Call `./capture.sh ./run.sh $URLFILE $HOW_MANY_TIMES_PER_URL $SCENARIO_LOGSTRING $LOG_DIR`
3. Find data in $LOG_DIR (defaults to ../testdata/run-$(date +%Y-%m-%dT%H:%M)-test)

How to compute data based on page load data
=================

1. `cd compute`
2. `./computetimings.py`
3. `./validate_object_sizes.py`

Step 2 outputs:
* Which page loads failed and which succeeded (to terminal and success_or_fail.log)
* For succeeded: Summary of HAR file and Resource Timings (to terminal and final_timings.log)
* For succeeded: Comparison of all object sizes and whether they are in HAR, Resource Timings, or both (to compare_har_res.log)

Step 3 outputs:
* Page loads considered (to terminal)
* All objects successfully read from packet capture trace, with matching HAR file and Resource Timings objects, if available (to object_sizes_trace.log)


Overview of scripts
===================

Download web pages
-----------

	load/*
        capture.sh                      Set up packet capture, then call run.sh (or other)
        run.sh                          Create log directory, then run fetchurl.sh and log its output
        fetchurl.sh                     Fetch URLs from a file 1 or more times, log data (see above)
        load_url_using_marionette.py    Fetch a URL using Firefox and Marionette
                                        Log Navigation Timings, Resource Timings, and a HAR file
        load_url_using_chrome.py        Fetch a URL using Chrome and DevTools, log data (see above)

        load_url_using_selenium.py      Fetch a URL using Selenium and geckodriver, log data (see above)

Evaluate generated data
------------------------

	eval/*
