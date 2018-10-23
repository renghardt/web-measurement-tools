#!/usr/bin/Rscript
# Compare different timing metrics for the same page

source("plottimings.R")


PRINT_SUMMARY = TRUE
SPLIT_SUMMARY_BY = c("methodology", "workload")
# "methodology" refers to the tool(s) used to fetch the page, e.g., Firefox + Marionette
# "workload" refers to the list of pages, e.g., Alexa 1000

INCLUDE_TRANSFERSIZE = FALSE
# Whether to include Byte Index computed from HAR transfer size (Chrome proprietary)

PLOT_ABS_DIFFERENCES = TRUE

logprefix="data/"

# Parse command line arguments, determine which runs will be read
logruns = runstoread(commandArgs(trailingOnly=TRUE))

logprefix=logruns$logprefix
runs = logruns$runs

OUTPUTDIR=paste(logprefix, runs[length(runs)], "/plots", sep="")

data = readpageruns(logprefix=logprefix, runs=runs)

# Check if all numbers of resources and sum of object sizes are the same for all attempts of the same page
# Fail if not -- this will obviously not work for data "in the wild".
#check_all_equal(c("number_of_resources", "sum_of_object_sizes"))


# Filter out any data with negative load times -- thanks Chrome :/ -- and data without firstPaint
data = fix.factors(subset(data, data$har_first200starttime >= 0 & data$har_onload_time > 0 & data$har_content_load_time > 0 & data$fetchStart >= 0 & data$responseStart > 0 & data$domContentLoadedEventStart > 0 & data$loadEventStart > 0 ))

data[["TimeToFirstByte"]] = data[["responseStart"]]

data[["Redirect_time_HAR"]] = data[["har_first200starttime"]]
data[["Redirect_time_Navt"]] = data[["fetchStart"]]

# Plot PLT with and without redirects
# based on HAR file timestamps

data[["PLT_with_redirects"]] = data$har_onload_time
data[["PLT_without_redirects"]] = data$har_onload_time - data[["Redirect_time_HAR"]]

loadtime_metrics = c("PLT_with_redirects", "PLT_without_redirects")

# Put all load times into a data frame where one row is one load time and "metrics" says which load time
# so we can plot them to a CDF
loadtimes_df = put_metrics_in_dataframe(data, loadtime_metrics)
loadtimes_df$value = ifelse( loadtimes_df$value < 0, 0, loadtimes_df$value)

plot.timings.cdfs(loadtimes_df, metrics="value", splitby="metrics", plot="eps", filename=paste(OUTPUTDIR, "/ecdf_loadtimes", sep=""), mainlabel="", xlabel="Time [ms]", log="x", legendposition="topleft")

dataframe_per_page = data.frame(page = levels(data$page))
dataframe_per_page[["median_PLT_with_redirects_per_page"]] = with(data, tapply(X=data[["PLT_with_redirects"]], IND=page, FUN=median))
dataframe_per_page[["median_PLT_without_redirects_per_page"]] = with(data, tapply(X=PLT_without_redirects, IND=page, FUN=median))
str(dataframe_per_page)

data_per_page_df = put_metrics_in_dataframe(dataframe_per_page, c("median_PLT_with_redirects_per_page", "median_PLT_without_redirects_per_page"))

plot.timings.cdfs(data_per_page_df, metrics="value", splitby="metrics", plot="eps", filename=paste(OUTPUTDIR, "/ecdf_loadtimes_by_page", sep=""), mainlabel="", xlabel="Time [ms]", legendposition="topleft", log="x")


# Put Object Index and Byte Index into data frame, plot CDF
object_index_metrics = c("har_object_index", "res_object_index")
byte_index_metrics = c( "har_byte_index_bodyorcontent", "har_byte_index_bodysize", "res_byte_index")
if (!is.null(data[["har_byte_transfersize"]]) & INCLUDE_TRANSFERSIZE) {
	if (any(!is.na(data[["har_byte_transfersize"]]))) {
		byte_index_metrics = c(byte_index_metrics, "har_byte_index_transfersize")	
	}
}

object_byte_index_df = put_metrics_in_dataframe(data, c(object_index_metrics, byte_index_metrics))

