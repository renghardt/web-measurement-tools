#!/bin/bash
# Script that fetches a URL n times using selenium and logs their completion times
#

URL="http://www.debian.org"

TIMES=1 # How often to fetch the URL

SCENARIO="firsttry"

if [ "$1" == '' ];
then
	echo "Usage: $0 <URLFILE> [<TIMES>] [<SCENARIO>] [<LOGPREFIX>]"
	echo "URLFILE: Text file containing one or more URLs, one each line"
	echo "TIMES: How often to fetch the URL (default: $TIMES)"
	echo "SCENARIO: String describing the scenario"
	echo "LOGPREFIX: Where to store the results (default: $LOGPREFIX)"
	exit 1
else
	URLFILE="$1"
fi

if [ "$2" != '' ];
then
	TIMES="$2"
fi

if [ "$3" != '' ];
then
	SCENARIO="$3"
fi

DATERUN=$(date +%Y-%m-%dT%H:%M)

if [ "$4" != '' ];
then
	LOGPREFIX="$4"
else
    LOGPREFIX="log/run-$DATERUN-browser"
fi


mkdir -p "$LOGPREFIX"

# Outer loop: Try number 1 .. n
for (( i=0; i < $TIMES; ++i )); #i in `seq 1 "$TIMES"`;
do
	echo "Try $((i+1))/$TIMES"

	# Middle loop: URLs
	while IFS=, read -r line || [[ -n "$line" ]]
	do
		u="$line"

		echo "Fetching $u"
	
		echo "calling: ./webtimings.py $u ${POLICYNAMES[$p]},$SCENARIO 1 $LOGPREFIX/" "${POLICYNAMES[$p]}"
		./webtimings.py $u "${POLICYNAMES[$p]},$SCENARIO" 1 "$LOGPREFIX/" "${POLICYNAMES[$p]}"
		exitstatus=$?
        killall -q firefox

		echo "Got exit status $exitstatus"

		echo "Done fetching $u ($((i+1)) out of $TIMES times)"
		echo ""

	done < $URLFILE

    killall -q firefox-esr
    killall -q firefox
done
