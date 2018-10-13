#!/usr/bin/Rscript
# Helper functions to read and plot timings and other metrics
# by Theresa Enghardt

# Functions that need to be sourced - should exist in the top level directory
# of this repository
if (file.exists("R_functions.R")) {
    source("R_functions.R")
}

readpagetimings <- function(logprefix=list.files(path="data/", pattern="run-*")[1], filename="final_timings.log", print=TRUE) {
	timingdata = data.frame()
	timinglist = list()

    colnames_to_use=c("page", "scenario", "starttimestamp", "fetchStart", "responseStart", "domInteractive", "domContentLoadedEventStart", "domContentLoadedEventEnd", "domComplete", "loadEventStart", "loadEventEnd", "firstPaint",
        "har_number_of_requests", "har_finished_after_onload", "har_no_reply", "har_status1xx", "har_status200", "har_status_other2xx", "har_status3xx", "har_status4xx", "har_status5xx", "har_unknown_status", "har_non_failed_requests", "har_starttime",
        "har_first200starttime", "har_redirects_before_first_200", "har_last_request_start_before_onload", "har_last_resource_end_before_onload", "har_onload_time", "har_content_load_time",
		"har_object_index", "har_byte_index_bodysize", "har_byte_index_bodyorcontent", "har_byte_index_transfersize",
        "har_sum_of_respbodysize", "har_sum_of_contentlength", "har_sum_of_contentsize", "har_sum_of_bodyorcontent", "har_sum_of_transfersize",
        "res_number_of_resources", "res_finished_after_onload", "res_number_of_resources_finished_before_onload", "res_last_resource_end_before_onload",
        "res_sum_of_encoded", "res_sum_of_decoded",
		"res_object_index", "res_byte_index",
		"smart_total_page_size") # as exported by computetiming.py
	files = list.files(path=logprefix, pattern=filename)
    if (print) {
        cat("Found files matching", filename, ":", files, "\n")
    }
	if(length(files) == 0) {
        cat("No files found under", logprefix, "! Returning NULL \n")
        return(NULL)
	}
	for (i in 1:length(files)) {
		filename = paste(logprefix,files[i], sep="")
		fileinfo = file.info(filename)
		if (fileinfo$size == 0) {
			cat("File",filename,"is empty! Returning NULL\n")
			return(NULL)
		}
        if (print) {
            cat("Reading file", paste(logprefix, files[i], sep=""), "\n")
        }
		tdata = read.csv(paste(logprefix,files[i], sep=""), header=FALSE)
		colnames(tdata) = colnames_to_use
        tdata$client = as.factor("browser")
        tdata$actual_time = tdata$loadEventEnd
		tdata$workload = gsub("http://.*/pics-","",tdata$page)
		tdata$workload = gsub("*.html","",tdata$workload)
		tdata$workload = as.factor(gsub("-",":",tdata$workload))
        tdata$starttimestamp = as.numeric(as.POSIXct(gsub("T", " ", tdata$starttime)))
        tdata = tdata[with(tdata, order(tdata[["starttimestamp"]])),]

		timinglist[[i]] = tdata
	}
	timingdata = do.call(rbind, timinglist)

	if (print) {
		str(timingdata)
	}
	return(timingdata)
}

