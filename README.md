This repository contains some scripts to automatically download web pages and analyze page loads, e.g., extracting performance metrics such as Page Load Time.

These scripts were tested on Debian stable, using Firefox 62.0.2 and har-export-trigger-0.6.1 (the latter is provided with this repository).


How to use
==========

1. Provide a list of URLs in a file, one URL per line
2. Call `./fetchurl.sh $URLFILE $HOW_MANY_TIMES_PER_URL $SCENARIO_LOGSTRING $LOG_DIR`
3. Find data in $LOG_DIR (defaults to ./log/run-$(date +%Y-%m-%dT%H:%M)-test)


Overview of scripts
===================

Download web pages
-----------

	load/*
        fetchurl.sh                     Fetch URLs from a file 1 or more times, log data (see above)
        load_url_using_marionette.py    Fetch a URL using Firefox and Marionette
                                        Log Navigation Timings, Resource Timings, and a HAR file

        load_url_using_selenium.py      Fetch a URL using Selenium and geckodriver, log data (see above)

Evaluate generated data
------------------------

	eval/*
