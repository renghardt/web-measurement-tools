#!/usr/bin/Rscript
# Compare different timing metrics for the same page

# Caution: This scripts consumes a lot of memory for large data sets
# such as 1000 page loads!

source("plottimings.R")


PRINT_SUMMARY = FALSE
SPLIT_SUMMARY_BY = c("methodology", "workload")
# "methodology" refers to the tool(s) used to fetch the page, e.g., Firefox + Marionette
# "workload" refers to the list of pages, e.g., Alexa 1000


PLOT_ABS_DIFFERENCES = TRUE

logprefix="data/"

# Parse command line arguments, determine which runs will be read
logruns = runstoread(commandArgs(trailingOnly=TRUE))

logprefix=logruns$logprefix
runs = logruns$runs

data = readpageruns(logprefix=logprefix, runs=runs)
data$har_requests_before_onload = data$har_number_of_requests - data$har_finished_after_onload

# Metrics one might use as "number of objects":
# HAR file requests that were finished before onLoad and had status code >=100 and <400
number_metrics = c("har_requests_before_onload", "har_non_failed_requests", "res_number_of_resources_finished_before_onload")

# Metrics one might use as "sum of object sizes":
# As logged in HAR file: (for one page load, before onLoad event)
#   Sum of all Response Body Sizes
#   Sum of all Content-Length headers
#   Sum of all content sizes (as logged in HAR file)
#   Sum of Response Body Sizes, but if this is not present, Content-Length header
# As logged using Resource Timings: (for the same page load, before onLoad event)
#   Sum of encodedBodySize
#   Sum of decodedBodySize
size_metrics = c("har_sum_of_respbodysize", "har_sum_of_contentlength", "har_sum_of_contentsize", "har_sum_of_bodyorcontent", "res_sum_of_encoded", "res_sum_of_decoded")#, "smart_total_page_size")

OUTPUTDIR=paste(logprefix, runs[length(runs)], "/plots", sep="")

cex=1


# Compare numbers of objects:
result = compute_compare_metrics(data, number_metrics, abs=PLOT_ABS_DIFFERENCES, print=F)
data = result$data
all_number_comparisons = result$all_comparisons

number_comparison_data = compute_comparison_dataframe(data, c("res_number_of_resources_finished_before_onload_-_har_non_failed_requests"), splitby="workload")

filename_comparison = "compare_numbers_of_objects"

plot.timings.cdfs(number_comparison_data, metrics="datadiff", splitby="comparison", plot="eps", filename=paste(OUTPUTDIR, "/ecdf_", filename_comparison, sep=""), mainlabel="", xlabel=paste(ifelse(PLOT_ABS_DIFFERENCES == TRUE, "Absolute d", "D"), "ifference in object count", sep=""), legendposition="bottomright", log="x")



# Compare object sizes:
result = compute_compare_metrics(data, size_metrics, abs = PLOT_ABS_DIFFERENCES)
data = result$data
all_size_comparisons = result$all_comparisons

size_comparison_data = compute_comparison_dataframe(data, all_size_comparisons)

filename_comparison = "compare_pagesizes"


# The really interesting ones are the ones we might not expect to differ much:
# Sum of response body sizes and sum of "response body size but if it's not there take content-length"
# Sum of response body sizes (HAR) and sum of encodedBodySize (Resource Timings) -- both should be Bytes on the wire
# Sum of "response body size or content length" (HAR) and sum of encodedBodySize (Resource Timings) -- both should be Bytes on the wire
# Sum of content sizes (HAR) and sum of decodedBodySize (Resource Timings) -- both should be decompressed Bytes

# Plot all differences, or only those where most or all values are > 0 and will thus be plotted in log scale ECDF