readpageruns <- function(logprefix="data/", runs=list.files(path=logprefix, pattern="^run*"), filename="final_timings.log", print=FALSE) {

	timingdata = data.frame()
	timinglist = list()

	for (i in 1:length(runs)) {
		run = runs[i]
		cat("  [", i, "/", length(runs), "] Reading in data from", run, "\n")
		data = readpagetimings(paste(logprefix, run, "/", sep=""), filename=filename, print=print)
		if (is.null(data)) {
			next
		}
		gsub("run-", "", run)
		datematch = regexpr("[[:digit:]]{4}-[[:digit:]]{2}-[[:digit:]]{2}T[[:digit:]]{2}:[[:digit:]]{2}-",run)
		dateofrun = substring(run, datematch, datematch+attr(datematch, "match.length")-2)
		data$run = as.factor(run)
		data$methodology = as.factor(get_methodology_label(run))
		data$browser = as.factor(get_browser_label(run))
		data$workload = as.factor(get_workload(run))
		gsub(dateofrun, "", run)
		scenario = as.factor(substring(run, datematch+attr(datematch, "match.length")))
		if (print) {
			cat("  Dateofrun:", dateofrun, "scenario:", scenario, "\n")
		}
		data$scenario = scenario

		timinglist[[i]] = data
	}
    timinglistlength1 = length(timinglist[[1]])
    if (all(lapply(timinglist, function(x) length(x)) == timinglistlength1)) {
        # All list items are similar - we can combine them to a single data frame
        timingdata = do.call(rbind, timinglist)
    } else {
        timinglist = timinglist[vapply(timinglist, Negate(is.null), NA)]
        cat("Warning: Lengths of data items do not match (different clients?)\n")
        cat("Some columns were filled with NAs.\n")
        timingdata = do.call(rbind, filldataframes(timinglist))
    }

	if (any(grepl("MAM", runs))) {
		mam = sapply(timingdata$scenario, function(x) {matchobj=regexpr("[A-Z]+", x); return(ifelse(attr(matchobj, "match.length") > 2 , substring(x, matchobj, matchobj+attr(matchobj, "match.length")-1), "MAM"))})
		timingdata$mam = factor(mam)
	}
	if (print) {
		str(timingdata)
	}
	return(timingdata)
}

# Make a boxplot of timings (or other data) in a data set
# indexed by workload and policy (or other splitby factors)
boxplottimings <- function(timingdata, filename="boxplot.pdf", log="", pages=NULL, metrics="wallclock_time", splitby=c("policy", "workload"), cex=1, mainlabel="", ylabel="", plot="terminal", exclude="", spacebelow=22) {

	if (is.null(pages)) {
		if (is.null(timingdata$page) && !is.null(timingdata$file)) {
			timingdata$page = timingdata$file
			timingdata$workload = timingdata$file
		}
		pages = levels(timingdata$page)
	}

	if (!is.null(timingdata$page)) {
        pagestosubset = pages

        if (mainlabel == "" && length(pages) == 1) {
            mainlabel = paste("Comparison of scenarios for", pages, "pages")
        }
        #cat("Boxplot of", metrics, "for", pagestosubset, "\n")

		# Subset the pages
		timingdata = subset(timingdata, (page %in% pagestosubset))
		timingdata$page = factor(timingdata$page, unique(timingdata$page))
		timingdata$workload = timingdata$page
		pages = levels(timingdata$page)
	} else {
		cat("WARNING: Cannot filter out pages from data!\n")
	}

	if (mainlabel == "") {
        mainlabel = paste("Comparison of scenarios for", paste(pages, collapse=", "))
	}
    if (ylabel == "") {
        ylabel=gsub("_", " ", paste(metrics, "[s]"))
    }
	boxplotmetrics(timingdata, filename=filename, metrics=metrics, log=log, splitby=splitby, cex=cex, mainlabel=mainlabel, ylabel=ylabel, plot=plot, spacebelow=spacebelow, exclude=exclude)
}

