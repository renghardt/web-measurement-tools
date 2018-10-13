#!/bin/bash
# If this script fails with "regular expression compile failed (missing operand)", you may need to install GNU awk (sudo apt install gawk)

run="$1"

cd "$run"
#awk '/Run 1\/1 - Fetching/ { OFS=","; print $5,$7 }' workload_output.log > starttimes.log
awk -F"+| " '/Run 1\/1 - Fetching/ { OFS=","; gsub("-", ":", $8); printf "%s,%s %s\n", $5,$7,$8 }' workload_output.log > starttimings.log
