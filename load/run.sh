#!/bin/bash
# Start MAMma with config adjusted, then execute a workload script
# Move results to their own directory

# Arguments
# * urlfile        - a file that contains URLs for the workloadscript, one per line
# * how often to fetch the url
# * scenario string (for logging)

yes| rm *.log

exec > >(tee -ia run_stdout.log)
exec 2> >(tee -ia run_stderr.log)

WORKLOADSCRIPT="./fetchurl.sh"

WORKLOAD_LOGFILE="workload_output.log"

SCENARIO="test"

export SSLKEYLOGFILE="ssl_keys.log"


if [ ! -x "$WORKLOADSCRIPT" ]
then
	WORKLOADSCRIPT="./fetchurl.sh"
fi

if [ "$1" == "" ]
then
	urlfile="success_urls"
else
	urlfile="$1"
fi

if [ "$2" == "" ]
then
    TIMES=1
else
    TIMES=$2
fi

if [ "$3" != "" ]
then
    SCENARIO="$3"
fi



DATERUN=$(date +%Y-%m-%dT%H:%M)

echo "urlfile: $urlfile"
cp "$urlfile" "urlfile-${urlfile}.log"

scenarioname="${SCENARIO}_${urlfile}"

echo ""
echo "Set up $scenarioname"
echo ""
echo ""

LOGPREFIX="../testdata/run-$DATERUN-$scenarioname"
mkdir -p "data"
mkdir -p $LOGPREFIX

echo "Running workload script $WORKLOADSCRIPT $urlfile"

# this is for fetchurl (browser instrumentation):
source "$WORKLOADSCRIPT" "$urlfile" "$TIMES" "$scenarioname" "$LOGPREFIX" 2>&1 >"$WORKLOAD_LOGFILE"

echo "Done with workload, exiting"

# Delete temporary browser profiles
rm -rf /tmp/foo*

mv *.log "$LOGPREFIX/"