# Make a bar plot of timings in a data set
#    Options:
#        metrics		What timing metrics to plot (default: actual_time)
#        aggregate		How to aggregate timings for same workload and policy (default: median)
#        horiz			Draw a horizontal barplot, bars from left to right? (default: FALSE)
#        metricslabel	What to call the timing metrics axis
#        plotmetricslog Draw a logarithmic metrics axis? (default: FALSE)
#        scenariolabel  What to call the scenario axis
#        metricslimit	Limit of the metrics axis
#        plotlegend		Plot a legend explaining the scenarios? (default: TRUE)
#        plotsimplifiedscenarioaxis 	On the scenario axis, plot only one label for every scenario (3 bars)
#        plotscenarioaxis				On the scenario axis, plot a label for every bar
#
barplottimings <- function(timingdata, metrics="actual_time", mainlabel="Timings per scenario", names=c(), policynames=c(), splitby=c("workload", "policy"), cex=1, aggregate="median", horiz=FALSE, metricslabel=paste(aggregate, metrics, "[s]"), plotmetricslog=FALSE, scenariolabel="", metricslimit=c(), plotlegend=TRUE, plotsimplifiedscenarioaxis=TRUE, plotscenarioaxis=FALSE, filename="barplot", plot="", spacebelow=4, print=FALSE) {

	prepare_file(plot=plot, filename=filename, spacebelow=spacebelow, width=13, height=10)

	if(print) {
		cat(ifelse(horiz, "Horizontal ", "Vertical "))
		cat("Barplot of", metrics, "\n")
	}

	errorbarlengths = c()

	# Compute aggregate timings - default is median - and error bars
	if (aggregate != "" & aggregate != "hist") {
		if (print & "workload" %in% splitby) {
			cat("Order of pages within function:", levels(timingdata$page), "\n")
		}
		if (splitby[1] != "workload") {
			timingdata$page = timingdata[[splitby[1]]]
		}
		plotdata = c()
		errorbar_lower = c()
		errorbar_upper = c()

		for (thispage in levels(timingdata$page)) {
			thispagedata = fix.factors(subset(timingdata, page == thispage))
			if (print) {
				cat("Adding data for", thispage, ":", thispagedata[[metrics]], "\n")
			}
			newplotdata = tapply(X=thispagedata[[metrics]], IND=thispagedata[[splitby[2]]], FUN=aggregate)
			if (print) {
				cat("New plotdata", newplotdata, "\n")
			}
			plotdata = c(plotdata, newplotdata)
			# Error bar: mean/median +- tinv(1-alpha,n-1)*std/sqrt( n )
			# alternatively, binomial
			#new_errorbar_lower = newplotdata - tapply(X=thispagedata[[metrics]], IND=thispagedata[[splitby[2]]], FUN=function(x) { sort(x)[qbinom(c(.025,.975), length(x), 0.5)][1] })
			new_errorbar_lower = newplotdata - tapply(X=thispagedata[[metrics]], IND=thispagedata[[splitby[2]]], FUN=function(x) { if (length(x) <= 2) { return(x[1]) }; n = length(x); index= round((n/2) - (1.96*sqrt(n)/2)); return(sort(x)[max(index, 1)]) })
			new_errorbar_upper = tapply(X=thispagedata[[metrics]], IND=thispagedata[[splitby[2]]], FUN=function(x) { if (length(x) <= 2) { return(x[1]) }; n = length(x); index=round((n/2) + (1.96*sqrt(n)/2)); return(sort(x)[index]) }) - newplotdata
			#new_errorbar_upper = tapply(X=thispagedata[[metrics]], IND=thispagedata[[splitby[2]]], FUN=function(x) { sort(x)[qbinom(c(.025,.975), length(x), 0.5)][2] }) - newplotdata
			new_errorbar_lower[is.na(new_errorbar_lower)] = 0
			new_errorbar_upper[is.na(new_errorbar_upper)] = 0
			#cat("New errorbar_lower", new_errorbar_lower, "\n")
			#cat("New errorbar_upper", new_errorbar_upper, "\n")
			errorbar_lower = c(errorbar_lower, new_errorbar_lower)
			errorbar_upper = c(errorbar_upper, new_errorbar_upper)

		}
		#plotdata = tapply(X=timingdata[[metrics]], IND=timingdata[[splitby[1]]]:timingdata[[splitby[2]]], FUN=aggregate)
		if (length(names) == 0) {
			names = unique(factor(timingdata[[splitby[1]]]:timingdata[[splitby[2]]]))
		}
	} else {
		if (aggregate == "hist") {
			breaks = c(0, 0.5, seq(1, max(timingdata[[metrics]])))
			if (length(names) == 0) {
				names = c(0, seq(1, max(timingdata[[metrics]])))
			}
			histogram_of_data = tapply(X=timingdata[[metrics]], IND=timingdata[[splitby[1]]]:timingdata[[splitby[2]]], FUN=hist, breaks=breaks)
			plotdata = c()
			for (n in names) {
				for (h in histogram_of_data) {
					plotdata = c(plotdata, h$counts[n+1])
				}
			}

			if (print) {
				cat("Histogram plotdata: ", plotdata, ", names: ", names, "\n")
			}
		} else {
			plotdata = timingdata[[metrics]]
			if (length(names) == 0) {
				names = factor(timingdata[[splitby[1]]]:timingdata[[splitby[2]]])
			}
		}
		errorbar_upper = c()
		errorbar_lower = c()
	}
	if (print) {
		cat(length(plotdata), "items to plot:", plotdata, "\n")
	}

	if (all(grepl(":", names))) {
		# Make labels for scenario axis
		names = strsplit(levels(names), split=":")
		names = sapply(names, function(x) {ifelse((length(x)>2), paste(toupper(x[3]), " (", x[2], " * ", toupper(x[1]), ")", sep=""), paste(toupper(x[2]), " (", x[1], ")", sep=""))})
	}

	if (length(metricslimit) == 0) {
		if (length(errorbar_upper) > 0) {
			metricslimit = c(0, max(plotdata + errorbar_upper,na.rm=T))
		} else {
			metricslimit=c(0, max(plotdata))
		}
	}

	x_las = 2
	xaxt = "s"
	yaxt = "s"
	log=""
	numberofpolicies = length(levels(timingdata[[splitby[2]]]))

	# If we plot the simplified scenario axis (one label for three bars, indicating their shared scenario),
	# do not plot the usual scenario axis with one label for every bar
	if (plotsimplifiedscenarioaxis == TRUE) {
		plotscenarioaxis = FALSE
	}

	# For horizontal barplot (bars go from left to right)
	if (horiz) {

		# Set x axis for metrics
		xlabel = metricslabel
		if (plotmetricslog) {
			log="x"
			if (metricslimit[1] == 0) {
				metricslimit[1] = min(plotdata)
			}
		} else {
			metricslimit[1]=0
		}
		xlimit = metricslimit

		# Set y axis for scenario
		if (!plotscenarioaxis) {
			yaxt = "n"
		}
		if (plotscenarioaxis || plotsimplifiedscenarioaxis) {
			margins=par()$mar
			par(mar=c(margins[1], 5+cex*2, margins[3], margins[4]))
		}
		ylabel = scenariolabel
		ylimit = c(0, length(names) + 0.5)

	} else {
	# Vertical barplot (default), bars go from bottom to top

		# Set x axis for scenario
		xlabel = scenariolabel
		xlimit = c(0, length(names) + 0.5)
		if (!plotscenarioaxis) {
			xaxt = "n"
		} else {
			margins=par()$mar
			par(mar=c(5+cex*2, margins[2], margins[3], margins[4]))
		}

		# Set y axis for metrics
		ylabel = metricslabel
		if (plotmetricslog) {
			log="y"
			if (metricslimit[1] == 0) {
				metricslimit[1] = min(plotdata)
			}
		} else {
			metricslimit[1] = 0
		}
		ylimit = metricslimit
	}

	#policycolors=c("azure4","azure3","white")
	#policycolors=gray(1:7 / 8)[seq(1,7, length.out=numberofpolicies)]
	policycolors=c("#202020", "#404040", "#808080", "#A0A0A0", "#C0C0C0", "#DFDFDF")[1:length(levels(timingdata[[splitby[2]]]))]
	#cat("Policy colors:", policycolors, "\n")
	if (length(policynames) == 0) {
		policynames = as.character(unique(timingdata[[splitby[2]]]))
	}
	policynames=sapply(policynames, plotlabel.human.readable)
	spaceinbarplot=c(0.2,rep(0,numberofpolicies-1))
	#spaceinbarplot=c(0.5, 0, 0.5, 0, 0.5, 0)
	if (print) {
		cat("space in barplot:", spaceinbarplot, "\n")
		cat("metricslim:",metricslimit,"\n")
		cat("ylim:",ylimit,"\n")
		cat("error bar lengths:", errorbarlengths, "\n")
	}
	if (all(nchar(names)) < 4) {
		x_las = 1
	}

	# Draw the barplot
	bp = barplot(plotdata, log=log, horiz=horiz, space=spaceinbarplot, names.arg=rep(names, length.out=length(plotdata)), las=x_las, xlab=xlabel, ylab=ylabel, main=mainlabel, col=policycolors, xaxt=xaxt, yaxt=yaxt, ylim=ylimit)

	# Draw error bars
	if (length(errorbar_upper) > 0 && any(errorbar_upper > 0)) {
		options(warn=-1)
		if (horiz) {
			arrows(plotdata+errorbar_upper, bp, plotdata-errorbar_lower, bp, angle=90, code=3, length=0.05)
		} else {
			arrows(bp, plotdata+errorbar_upper, bp, plotdata-errorbar_lower, angle=90, code=3, length=0.1)
		}
		options(warn=0)
	}

	# Make the simplified scenario axis: One label for every 3 bars, indicating the scenario
	if (plotsimplifiedscenarioaxis ) {
		if ("page" %in% splitby | "workload" %in% splitby) {
			workloadnames = levels(unique(timingdata$page))
			workloadnames = gsub("/", "", workloadnames)
		} else {
			workloadnames = levels(timingdata[[splitby[1]]])
		}
		names = rep(names, length.out=length(plotdata))
		if (print) {
			cat(length(names),"names:",names,"\n")
			cat(length(policynames),"policynames:",policynames,"\n")
			cat(length(workloadnames),"workloadnames:",workloadnames,"\n")
		}
		if (horiz) {
			axis(side=2, bp[seq(2,length(names),length.out=length(workloadnames))], labels=workloadnames, las=1)
		} else {
			if (all(nchar(workloadnames) < 4)) {
				wlas = 1
			} else {
				wlas = 2
			}

			if (length(workloadnames) > 8 & any(nchar(workloadnames) > 4)) {
				wlas = 2
			}
			if (length(policynames) == 1) {
				axis_at = bp[seq(1,length(names),length.out=length(workloadnames))]
			}
			if (length(policynames) > 1) {
				axis_at = bp[seq(1,length(names),length.out=length(workloadnames))]+0.5
				axis_at[length(axis_at)] = axis_at[length(axis_at)] - 1
			}
			if (print) {
				cat("Plotting axis labels", workloadnames, "at", axis_at, "with las", wlas, "\n")
			}
			axis(side=1, axis_at, tick=F, labels=workloadnames, las=wlas)
		}
	}

	# Plot a legend of policies
	if (plotlegend) {
		if (length(errorbar_upper) > 0) {
			wheretoplotlegend = find_empty_plotarea(rbind(plotdata+errorbar_upper, plotdata-errorbar_lower), metricslimit, plotmetricslog, dmins=c(0,0,0))
		} else {
			wheretoplotlegend = find_empty_plotarea(plotdata, metricslimit, plotmetricslog, dmins=c(0,0,0))
		}
		if (wheretoplotlegend == "") {
			wheretoplotlegend = "topleft"
			if (print) {
				cat("Cannot find an empty area to plot legend - using", wheretoplotlegend, "\n")
			}
		}
		bty='o'
		inset=0.01
		if (plotmetricslog) {
			bty='n'
		} else {
			inset = 0.05
		}
		legendnames = policynames[1:numberofpolicies]
		if (print) {
			cat("Plotting legend with names", legendnames, "\n")
		}
		l = legend(wheretoplotlegend, inset=inset, legend=legendnames, fill=policycolors, cex=cex, bty=bty)

		if (plotmetricslog) {
			l = l$rect
			xmid = l$left + 0.5* l$w
		}
	}
	if (plot == "pdf" | plot == "eps" | plot == "png") {
		invisible(dev.off())
	}
}

