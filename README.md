This repository contains some scripts to automatically download web pages and analyze page loads, e.g., extracting performance metrics such as Page Load Time.

These scripts were tested on Debian stable, using Firefox 61.0.2, Selenium 3.14.0, geckodriver 0.21.0, and har-export-trigger-0.61.1 (the latter is provided with this repository).

Download web pages
-----------

	load/*
        webtimings.py       Fetch a web page and log its Navigation Timings, Resource Timings, and HAR file
        fetchurl.sh         Fetch URLs from a file 1 or more times, log data (see above)

Evaluate generated data
------------------------

	eval/*
