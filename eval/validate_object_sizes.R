#!/usr/bin/Rscript
# Compare different timing metrics for the same page

source("plottimings.R")

PRINT_SOME_MISMATCHES = FALSE


PRINT_SUMMARY = TRUE
SPLIT_SUMMARY_BY = c("browser")
# "methodology" refers to the tool(s) used to fetch the page, e.g., Firefox + Marionette
# "workload" refers to the list of pages, e.g., Alexa 1000
# "browser" refers to just the browser, e.g., Firefox + Marionette


logprefix="data/"

# Parse command line arguments, determine which runs will be read
logruns = runstoread(commandArgs(trailingOnly=TRUE))

logprefix=logruns$logprefix
runs = logruns$runs

OUTPUTDIR=paste(logprefix, runs[length(runs)], "/plots", sep="")


# Read in data, compute "HAR bodylen - headerlen" because of known HAR bug (it adds the headers to the bodySize)
data = read_runs_objectsize_validation(logprefix, runs)

# Bug in Firefox - it adds headerSize of response bodySize - so we subtract it again
data[["har_bodylen_-_headerlen"]] = data$har_bodylen - data$har_headerlen
data[["har_bodylen"]] = ifelse((grepl("selenium", as.character(data$run)) | grepl("marionette", as.character(data$run))), data[["har_bodylen_-_headerlen"]], data[["har_bodylen"]])

headersize_metrics = c("trace_headerlen", "har_headerlen")

bodylen_metrics = c("trace_bodylen", "har_bodylen", "har_contentlengthheader", "res_bodylen")

totallen_metrics = c("trace_tcplen", "har_transfersize")

# Compare all headersize metrics and all bodylen metrics with each other
result = compute_compare_metrics(data, headersize_metrics)
data = result$data
all_header_comparisons = result$all_comparisons

result = compute_compare_metrics(data, bodylen_metrics)
data = result$data
all_bodylen_comparisons = result$all_comparisons

result = compute_compare_metrics(data, totallen_metrics)
data = result$data
all_totallen_comparisons = result$all_comparisons


comparisons_to_plot = c("trace_headerlen_-_har_headerlen", "har_headerlen_-_trace_headerlen", "trace_bodylen_-_har_bodylen", "har_bodylen_-_trace_bodylen", "trace_bodylen_-_har_contentlengthheader", "har_contentlengthheader_-_trace_bodylen", "trace_bodylen_-_res_bodylen", "res_bodylen_-_trace_bodylen")
plot_comparison_data = compute_comparison_dataframe(data, comparisons_to_plot)

plot.timings.cdfs(plot_comparison_data, metrics="datadiff", splitby="comparison", plot="eps", filename=paste(OUTPUTDIR, "/ecdf_", "validation_header_body_sizes", sep=""), mainlabel="Data differences", xlabel="Difference in header or body size [Bytes]", log="x")



data_with_contentlengthheader = subset(data, har_contentlengthheader > 0)
data_with_res = subset(data, res_bodylen > 0)

data_non_3xx_and_with_content = subset(data, (http_status < 300 | http_status >= 400) & trace_bodylen > 0)