plot.timings.cdfs <- function(data, metrics="wallclock_time", splitby = "policy", print=F, plot="terminal", filename = "cdfs", cex=1, mainlabel="", xlabel="", log="", xlim=NULL, subsetdata=F, legendposition="topleft") {
    prepare_file(plot=plot, filename=filename, width=13, height=10, spacebelow=3)
    splitdata = split(data, data[[splitby]])
    #cat("Split data by", splitby, "- got list of length", length(splitdata), "\n")
    if (xlabel == "") {
        xlabel = metrics
    }
    plot.cdf.list(splitdata, metrics=metrics, mainlabel=mainlabel, xlabel=xlabel, log=log, xlim=xlim, subsetdata=subsetdata, legendposition=legendposition)

	if (plot == "pdf" | plot == "eps" | plot == "png") {
		invisible(dev.off())
	}
}

# Read data on whether page loads failed or succeeded
read_success_or_fail <- function(logprefix=list.files(path="data/", pattern="run-*")[1], filename="success_or_fail.log", print=TRUE)
{
	data <- read.csv(paste(logprefix, filename, sep=""), header=T)

	# Do not have to set column names -- they are in the file
	#	colnames(data) = c("page", "starttime", "does_navtiming_exist", "does_restiming_exist", "does_harfile_exist", "last_event_in_failed_navtiming", "num_dnsreplies", "num_ssl", "num_http", "num_https", "num_httpGET", "num_http301or302", "num_http200")

    if (print) {
        str(data)
    }
	return(data)
}

