#!/bin/bash
#
# Filter out traffic that does not belong to page load from trace
#
# This script includes name resolutions and IP addresses that we saw
# and they might differ for you.

RUN="$1"

PCAPFILE="pcap/local:eth0.pcap"

# Filtering out: DNS Queries to www.gstatic.com and accounts.google.com which happen at every Chrome startup
# even though we have told Chrome to be quiet,
# as well as traffic to and from IP addresses that were resolved from these queries in out case

tshark -r "${RUN}/${PCAPFILE}" -Y '!(dns.qry.name == "www.gstatic.com") and !(dns.qry.name == "accounts.google.com") and !(ip.addr == 216.58.212.131) and !(ip.addr == 216.58.212.141) and !(ip.addr == 172.217.17.109) and !(ip.addr == 172.217.17.99) and !(ipv6.addr == 2a00:1450:400e:800::2003) and !(ipv6.addr == 2a00:1450:400e:800::200d) and !(ipv6.addr == 2a00:1450:400e:806::2003) and !(ipv6.addr == 2a00:1450:400e:806::200d)' -w "${RUN}/cleaned_trace.pcap"

mv "${RUN}/cleaned_trace.pcap" "${RUN}/${PCAPFILE}"
