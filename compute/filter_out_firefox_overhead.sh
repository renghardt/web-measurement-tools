#!/bin/bash
#
# Filter out traffic that does not belong to page load from trace
#
# This script includes name resolutions and IP addresses that we saw
# and they might differ for you.


RUN="$1"

PCAPFILE="pcap/local:eth0.pcap"

# Filtering out: DNS Queries to search.services.mozilla.com and blocklists.settings.services.mozilla.com
# which happen at every Firefox startup even though we have told Firefox to be quiet,
# as well as traffic to and from IP addresses that were resolved from these queries in out case

tshark -r "${RUN}/${PCAPFILE}" -Y '!(dns.qry.name == "search.services.mozilla.com") and !(dns.qry.name == "blocklists.settings.services.mozilla.com") and !(ip.addr == 54.186.210.44) and !(ip.addr == 52.35.13.105) and !(ip.addr == 35.160.229.116) and !(ip.addr == 54.186.24.102) and !(ip.addr == 34.208.112.187) and !(ip.addr == 52.35.195.171) and !(ip.addr == 192.5.6.30) and !(ip.addr == 192.33.14.30) and !(ip.addr == 192.31.80.30) and !(ipv6.addr == 2001:503:a83e::2:30) and !(ipv6.addr == 2001:503:231d::2:30) and !(ipv6.addr == 2001:503:83eb::30)' -w "${RUN}/cleaned_trace.pcap"

mv "${RUN}/cleaned_trace.pcap" "${RUN}/${PCAPFILE}"