read_runs_success_or_fail <- function(logprefix="data/", runs=list.files(path=logprefix, pattern="^run*"), filename="success_or_fail.log", print=FALSE) {

	rundata = data.frame()
	rundatalist = list()

	for (i in 1:length(runs)) {
		run = runs[i]
		cat("  [", i, "/", length(runs), "] Reading in data from", run, "\n")
		data = read_success_or_fail(paste(logprefix, run, "/", sep=""), filename=filename, print=print)
		if (is.null(data)) {
			next
		}
		gsub("run-", "", run)
		datematch = regexpr("[[:digit:]]{4}-[[:digit:]]{2}-[[:digit:]]{2}T[[:digit:]]{2}:[[:digit:]]{2}-",run)
		dateofrun = substring(run, datematch, datematch+attr(datematch, "match.length")-2)
		data$run = as.factor(run)
		data$workload = as.factor(get_workload(run))
		data$methodology = as.factor(get_methodology_label(run))
		data$browser = as.factor(get_browser_label(run))
		gsub(dateofrun, "", run)
		scenario = as.factor(substring(run, datematch+attr(datematch, "match.length")))
		if (print) {
			cat("  Dateofrun:", dateofrun, "scenario:", scenario, "\n")
		}
		data$scenario = scenario

		rundatalist[[i]] = data
	}
    rundatalistlength1 = length(rundatalist[[1]])
    if (all(lapply(rundatalist, function(x) length(x)) == rundatalistlength1)) {
        # All list items are similar - we can combine them to a single data frame
        rundata = do.call(rbind, rundatalist)
    } else {
        rundatalist = rundatalist[vapply(rundatalist, Negate(is.null), NA)]
        cat("Warning: Lengths of data items do not match\n")
        cat("Some columns were filled with NAs.\n")
        rundata = do.call(rbind, filldataframes(rundatalist))
    }

	if (print) {
		str(rundata)
	}
	return(rundata)
}

