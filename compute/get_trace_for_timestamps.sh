#!/bin/bash
#
# Get all DNS and HTTP traffic from a trace, log some relevant info to file
# This only works if a pcap file exists!

SSLKEYLOGFILE="ssl_keys.log"

PCAPFILE="pcap/local:eth0.pcap"


RUN="$1"

PAGENAME="$2"

TIMESTAMP1="$3"
TIMESTAMP1_PRINT=${TIMESTAMP1/ /+}
TIMESTAMP1_PRINT=${TIMESTAMP1_PRINT//:/-}

TIMESTAMP2="$4"

dir_before=$PWD
cd "$RUN"
echo "Getting packets from $TIMESTAMP1 to $TIMESTAMP2 for pcap/${PAGENAME}+${TIMESTAMP1_PRINT}_packets.log"

tshark -o ssl.keylog_file:$SSLKEYLOGFILE -Y "frame.time >= \"$TIMESTAMP1\" and frame.time < \"$TIMESTAMP2\"" -r $PCAPFILE -T fields -Eseparator=, -e frame.protocols -e ip.src -e ip.dst -e http.request.method -e http.request.uri -e http.response.code -e http2.header.name -e http2.header.value -e dns.resp.name -e dns.a -e dns.aaaa > "pcap/${PAGENAME}+${TIMESTAMP1_PRINT}_packets.log"

cd $dir_before