plot.timings.cdfs(object_byte_index_df, metrics="value", splitby="metrics", plot="eps", filename=paste(OUTPUTDIR, "/ecdf_object_byte_index", sep=""), mainlabel="", xlabel="Object or Byte Index [ms]", log="x")


# Compute Object Index and Byte Index differences
result = compute_compare_metrics(data, object_index_metrics, abs=PLOT_ABS_DIFFERENCES, print=F)
data = result$data
all_object_index_comparisons = result$all_comparisons

result = compute_compare_metrics(data, byte_index_metrics, abs=PLOT_ABS_DIFFERENCES, print=F)
data = result$data
all_byte_index_comparisons = result$all_comparisons

object_index_comparison_data = compute_comparison_dataframe(data, all_object_index_comparisons)
byte_index_comparison_data = compute_comparison_dataframe(data, all_byte_index_comparisons)

plot.timings.cdfs(object_index_comparison_data, metrics="datadiff", splitby="comparison", plot="eps", filename=paste(OUTPUTDIR, "/ecdf_object_index_comparison", sep=""), mainlabel="", xlabel=paste(ifelse(PLOT_ABS_DIFFERENCES == TRUE, "Absolute d", "D"), "ifference of Object Index [ms]", sep=""), legendposition="topleft", log="x")
plot.timings.cdfs(byte_index_comparison_data, metrics="datadiff", splitby="comparison", plot="eps", filename=paste(OUTPUTDIR, "/ecdf_byte_index_comparison", sep=""), mainlabel="", xlabel=paste(ifelse(PLOT_ABS_DIFFERENCES == TRUE, "Absolute d", "D"), "ifference of Byte Index [ms]", sep=""), legendposition="topleft", log="x")

# Compute differences of Object and Byte Index relative to maximum of the two
data[["object_index_rel_diff"]] = apply(data, 1, function(x) { return(ifelse(all(is.na(c(x[["res_object_index"]], x[["har_object_index"]]))), NA, as.numeric(x[["res_object_index_-_har_object_index"]]) / max(as.numeric(x[["res_object_index"]]), as.numeric(x[["har_object_index"]]), na.rm=T) * 100))})
data[["byte_index_rel_diff_res_-_bodyorcontent"]] = apply(data, 1, function(x) { return(ifelse(all(is.na(c(x[["har_byte_index_bodyorcontent"]], x[["res_byte_index"]]))), NA, as.numeric(x[["res_byte_index_-_har_byte_index_bodyorcontent"]]) / max(as.numeric(x[["res_byte_index"]]), as.numeric(x[["har_byte_index_bodyorcontent"]]), na.rm=T) * 100)) } )
data[["byte_index_rel_diff_res_-_har"]] = apply(data, 1, function(x) { return(ifelse(all(is.na(c(x[["res_byte_index"]], x[["har_byte_index_bodysize"]]))), NA, as.numeric(x[["res_byte_index_-_har_byte_index_bodysize"]]) / max(as.numeric(x[["res_byte_index"]]), as.numeric(x[["har_byte_index_bodysize"]]), na.rm=T) * 100)) })
data[["byte_index_rel_diff_bodyorcontent_-_har"]] = apply(data, 1, function(x) { return(ifelse(all(is.na(c(x[["har_byte_index_bodysize"]], x[["har_byte_index_bodyorcontent"]]))), NA, as.numeric(x[["har_byte_index_bodysize_-_har_byte_index_bodyorcontent"]]) / max(as.numeric(x[["har_byte_index_bodysize"]]), as.numeric(x[["har_byte_index_bodyorcontent"]]), na.rm=T) * 100))})
if (INCLUDE_TRANSFERSIZE & !is.null(data[["har_byte_index_transfersize_-_har_byte_index_bodyorcontent"]])) {
	data[["byte_index_rel_diff_transfersize_-_bodyorcontent"]] = apply(data, 1, function(x) { return(ifelse(all(is.na(c(x[["har_byte_index_transfersize"]], x[["har_byte_index_bodyorcontent"]]))), NA, as.numeric(x[["har_byte_index_transfersize_-_har_byte_index_bodyorcontent"]]) / max(as.numeric(x[["har_byte_index_transfersize"]]), as.numeric(x[["har_byte_index_bodyorcontent"]]), na.rm=T) * 100))})
}