# Read data object size validation, i.e., "ground truth" from the trace
read_objectsize_validation_data <- function(logprefix=list.files(path="data/", pattern="run-*")[1], filename="object_sizes_trace.log", print=TRUE)
{
	data <- read.csv(paste(logprefix, filename, sep=""), header=F)

	# Set column names
	colnames(data) = c("page", "starttime", "resource_starttimestamp", "uri", "http_status", "trace_tcplen", "trace_headerlen", "trace_bodylen", "har_transfersize", "har_headerlen", "har_bodylen", "har_contentlengthheader", "res_bodylen")

    if (print) {
        str(data)
    }
	return(data)
}

read_runs_objectsize_validation <- function(logprefix="data/", runs=list.files(path=logprefix, pattern="^run*"), filename="object_sizes_trace.log", print=FALSE) {

	rundata = data.frame()
	rundatalist = list()

	for (i in 1:length(runs)) {
		run = runs[i]
		cat("  [", i, "/", length(runs), "] Reading in data from", run, "\n")
		data = read_objectsize_validation_data(paste(logprefix, run, "/", sep=""), filename=filename, print=print)
		if (is.null(data)) {
			next
		}
		gsub("run-", "", run)
		datematch = regexpr("[[:digit:]]{4}-[[:digit:]]{2}-[[:digit:]]{2}T[[:digit:]]{2}:[[:digit:]]{2}-",run)
		dateofrun = substring(run, datematch, datematch+attr(datematch, "match.length")-2)
		data$run = as.factor(run)
		data$methodology = as.factor(get_methodology_label(run))
		data$browser = as.factor(get_browser_label(run))
		data$workload = as.factor(get_workload(run))
		gsub(dateofrun, "", run)
		scenario = as.factor(substring(run, datematch+attr(datematch, "match.length")))
		if (print) {
			cat("  Dateofrun:", dateofrun, "scenario:", scenario, "\n")
		}
		data$scenario = scenario

		rundatalist[[i]] = data
	}
    rundatalistlength1 = length(rundatalist[[1]])
    if (all(lapply(rundatalist, function(x) length(x)) == rundatalistlength1)) {
        # All list items are similar - we can combine them to a single data frame
        rundata = do.call(rbind, rundatalist)
    } else {
        rundatalist = rundatalist[vapply(rundatalist, Negate(is.null), NA)]
        cat("Warning: Lengths of data items do not match\n")
        cat("Some columns were filled with NAs.\n")
        rundata = do.call(rbind, filldataframes(rundatalist))
    }

	if (print) {
		str(rundata)
	}
	return(rundata)
}

