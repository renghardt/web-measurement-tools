#!/usr/bin/Rscript
# Compare different timing metrics for the same page

# Caution: This script consumes a lot of memory for large data sets
# such as 1000 page loads!

source("plottimings.R")


PRINT_SUMMARY = TRUE
SPLIT_SUMMARY_BY = c("browser")
#SPLIT_SUMMARY_BY = c("methodology", "workload")
# "methodology" refers to the tool(s) used to fetch the page, e.g., Firefox + Marionette
# "workload" refers to the list of pages, e.g., Alexa 1000

PLOT_ABS_DIFFERENCES = TRUE

INCLUDE_DECOMPRESSED_METRICS = FALSE

logprefix="data/"

# Parse command line arguments, determine which runs will be read
logruns = runstoread(commandArgs(trailingOnly=TRUE))

logprefix=logruns$logprefix
runs = logruns$runs

OUTPUTDIR=paste(logprefix, runs[length(runs)], "/plots", sep="")

data = read_runs_compare_objects(logprefix=logprefix, runs=runs)

# Bug in Firefox - it adds headerSize of response bodySize - so we subtract it again
data[["har_bodylen_-_headerlen"]] = data$har_bodylen - data$har_headerlen
data[["har_bodylen"]] = ifelse((grepl("selenium", as.character(data$run)) | grepl("marionette", as.character(data$run))), data[["har_bodylen_-_headerlen"]], data[["har_bodylen"]])


bodylen_metrics = c("har_contentlengthheader", "har_bodylen", "res_bodylen")
decompressed_len_metrics = c("har_contentsize", "res_decoded")

# Compare all metrics with each other
result = compute_compare_metrics(data, bodylen_metrics, abs=PLOT_ABS_DIFFERENCES, exclude_lower_zero=F)
data = result$data
all_bodylen_comparisons = result$all_comparisons

result = compute_compare_metrics(data, decompressed_len_metrics, abs=PLOT_ABS_DIFFERENCES)
data = result$data
all_decompressed_len_comparisons = result$all_comparisons

#for (comparison in comparisons_to_plot) {
#	print_comparison_summary(data, comparison)
#}


metrics_to_plot = c(bodylen_metrics)
if (INCLUDE_DECOMPRESSED_METRICS) {
	metrics_to_plot = c(metrics_to_plot, decompressed_len_metrics)
}

objectsizedata = list()
for (objectsizemetrics in metrics_to_plot) {
	newdata = data.frame(metrics = as.character(objectsizemetrics), size=data[[objectsizemetrics]], page=data$page, run=data$run)
	objectsizedata = c(objectsizedata, list(newdata))
}
objectsizes_df = do.call(rbind, objectsizedata)

plot.timings.cdfs(subset(objectsizes_df, size > 0), metrics="size", splitby="metrics", plot="eps", filename=paste(OUTPUTDIR, "/ecdf_objectsizes_all", sep=""), mainlabel="", xlabel="Object size [Bytes]", log="x")

comparisons_to_plot = c("har_bodylen_-_har_contentlengthheader", "har_contentlengthheader_-_har_bodylen", "res_bodylen_-_har_contentlengthheader", "har_contentlengthheader_-_res_bodylen", "har_bodylen_-_res_bodylen", "res_bodylen_-_har_bodylen", "har_contentsize_-_res_decoded", "res_decoded_-_har_contentsize")
if (PLOT_ABS_DIFFERENCES) {
	comparisons_to_plot = c(all_bodylen_comparisons)
	if (INCLUDE_DECOMPRESSED_METRICS) {
		comparisons_to_plot = c(comparisons_to_plot, all_decompressed_len_comparisons)
	}
}

plot_comparison_data = compute_comparison_dataframe(data, comparisons_to_plot)


plot.timings.cdfs(plot_comparison_data, metrics="datadiff", splitby="comparison", plot="eps", filename=paste(OUTPUTDIR, "/ecdf_diff_objectsizes", sep=""), xlabel=paste(ifelse(PLOT_ABS_DIFFERENCES == TRUE, "Absolute D", "d"), "ifference [Bytes]", sep=""), log="x", legendposition="bottomright")