#subset_of_comparisons = c("har_sum_of_bodyorcontent_-_har_sum_of_respbodysize", "har_sum_of_respbodysize_-_har_sum_of_bodyorcontent", "har_sum_of_respbodysize_-_res_sum_of_encoded", "res_sum_of_encoded_-_har_sum_of_respbodysize", "har_sum_of_contentsize_-_res_sum_of_decoded", "res_sum_of_decoded_-_har_sum_of_contentsize")
if (PLOT_ABS_DIFFERENCES) {
	subset_of_comparisons = c("har_sum_of_bodyorcontent_-_har_sum_of_respbodysize", "res_sum_of_encoded_-_har_sum_of_respbodysize", "res_sum_of_decoded_-_har_sum_of_contentsize")
} else {
	subset_of_comparisons = c("har_sum_of_respbodysize_-_har_sum_of_bodyorcontent", "har_sum_of_respbodysize_-_res_sum_of_encoded", "har_sum_of_contentsize_-_res_sum_of_decoded", "res_sum_of_decoded_-_har_sum_of_contentsize")
}

comparison_data_to_plot = fix.factors(subset(size_comparison_data, size_comparison_data$comparison %in% subset_of_comparisons))
comparison_data_to_plot$comparison = factor(comparison_data_to_plot$comparison, levels= subset_of_comparisons)
comparison_data_to_plot = comparison_data_to_plot[with(comparison_data_to_plot, order(comparison)),]
plot.timings.cdfs(comparison_data_to_plot, metrics="datadiff", splitby="comparison", plot="eps", filename=paste(OUTPUTDIR, "/ecdf_", filename_comparison, sep=""), mainlabel="Data differences", xlabel="Difference [Bytes]", log="x", xlim=c(1, get_xmax(comparison_data_to_plot, "datadiff")), legendposition="topleft")


# Assuming our "smart" total page size is correct, what are the differences?
#everything_against_smart = c("har_sum_of_bodyorcontent_-_smart_total_page_size", "har_sum_of_respbodysize_-_smart_total_page_size", "smart_total_page_size_-_res_sum_of_encoded")

#comparison_data_to_plot = fix.factors(subset(size_comparison_data, size_comparison_data$comparison %in% everything_against_smart))
#comparison_data_to_plot$comparison = factor(comparison_data_to_plot$comparison, levels= everything_against_smart)
#comparison_data_to_plot = comparison_data_to_plot[with(comparison_data_to_plot, order(comparison)),]

#plot.timings.cdfs(comparison_data_to_plot, metrics="datadiff", splitby="comparison", plot="eps", filename=paste(OUTPUTDIR, "/ecdf_smart_", filename_comparison, sep=""), mainlabel="", xlabel="Data difference [Bytes]", log="x", xlim=c(1, get_xmax(comparison_data_to_plot, "datadiff")), legendposition="topleft")



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

		cat("Number of objects", ifelse(PLOT_ABS_DIFFERENCES == TRUE, "absolute", ""), "difference:\n\n")
		print_comparison_summary(subsetdata, "res_number_of_resources_finished_before_onload_-_har_non_failed_requests")

		quantiles = c(0, 0.001, 0.01, 0.5, 0.9, 0.95, 0.99)
		cat("HAR (Non-Failed) entries - Resource Timing entries,", ifelse(PLOT_ABS_DIFFERENCES == TRUE, "absolute", ""), "difference quantiles:\n\t", paste(quantiles, collapse="\t"), "\n\t", paste(quantile(subsetdata[["res_number_of_resources_finished_before_onload_-_har_non_failed_requests"]], quantiles, na.rm=T), collapse="\t"), "\n\n")

		cat("Total page sizes:\n\n")
		for (comparison in subset_of_comparisons) {
			print_comparison_summary(subsetdata, comparison)
		}
		#for (comparison in everything_against_smart) {
		#	print_comparison_summary(data, comparison)
		#}
	}

	cat("Total page sizes for all:\n\n")
	for (comparison in subset_of_comparisons) {
		print_comparison_summary(data, comparison)
	}
}

#print_top_n(data, all_number_comparisons, printcolumns=c("page"))
#print_top_n(data, subset_of_comparisons, printcolumns=c("page"))

#print_top_n(data, c("har_status1xx", "har_status4xx", "har_status5xx", "har_unknown_status", "har_no_reply"), printcolumns=c("page"))