# Read data comparing resource timing and HAR objects
read_compare_objects <- function(logprefix=list.files(path="data/", pattern="run-*")[1], filename="compare_har_res.log", print=TRUE)
{
	fullfilename = paste(logprefix, filename, sep="")
	data <- read.csv(fullfilename, header=F)

	colnames(data) = c("page", "starttime", "http_status", "http_version", "found_where", "har_transfersize", "har_bodylen", "har_headerlen", "har_contentlengthheader", "har_contentsize", "res_bodylen", "res_decoded", "url")

    if (print) {
        str(data)
    }
	return(data)
}

read_runs_compare_objects <- function(logprefix="data/", runs=list.files(path=logprefix, pattern="^run*"), filename="compare_har_res.log", print=FALSE) {

	rundata = data.frame()
	rundatalist = list()

	for (i in 1:length(runs)) {
		run = runs[i]
		cat("  [", i, "/", length(runs), "] Reading in data from", run, "\n")
		data = read_compare_objects(paste(logprefix, run, "/", sep=""), filename=filename, print=print)
		if (is.null(data)) {
			next
		}
		gsub("run-", "", run)
		datematch = regexpr("[[:digit:]]{4}-[[:digit:]]{2}-[[:digit:]]{2}T[[:digit:]]{2}:[[:digit:]]{2}-",run)
		dateofrun = substring(run, datematch, datematch+attr(datematch, "match.length")-2)
		data$run = as.factor(run)
		data$methodology = as.factor(get_methodology_label(run))
		data$browser = as.factor(get_browser_label(run))
		data$workload = as.factor(get_workload(run))
		gsub(dateofrun, "", run)
		scenario = as.factor(substring(run, datematch+attr(datematch, "match.length")))
		if (print) {
			cat("  Dateofrun:", dateofrun, "scenario:", scenario, "\n")
		}
		data$scenario = scenario

		rundatalist[[i]] = data
	}
    rundatalistlength1 = length(rundatalist[[1]])
    if (all(lapply(rundatalist, function(x) length(x)) == rundatalistlength1)) {
        # All list items are similar - we can combine them to a single data frame
        rundata = do.call(rbind, rundatalist)
    } else {
        rundatalist = rundatalist[vapply(rundatalist, Negate(is.null), NA)]
        cat("Warning: Lengths of data items do not match\n")
        cat("Some columns were filled with NAs.\n")
        rundata = do.call(rbind, filldataframes(rundatalist))
    }

	if (print) {
		str(rundata)
	}
	return(rundata)
}