if (PRINT_SUMMARY) {
	split1 = split_dataframe_by_factors(data, SPLIT_SUMMARY_BY)
	data = split1$data
	splitfactor = split1$splitfactor

	for (factorlevel in levels(splitfactor)) {
		subsetdata = fix.factors(subset(data, splitfactor == factorlevel))
		if (nrow(subsetdata) == 0) {
			cat("\n\tNo data for", as.character(factorlevel), "\n\n")
			next
		}
		cat("\n\t", as.character(factorlevel), ": \n\n")

		# For how many objects do we get a Content-Length header, a HAR body Size, a Resource Timings body Size?
		data_with_contentlengthheader = fix.factors(subset(subsetdata, har_contentlengthheader >= 0))
		data_without_contentlengthheader = fix.factors(subset(subsetdata, is.na(har_contentlengthheader) | har_contentlengthheader < 0))
		cat("Got content-length header:\t\t\t\t", nrow(data_with_contentlengthheader) / nrow(subsetdata) * 100, "% (", nrow(data_with_contentlengthheader), "/", nrow(subsetdata), ")\n")

		data_3xx = fix.factors(subset(data_without_contentlengthheader, (http_status >= 300 & http_status < 400)))

		data_no_3xx = fix.factors(subset(data_without_contentlengthheader, (http_status < 300 | http_status >= 400)))
		cat("of rest, 3xx:\t\t\t\t\t\t", nrow(data_3xx) / nrow(subsetdata) * 100, "% (", nrow(data_3xx), "/", nrow(subsetdata), "), no 3xx: ", nrow(data_no_3xx), "\n")

		data_with_resource_size = fix.factors(subset(data_no_3xx, res_bodylen > 0))
		data_without_resource_size = fix.factors(subset(data_no_3xx, is.na(res_bodylen) | res_bodylen <= 0))
		cat("Of rest, non-3xx with nonzero Resource Timing size:\t", nrow(data_with_resource_size) / nrow(subsetdata) * 100, "% (", nrow(data_with_resource_size), "/", nrow(subsetdata), ")\n")

		data_with_bodysize = fix.factors(subset(data_without_resource_size, !is.na(data_without_resource_size[["har_bodylen"]]) & data_without_resource_size[["har_bodylen"]] >= 0))
		cat("Of rest, non-3xx which has a body size:\t\t\t", nrow(data_with_bodysize) / nrow(subsetdata) * 100, "%(", nrow(data_with_bodysize), "/", nrow(subsetdata), ")\n")

		#data_zero = fix.factors(subset(data_without_resource_size, is.na(data_without_resource_size[["har_bodylen"]]) | data_without_resource_size[["har_bodylen"]] == 0))
		data_without_anything = fix.factors(subset(data_without_resource_size, is.na(data_without_resource_size[["har_bodylen"]]) | data_without_resource_size[["har_bodylen"]] < 0))
		#cat("Of rest, non-3xx with zero:\t\t\t\t", nrow(data_zero) / nrow(data) * 100, "%(", nrow(data_zero), "/", nrow(data), ")\n")
		cat("Of rest, non-3xx without anything:\t\t\t", nrow(data_without_anything) / nrow(subsetdata) * 100, "%(", nrow(data_without_anything), "/", nrow(subsetdata), ")\n")


		# Summary of comparisons of object sizes
		for (comparison in comparisons_to_plot){
			print_comparison_summary(subsetdata, comparison)
		}
		data_with_no_bodylen = subset(subsetdata, har_bodylen < 0 & har_transfersize > 2000)
		if (nrow(data_with_no_bodylen) > 0) {
			cat("\nFor data with no body size: (", nrow(data_with_no_bodylen) / nrow(subsetdata) * 100, "% )\n")
			summarizedata(data_with_no_bodylen, c("har_contentlengthheader", "har_transfersize", "http_version", "http_status", "found_where"))
		}
		http2data = subset(subsetdata, http_version == "http/2.0")
		if (nrow(http2data) > 0) {
			summarizedata(, "har_bodylen")
		}
	}
	cat("For the entire dataset:\n")
	# Summary of comparisons of object sizes
	for (comparison in comparisons_to_plot){
		print_comparison_summary(data, comparison)
	}

}

