#!/bin/bash

# Script to set up packet captures
# Pass arguments to run.sh:
# * urlfile
# * how many times per url
# * scenario string

# Note: If you execute this as a non-root user, you may first have to allow
# capturing packets.
#
# E.g. on Linux:
# setcap cap_net_raw,cap_net_admin=eip /usr/sbin/tcpdump
# ln -s /usr/sbin/tcpdump /usr/local/bin/tcpdump


if [ "$1" == "" ]
then
    RUNSCRIPT="run.sh"
else
    RUNSCRIPT="$1"
    shift
fi

if [ "$1" != "" ]
then
	WORKLOADARGS="$@"
else
	WORKLOADARGS=""
fi

CAPTURE_LOCAL=("any")

echo "Capture traffic on: $CAPTURE_ON, runscript: $RUNSCRIPT, WORKLOADARGS: ${WORKLOADARGS[@]}"


tcpdumpfilter="port 80 or port 53 or port 443"

DATERUN=$(date +%Y-%m-%dT%H:%M)

DIRECTORY="pcap/capture-$DATERUN"
WORKLOAD_LOGDIR="../testdata"

mkdir -p "pcap"
mkdir -p "$DIRECTORY"

echo "    Killing all previous instances of tcpdump and nc"

killall -q tcpdump

echo ""

i=0
for capture in "${CAPTURE_LOCAL[@]}"
do
	interface=$capture
	echo "    Local: Starting tcpdump interface $interface filtering ($tcpdumpfilter) ..."
	tcpdump -i $interface -w- "$tcpdumpfilter" > $DIRECTORY/local:${capture}.pcap &
	sleep 1
	i=`expr $i + 1`
done

echo ""

echo "======"
echo "Done setting up capture!!"
echo "======"

if [ -x "$RUNSCRIPT" ]
then
	echo ""
	echo "$RUNSCRIPT $WORKLOADARGS"
	source "$RUNSCRIPT" $WORKLOADARGS
	sleep 5
	echo ""
else
	echo "No worklodscript. Just sleeping..."
	sleep 5
fi


echo "======"
echo "Tearing down capture!!"
echo "======"

echo ""

echo "    Local: Stopping tcpdump..."
killall tcpdump
sleep 1

echo "    Trying to match $RUNSCRIPT output with a log from ${WORKLOAD_LOGDIR}..."

if [[ "$RUNSCRIPT" == *run.sh && -d "$WORKLOAD_LOGDIR" ]]
then
	# Get most recent log dir

	logdir=$(ls ${WORKLOAD_LOGDIR} | grep ^run- | tail -n 1)
	echo "    Most recent log file: $logdir"
	dateoflogfile=$(echo $logdir | grep -Eo '[[:digit:]]{4}-[[:digit:]]{2}-[[:digit:]]{2}T[[:digit:]]{2}:[[:digit:]]{2}')

	echo "    Comparing ${dateoflogfile:1:-2} with ${DATERUN:1:-2}"
	# If that new log dir is more recent than DATERUN (=when capture script started)
	# then they probably belong together, so we put them together
	if [[ "${dateoflogfile:1:-2}" == "${DATERUN:1:-2}" || "$dateoflogfile" > "$DATERUN" ]]
	then
		echo "    Copying this capture to $WORKLOAD_LOGDIR/$logdir"
		mkdir -p "$WORKLOAD_LOGDIR/$logdir/pcap"
		mv ./$DIRECTORY/*.pcap "$WORKLOAD_LOGDIR/$logdir/pcap/"
		mv ./$DIRECTORY/*.log "$WORKLOAD_LOGDIR/$logdir/"
		rmdir ./$DIRECTORY
		echo "	Done with $WORKLOAD_LOGDIR/$logdir/"
	else
		echo "    Not copying"
	fi
fi