rel_diff_metrics = c("byte_index_rel_diff_bodyorcontent_-_har", "byte_index_rel_diff_res_-_bodyorcontent", "byte_index_rel_diff_res_-_har")
if (INCLUDE_TRANSFERSIZE & !is.null(data[["har_byte_index_transfersize_-_har_byte_index_bodyorcontent"]])) {
	rel_diff_metrics = c(rel_diff_metrics, "byte_index_rel_diff_transfersize_-_bodyorcontent")
}

rel_byte_index_df = put_metrics_in_dataframe(data, rel_diff_metrics)
plot.timings.cdfs(rel_byte_index_df, metrics="value", splitby="metrics", plot="eps", filename=paste(OUTPUTDIR, "/ecdf_rel_object_byte_index", sep=""), mainlabel="", xlabel="Relative Byte Index Difference [%]", xlim=c(0, 100), legendposition="bottomright")

# Plot shares (percentages) of load time metrics that redirects take up
# based on Navigation Timings

olddata = data
data = subset(data, firstPaint > 0)

data[["Redirect_share_of_PLT"]] = data[["Redirect_time_Navt"]] / data[["loadEventStart"]] * 100
data[["Redirect_share_of_domContentLoaded"]] = data[["Redirect_time_Navt"]] / data[["domContentLoadedEventStart"]] * 100
data[["Redirect_share_of_TTFB"]] = data[["Redirect_time_Navt"]] / data[["TimeToFirstByte"]] * 100
data[["Redirect_share_of_firstPaint"]] = data[["Redirect_time_Navt"]] / data[["firstPaint"]] * 100

redirect_share_metrics = c("Redirect_share_of_PLT", "Redirect_share_of_domContentLoaded", "Redirect_share_of_firstPaint", "Redirect_share_of_TTFB")

# Only plot this if we have any data with firstPaint > 0
if (nrow(data) > 0) {
	shares_df = put_metrics_in_dataframe(data, redirect_share_metrics)

	plot.timings.cdfs(shares_df, metrics="value", splitby="metrics", plot="eps", filename=paste(OUTPUTDIR, "/ecdf_shares", sep=""), mainlabel="", xlabel="Redirect Time / Load Time [%]", xlim=c(0,100), legendposition="bottomright")
}

data = olddata

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

        summarizedata(subsetdata, loadtime_metrics)
		#summarizedata(subsetdata, redirect_share_metrics)
		quantiles = c(0.1, 0.5, 0.9, 0.95, 0.99, 0.999)
		for (metric in loadtime_metrics) {
			if (!is.null(subsetdata[[metric]])) {
				cat(metric, "quantiles:\n", paste(quantiles, collapse="\t"), "\n", paste(round(quantile(subsetdata[[metric]], quantiles, na.rm=T), digits=2), collapse="\t"), "\n\n")
			}
		}
		for (metric in redirect_share_metrics) {
			if (!is.null(subsetdata[[metric]])) {
				cat(metric, "quantiles:\n", paste(quantiles, collapse="\t"), "\n", paste(round(quantile(subsetdata[[metric]], quantiles, na.rm=T), digits=2), collapse="\t"), "\n\n")
			}
		}
	}
	cat("Overall:\n")
	quantiles = c(0.1, 0.5, 0.9, 1)
	for (metric in loadtime_metrics) {
		if (!is.null(subsetdata[[metric]])) {
			cat(metric, "quantiles:\n", paste(quantiles, collapse="\t"), "\n", paste(round(quantile(subsetdata[[metric]], quantiles, na.rm=T), digits=2), collapse="\t"), "\n\n")
		}
	}
	quantiles = c(0.5, 0.9, 1)
	for (metric in redirect_share_metrics) {
		if (!is.null(subsetdata[[metric]])) {
			cat(metric, "quantiles:\n", paste(quantiles, collapse="\t"), "\n", paste(round(quantile(data[[metric]], quantiles, na.rm=T), digits=2), collapse="\t"), "\n\n")
		}
	}
	for (metric in rel_diff_metrics) {
		if (!is.null(subsetdata[[metric]])) {
			cat(metric, "quantiles:\n", paste(quantiles, collapse="\t"), "\n", paste(round(quantile(data[[metric]], quantiles, na.rm=T), digits=2), collapse="\t"), "\n\n")
		}
	}
}