if (PRINT_SUMMARY) {
	split1 = split_dataframe_by_factors(data, SPLIT_SUMMARY_BY)
	data = split1$data
	splitfactor = split1$splitfactor
	data_with_contentlengthheader = split_dataframe_by_factors(data_with_contentlengthheader, SPLIT_SUMMARY_BY)$data
	data_with_res = split_dataframe_by_factors(data_with_res, SPLIT_SUMMARY_BY)$data
	data_non_3xx_and_with_content = split_dataframe_by_factors(data_non_3xx_and_with_content, SPLIT_SUMMARY_BY)$data

	for (factorlevel in levels(splitfactor)) {
		subsetdata = fix.factors(subset(data, splitfactor == factorlevel))
		if (nrow(subsetdata) == 0) {
			cat("\n\tNo data for", as.character(factorlevel), "\n\n")
			next
		}
		cat("\n\t", as.character(factorlevel), ": \n\n")

		cat("=== For all data computed from trace: ===\n")
		for (comparison in c(comparisons_to_plot, all_totallen_comparisons)) {
			print_comparison_summary(subsetdata, comparison)
		}
		cat("\n")

		cat("=== For data with Content-Length header: ===\n")
		print_comparison_summary(subset(data_with_contentlengthheader, splitfactor == factorlevel), "trace_bodylen_-_har_contentlengthheader")
		cat("\n")

		cat("=== For data with Resoure Timing: ===\n")
		print_comparison_summary(subset(data_with_res, splitfactor == factorlevel), "trace_bodylen_-_res_bodylen")

		cat("=== For data non 3xx and with content, if it exists ===\n")
		print_comparison_summary(subset(data_non_3xx_and_with_content, splitfactor == factorlevel & data_non_3xx_and_with_content[["har_bodylen"]] > 0), "trace_bodylen_-_har_bodylen")
		print_comparison_summary(subset(data_non_3xx_and_with_content, splitfactor == factorlevel & data_non_3xx_and_with_content[["res_bodylen"]] > 0), "trace_bodylen_-_res_bodylen")
		cat("\n")
	}
}

if (PRINT_SOME_MISMATCHES) {
	# Compare header sizes, excluding known cases where it's off

	# If har_headerlen <= 0, no headers got logged - perhaps the packet was not processed by the browser
	# e.g., it gave up on the object and retried
	data_with_headerlen = subset(data, har_headerlen > 0)
	print_top_n(data_with_headerlen, c("trace_headerlen_-_har_headerlen"), printcolumns=c("page", "uri"))
	print_top_n(data_with_headerlen, c("har_headerlen_-_trace_headerlen"), printcolumns=c("page", "uri"))

	# Remaining cases to be expected here:
	# For some packets, there's a difference in the range of -20 .. 400 Bytes (trace_headerlen - har_headerlen)
	# --> HAR sometimes counts less bytes than are actually in the trace (we checked), or slightly more.
	# The browser usually parses and processes the headers, and then reconstructs what it thinks the header size is
	# from its data. This might not be the exact same as the headers that were in the original packet.

	# In cases where HAR counted more bytes, we found that some actual packets were missing the status phrase,
	# e.g., the packet contained only "204" instead of "204 No Content".
	# The browser internally only reads the number code, as the status phrase is redundant information.
	# Later on, the browser computes the header size using both the number and the status phrase, as if it had been
	# in the packet. The difference in header size was exactly the length of the status phrase (+ separator).

	# In cases where HAR counted less bytes, we found that this is most off when there's cookies.
	# The more cookies there are, the bigger the difference.


	# Compare body sizes, excluding known cases where it's off

	# Resource and HAR body len might be way too big for 3xx status codes and for some cases with 0 trace_bodylen.
	# This is probably a bug in the HAR body size computation, where 0 bytes were received, but >0 bytes were logged.
	# Also, it seems like HAR bodylen always counts the headers on top, so let's compare with the version
	# where we subtracted the header size.
	print_top_n(data_non_3xx_and_with_content, c("res_bodylen_-_trace_bodylen", "har_bodylen_-_trace_bodylen"), printcolumns=c("page", "uri"))

	# Resource and HAR body len are -1 if they did not get logged -- exclude those
	# --> Only look at data with resource or HAR bodySize > 0
	print_top_n(subset(data, (res_bodylen > 0)), c("trace_bodylen_-_res_bodylen"), printcolumns=c("page", "uri"))
	print_top_n(subset(data, (data[["har_bodylen"]] > 0)), c("trace_bodylen_-_har_bodylen"), printcolumns=c("page", "uri"))

	# Content Length Header is -1 in case it was missing in the packet
	# --> Only look at data with Content-Length header
	print_top_n(subset(data_with_contentlengthheader, data_with_contentlengthheader[["trace_bodylen_-_har_contentlengthheader"]] > 0), c("trace_bodylen_-_har_contentlengthheader"), printcolumns=c("page", "uri", "run"))
	print_top_n(subset(data_with_contentlengthheader, data_with_contentlengthheader[["har_contentlengthheader_-_trace_bodylen"]] > 0), c("har_contentlengthheader_-_trace_bodylen"), printcolumns=c("page", "uri", "run"))
}
