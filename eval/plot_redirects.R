#!/usr/bin/Rscript
# Plot number of redirects and additional latency for page load

source("plottimings.R")

logprefix="data/"

# Parse command line arguments, determine which runs will be read
logruns = runstoread(commandArgs(trailingOnly=TRUE))

logprefix=logruns$logprefix
runs = logruns$runs

data = readpageruns(logprefix=logprefix, runs=runs)

OUTPUTDIR=paste(logprefix, runs[length(runs)], "/plots", sep="")

# Number of redirects (HTTP 301 or 302) before first HTTP 200
#print(summarizedata(data, "har_redirects_before_first_200", index="methodology"))

redirectlist = list()
for (thisrun in levels(data$run)) {
	for (num_redirects in seq(0, max(data[["har_redirects_before_first_200"]]))) {
		datasubset = fix.factors(subset(data, run == thisrun & har_redirects_before_first_200 == num_redirects))
		redirectlist = c(redirectlist, list(data.frame(number_of_redirects = as.factor(num_redirects), run=thisrun, methodology = as.factor(get_methodology_label(thisrun)), workload=as.factor(get_workload(thisrun)), num_occurences=nrow(datasubset))))
	}
}
redirects_df = do.call(rbind, redirectlist)
#str(redirects_df)

barplottimings(redirects_df, metrics="num_occurences", mainlabel="", splitby=c("number_of_redirects", "workload"), aggregate="median", metricslabel="Frequency in data set", scenariolabel="HTTP 301 or 302 before first 200", filename=paste(OUTPUTDIR, "/barplot_redirects", sep=""), plot="eps", print=F)

plot.timings.cdfs(data, metrics="har_redirects_before_first_200", mainlabel="", splitby="workload", plot="eps", filename=paste(OUTPUTDIR, "/ecdf_har_redirects", sep=""), xlabel="Number of redirects")

# Time until the first browsing event (usually DNS start) that led to the load of the first HTTP 200
# this is basically the time that the browser wasted fetching redirect pages
plot.timings.cdfs(subset(data, har_first200starttime > 0), metrics="har_first200starttime", splitby="workload", plot="eps", filename=paste(OUTPUTDIR, "/ecdf_har_first200starttime", sep=""), mainlabel="", xlabel="Time [ms]", log="x")

quantiles = c(0.5, 0.9, 0.95, 0.99, 0.999)
cat("Redirect time quantiles:", paste(quantiles, collapse="\t"), "\n\t\t\t", paste(quantile(subset(data, har_first200starttime > 0)[["har_first200starttime"]], quantiles, na.rm=T), collapse="\t"), "\n\n")

morethan1 = subset(subset(data, har_first200starttime > 0), har_first200starttime > 1000)
cat("More than 1 second:", nrow(morethan1) / nrow(subset(data, har_first200starttime > 0)) * 100, "%\n")

# How many percent of the total Page Load Time do the initial redirects take up
# Total Page Load Time = very start of it all until onLoad time (as reported in HAR)
data$har_redirecttime_by_plt = data[["har_first200starttime"]] / data[["har_onload_time"]]
plot.timings.cdfs(data, metrics="har_redirecttime_by_plt", mainlabel="", splitby="run", plot="eps", filename=paste(OUTPUTDIR, "/ecdf_har_redirects_by_plt", sep=""), xlabel="Redirect time / time until onLoad [%]")

# Look only at page loads with 1 or more redirects:
# Divide duration of the redirects by number of redirects
# to get an estimate of the time spent per redirect
data_with_redirects = fix.factors(subset(data, har_redirects_before_first_200 > 0))
data_with_redirects$har_redirecttime_by_num_redirects = data_with_redirects[["har_first200starttime"]] / data_with_redirects[["har_redirects_before_first_200"]]
plot.timings.cdfs(data_with_redirects, metrics="har_redirecttime_by_num_redirects", mainlabel="", splitby="run", plot="eps", filename=paste(OUTPUTDIR, "/ecdf_har_redirects_by_num_redirects", sep=""), xlabel="Redirect time / number of redirects [ms]")
