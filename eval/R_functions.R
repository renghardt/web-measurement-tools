#!/usr/bin/Rscript 
# Some helper functions
# by Theresa Enghardt

# Disable scientific notation
options(scipen=999)

# maximum realistic value -- reset everything higher to this value
MAX_VALUE=10^32

capitalize <- function(string) {
    return(paste(toupper(substring(string, 1, 1)), substring(string, 2), sep=""))
}

capitalize_protocol_names <- function(string) {
    return(capitalize((gsub("[Tt]cp", "TCP", gsub("[Dd]ns", "DNS", gsub("[Hh]ttp", "HTTP", gsub("[Ss]sl", "SSL", string)))))))
}

split_dataframe_by_factors <- function(data, factors, print=F) {
	if (all(is.na(factors)) | length(factors) <= 0) {
		return(list(data = data, splitfactor = c()))
	}
	splitfactor = data[[factors[1]]]
	if (print) {
		cat("Splitting summary by", factors[1], "- levels:", as.character(unique(splitfactor)), "\n")
	}
	data$splitfactor = data[[factors[1]]]

	if (length(factors) > 1) {
		for (factor in factors[2:length(factors)]) {
			if (print) {
				cat("Also splitting by", as.character(factor), "- levels:", as.character(unique(data[[factor]])), "\n")
			}
			splitfactor = splitfactor:data[[factor]]
			data$splitfactor = data$splitfactor:data[[factor]]
		}
	}
	return(list(data = data, splitfactor = splitfactor))
}

check_all_equal <- function(data, metrics_to_check=c(), splitfactor = "page") {

	# Check if all runs for the same page have the same value for some metrics
	splitdata = fix.factors(split(data, data[[splitfactor]]))

	if (length(metrics_to_check) > 0) {
		for (sdata in splitdata) {
			invalid = check_metrics(sdata, metrics = metrics_to_check, allequal=TRUE)
			if (invalid) {
				stop("Broken value - not plotting\n")
			}
		}
	}
}


# Process command line arguments, return a list with the following items:
# logprefix - the directory containing ^run-* directories, which in turn contain
#             the run data
# runs      - a vector of the names of the individual ^run-* directories to read
#
runstoread <- function(args, logprefix="data/") {

    USAGE="Usage:\n \
          <script> [<logprefix>] [<index of first run> [<number of runs to read>]]\n\n"

    USAGE=paste(USAGE, "\t\tdefault logprefix =", logprefix, "\n")

	if (length(args) > 0) {
        # Argument is a file, might be a directory - take as logprefix
		if (file.exists(args[1])) {
			logprefix=args[1]
			if (substring(logprefix, nchar(logprefix)) != "/") {
				logprefix = paste(logprefix, "/", sep="")
				cat("Using logprefix", logprefix, "\n")
				args = args[-1]
			}
		}
	}

	runs = addruns(args, logprefix, print=FALSE)

	return(list(logprefix=logprefix, runs=runs))
}

addruns <- function(args, logprefix, print=F) {
	runs=c()
	runs_and_args = c(runs, add_runs_from_args(runs, args, logprefix))
	runs = runs_and_args$runs
	if (print) {
	cat("Runs after first call:", runs, "\n")
	}

	while (length(runs_and_args$args) < length(args) && length(runs_and_args$args) > 0) {
		args = runs_and_args$args
		runs_and_args = c(runs, add_runs_from_args(runs, args, logprefix))
		if (print) {
			cat("Adding runs:", runs_and_args$runs, "\n")
		}
		runs = c(runs, runs_and_args$runs)
		if (print) {
			cat("Args now:", args, "and runs_and_args$args:", runs_and_args$args, "\n")
		}
	}
	return(runs)
}

add_runs_from_args <- function(runs, args, logprefix) {

	startfromrun=1
	numberofruns=255

	if (length(args) > 0) {
		# Argument is not a directory, but a number - take as index of the run
		# to start with within the logprefix directory
		if (!is.na(suppressWarnings(as.numeric(args[1])))) {
			startfromrun = as.numeric(args[1])
			cat("Starting from run", startfromrun, "in", logprefix, "\n")
			args = args[-1]
		} else {
			cat("Did not understand argument", args[1], "\n")
			cat(USAGE, "\n")
			stop("Fix your arguments\n")
		}
	}
	# Another argument which is a number - take as the number of runs to read
	if (length(args) > 0) {
		if (!is.na(suppressWarnings(as.numeric(args[1])))) {
			numberofruns = as.numeric(args[1])
			cat("Only reading", numberofruns, "runs\n")
			args = args[-1]
		}
	}

	runs = list.files(path=logprefix, pattern="^run*")
	runs = runs[startfromrun:length(runs)]

	if (numberofruns < length(runs)) {
		runs = runs[1:numberofruns]
	}
	return(list(runs=runs, args=args))
}

filldataframes <- function(datalist) {
    for(i in 1:length(datalist)) {
        for (j in 1:length(datalist)) {
            datalist[[i]] = filldataframe(datalist[[i]], datalist[[j]])
        }
    }
    return(datalist)
}

filldataframe <- function(data, model) {
    for (colname in colnames(model)) {
        if (is.null(data[[colname]])) {
            data[[colname]] = NA
        }
    }
    return(data)
}

# Prepare a PNG file of a given font size (=cex), width and height
# After invoking this function, plot and then invoke dev.off()
prepare_png <- function(filename="out.png", cex=2, width=cex*600, height=cex*400) {
	png(filename, width=width, height=height)
	cat("\n\tPlotting to", filename, "dimensions:", width, "x", height, "cex:", cex, "\n")
	par(mar=c(3+cex, 3+cex, cex*1.5, cex))
	par(cex=cex, cex.axis=cex, cex.lab=cex, cex.main=cex, cex.sub=cex)
}

# Prepare a PDF file of a given font size (=cex), width and height
# After invoking this function, plot and then invoke dev.off()
prepare_pdf <- function(filename="out.pdf", cex=2, width=cex*10, height=cex*7) {
	pdf(filename, width=width, height=height)
	cat("\n\tPlotting to", filename, "dimensions:", width, "x", height, "cex:", cex, "\n")
	par(mar=c(3+cex, 3+cex, cex*1.5, cex))
	par(cex=cex, cex.axis=cex, cex.lab=cex, cex.main=cex, cex.sub=cex)
}

get_ymax <- function(data, metrics) {
	if (class(data) == "list") {
		ymax=data[[1]][[metrics[1]]][[1]]
		for (d in data) {
			for (metric in metrics) {
				ymax = max(ymax, d[[metric]], na.rm=TRUE)
			}
		}
	} else if (class(data) == "data.frame") {
		ymax=data[[metrics[1]]][[1]]
		for (metric in metrics) {
			ymax = max(ymax, data[[metric]], na.rm=TRUE)
		}
	} else {
		ymax = max(data[[metrics[[1]]]], na.rm=TRUE)
	}
	return(ymax)
}

get_ymin <- function(data, metrics) {
	if (class(data) == "list") {
		ymin=data[[1]][[metrics[1]]][[1]]
		for (d in data) {
			for (metric in metrics) {
				ymin = min(ymin, d[[metric]], na.rm=TRUE)
			}
		}
	} else if (class(data) == "data.frame") {
		ymin=data[[metrics[1]]][[1]]
		for (metric in metrics) {
			ymin = min(ymin, data[[metric]], na.rm=TRUE)
		}
	} else {
		ymin = min(data[[metrics[[1]]]], na.rm=TRUE)
	}
	return(ymin)
}

get_xmax <- function(data, xdata) {
	if (class(data) == "list") {
		xmax=data[[1]][[xdata]][[1]]
		for (d in data) {
			xmax = max(xmax, d[[xdata]], na.rm=TRUE)
		}
	} else if (class(data) == "data.frame") {
		xmax=data[[xdata[1]]][[1]]
		metrics = xdata
		for (metric in metrics) {
			xmax = max(xmax, data[[xdata]], na.rm=TRUE)
		}
	} else {
		xmax = max(data[[xdata[[1]]]], na.rm=TRUE)
	}
	return(xmax)
}

get_min <- function(data1, data2=NA, na.rm=TRUE, log=FALSE) {
	if (log) {
		data1 = data1[data1 > 0]
		if (any(!is.na(data2))) {
			data2 = data2[data2 > 0]
		} else {
			data2 = data1
		}
	}
	return(min(data1, data2, na.rm=na.rm))
}

get_xmin <- function(data, xdata, log=FALSE) {
	if (class(data) == "list") {
		if (log) {
			firstdata = data[[1]][[xdata]][[1]]
			firstdata = firstdata[firstdata > 0]
			if (length(firstdata) > 0) {
				xmin = min(firstdata)
			} else {
				xmin = Inf
			}
		} else {
			xmin=data[[1]][[xdata]][[1]]
		}
		for (d in data) {
			xmin = get_min(xmin, d[[xdata]], na.rm=TRUE, log=log)
		}
	} else if (class(data) == "data.frame") {
		if (log) {
			firstdata = data[[xdata[1]]][[1]]
			firstdata = firstdata[firstdata > 0]
			xmin = min(firstdata)
		} else {
			xmin=data[[xdata[1]]][[1]]
		}
		for (metric in metrics) {
			xmin = get_min(xmin, data[[xdata]], na.rm=TRUE, log=log)
		}
	} else {
		xmin = get_min(data[[xdata[[1]]]], na.rm=TRUE, log=log)
	}
	cat("\n")
	return(xmin)
}

get_datalimits <- function(data)
{
	xmin_left = NA
	xmax_left = NA
	xmin_center = NA
	xmax_center = NA
	xmin_right = NA
	xmax_right = NA

	if (is.null(data) || all(is.na(data))) {
		cat("Cannot get data limits!\n")
	}

	if (class(data) == "numeric") {
		# Data is a vector
		l = length(data)
		# first third goes until this index
		l1 = ceiling(l/3)
		# second third goes until this index
		l2 = ceiling(l/3) * 2

		xmax_left = max(data[1:l1], na.rm=T)
		xmin_left = min(data[1:l1], na.rm=T)
		xmax_center = max(data[l1:l2], na.rm=T)
		xmin_center = min(data[l1:l2], na.rm=T)
		xmax_right = max(data[l2:l], na.rm=T)
		xmin_right = min(data[l2:l], na.rm=T)
	} else if (class(data) == "matrix") {
		# Data is a matrix
		l = max(dim(data))
		l1 = ceiling(l/3)
		# second third goes until this index
		l2 = ceiling(l/3) * 2
		if (dim(data)[1] > dim(data)[2]){
			data = t(data)
		}
		xmax_left = max(data[,1:l1], na.rm=T)
		xmin_left = min(data[,1:l1], na.rm=T)
		xmax_center = max(data[,l1:l2], na.rm=T)
		xmin_center = min(data[,l1:l2], na.rm=T)
		xmax_right = max(data[,l2:l], na.rm=T)
		xmin_right = min(data[,l2:l], na.rm=T)
	}

	return(c(xmin_left, xmin_center, xmin_right, xmax_left, xmax_center, xmax_right))
}


find_empty_plotarea <- function(data = NULL, ylim = c(min(dmins), max(dmaxs)), metricslog = FALSE, dmins = c(NA, NA, NA), dmaxs = c(NA, NA, NA), fallback=TRUE, numlegends=1)
{
	# Compute data mins and maxs
	dlims = get_datalimits(data)
	if (any(is.na(dmins))) {
		dmins = dlims[1:3]
	}
	if (any(is.na(dmaxs))) {
		dmaxs = dlims[4:6]
	}
	if (all(is.na(dmins)) || all(is.na(dmaxs))) {
		return("")
	}

	if (any(is.na(ylim))) {
		ylim = c(min(data), max(data))
	}

	threshold1 = ylim[1] + (ylim[2] - ylim[1]) * 1/3
	threshold2 = ylim[1] + (ylim[2] - ylim[1]) * 2/3

	#cat("ylims:", ylim[1], ylim[2], "\n")
	#cat("Thresholds:", threshold1, threshold2, "\n")
	#cat("dmins:", dmins[1], dmins[2], dmins[3], "\n")
	#cat("dmaxs:", dmaxs[1], dmaxs[2], dmaxs[3], "\n")

	choices = c()

	# Trying to find areas where legend will definitely fit
	if (dmaxs[3] < threshold2 ) {
		choices = c(choices, "topright")
	}
	if (dmaxs[1] < threshold2) {
		choices = c(choices, "topleft")
	}
	if (dmins[3] > threshold1 ) {
		choices = c(choices, "bottomright")
	}
	if (dmins[1] > threshold1 ) {
		choices = c(choices, "bottomleft")
	}
	if (dmaxs[2] < threshold2) {
		choices = c(choices, "top")
	}
	if (dmins[2] > threshold1) {
		choices = c(choices, "bottom")
	}

	if (length(choices) < numlegends && fallback) {
		# Sort data maxima, append the corresponding position to choices
		inds = sort(dmaxs, index.return=T)$ix
		positions = c("topleft", "top", "topright")
		choices = c(choices, positions[inds])
		choices = unique(choices)
	}

	if (length(choices) >= numlegends) {
		#cat("Choices:",choices,"- choosing no.",numlegends,"\n\n")
		return(choices[numlegends])
	} else {
		#cat("Choices:",choices,"- not enough, needed" , numlegends, "\n\n")
		return("")
	}
}

get_workload <- function(label) {
    if (grepl("alexa1000", label)) {
        return("Alexa 1000")
    }
    if (grepl("alexa10k", label)) {
        return("Alexa 10001-11000")
    }
	return(label)
}

get_browser_label <- function(label) {
    if (grepl("selenium", label)) {
        return("Firefox")
    }
    if (grepl("marionette", label)) {
        return("Firefox")
    }
    if (grepl("chrome", label)) {
        return("Chrome")
    }
	return(label)
}



get_methodology_label <- function(label) {
    if (grepl("selenium", label)) {
        return("Firefox + Selenium")
    }
    if (grepl("marionette", label)) {
        return("Firefox + Marionette")
    }
    if (grepl("chrome", label)) {
        return("Chrome DevTools")
    }
	return(label)
}

plotlabel.human.readable <- function(label, exclude="") {
    if (is.null(label)) {
        return("NULL")
    }
    if (grepl("res_number_of_resources_finished_before_onload_-_har_non_failed_requests_Alexa_10001-11000", label)) {
        return("HAR - Res (Alexa 10001-11000)")
    }
    if (grepl("res_number_of_resources_finished_before_onload_-_har_non_failed_requests_Alexa_1000", label)) {
        return("HAR - Res (Alexa 1000)")
    }
	if (grepl("Firefox", label) | grepl("Chrome", label)) {
		return(label)
	}
    if (grepl("Redirect_share_of_PLT", label)) {
        return("PLT")
    }
    if (grepl("Redirect_share_of_domContentLoaded", label)) {
        return("domContentLoaded")
    }
    if (grepl("Redirect_share_of_TTFB", label)) {
        return("TTFB")
    }
    if (grepl("Redirect_share_of_firstPaint", label)) {
        return("TTFP")
    }
    if (grepl("trace_headerlen_-_har_headerlen", label)) {
        return("Trace - HAR header size")
    }
    if (grepl("har_headerlen_-_trace_headerlen", label)) {
        return("HAR - Trace header size")
    }
    if (grepl("trace_bodylen_-_har_bodylen", label)) {
        return("Trace - HAR")
    }
    if (grepl("har_bodylen_-_trace_bodylen", label)) {
        return("HAR - Trace")
    }
    if (grepl("trace_bodylen_-_har_contentlengthheader", label)) {
        return("Trace - Content-Length")
    }
    if (grepl("har_contentlengthheader_-_trace_bodylen", label)) {
        return("Content-Length - Trace")
    }
    if (grepl("trace_bodylen_-_res_bodylen", label)) {
        return("Trace - Res")
    }
    if (grepl("res_bodylen_-_trace_bodylen", label)) {
        return("Res - Trace")
    }
    if (grepl("har_requests_before_onload_-_res_number_of_resources_finished_before_onload", label)) {
        return("HAR - Resource Timings Entries")
    }
    if (grepl("res_number_of_resources_finished_before_onload_-_har_requests_before_onload", label)) {
        return("HAR - Resource Timings Entries")
    }
    if (grepl("res_number_of_resources_finished_before_onload_-_har_non_failed_requests", label)) {
        return("HAR - Resource Timings Entries")
    }
    if (grepl("har_non_failed_requests_-_res_number_of_resources_finished_before_onload", label)) {
        return("HAR (non failed) - Resource Timings Entries")
    }
    if (grepl("har_bodylen_-_har_contentlengthheader", label)) {
        return("HAR - Content-Length")
    }
    if (grepl("res_bodylen_-_har_contentlengthheader", label)) {
        return("Res - Content-Length")
    }
    if (grepl("har_contentlengthheader_-_har_bodylen", label)) {
        return("Content-Length - HAR")
    }
    if (grepl("res_bodylen_-_har_bodylen", label)) {
        return("Res - HAR")
    }
    if (grepl("har_contentlengthheader_-_res_bodylen", label)) {
        return("Content-Length - Res")
    }
    if (grepl("har_bodylen_-_res_bodylen", label)) {
        return("HAR - Res")
    }
    if (grepl("res_decoded_-_har_contentsize", label)) {
        return("Res - HAR decoded")
    }
    if (grepl("har_contentsize_-_res_decoded", label)) {
        return("HAR - Res decoded")
    }
    if (grepl("har_byte_index_bodyorcontent_-_har_byte_index_bodysize_Alexa_10001-11000", label)) {
        return("CL - HAR (Alexa 10001-11000)")
    }
    if (grepl("har_byte_index_bodyorcontent_-_har_byte_index_bodysize_Alexa_1000", label)) {
        return("CL - HAR (Alexa 1000)")
    }
    if (grepl("har_byte_index_bodyorcontent_-_har_byte_index_bodysize", label)) {
        return("Content-Length - HAR")
    }
    if (grepl("res_byte_index_-_har_byte_index_bodysize_Alexa_10001-11000", label)) {
        return("Res - HAR (Alexa 10001-11000)")
    }
    if (grepl("res_byte_index_-_har_byte_index_bodysize_Alexa_1000", label)) {
        return("Res - HAR (Alexa 1000)")
    }
    if (grepl("res_byte_index_-_har_byte_index_bodysize", label)) {
        return("Res - HAR")
    }
    if (grepl("res_byte_index_-_har_byte_index_bodyorcontent_Alexa_10001-11000", label)) {
        return("Res - CL (Alexa 10001-11000)")
    }
    if (grepl("res_byte_index_-_har_byte_index_bodyorcontent_Alexa_1000", label)) {
        return("Res - CL (Alexa 1000)")
    }
    if (grepl("res_byte_index_-_har_byte_index_bodyorcontent", label)) {
        return("Res - Content-Length")
    }
    if (grepl("res_object_index_-_har_object_index_Alexa_10001-11000", label)) {
        return("Res - HAR (Alexa 10001-11000)")
    }
    if (grepl("res_object_index_-_har_object_index_Alexa_1000", label)) {
        return("Res - HAR (Alexa 1000)")
    }
    if (grepl("res_object_index_-_har_object_index", label)) {
        return("Res - HAR")
    }
    if (grepl("byte_index_rel_diff_res_-_bodyorcontent", label)) {
        return("Res - Content-Length")
    }
    if (grepl("byte_index_rel_diff_res_-_har", label)) {
        return("Res - HAR")
    }
    if (grepl("byte_index_rel_diff_bodyorcontent_-_har", label)) {
        return("Content-Length - HAR")
    }
    if (grepl("byte_index_rel_diff_transfersize_-_bodyorcontent", label)) {
        return("HAR transfer size - Content-Length")
    }
    if (grepl("domContentLoadedEventStart", label)) {
        return("DOM Content Loaded")
    }
    if (grepl("loadEventStart", label)) {
        return("onLoad")
    }
    if (grepl("har_sum_of_bodyorcontent_-_har_sum_of_respbodysize", label)) {
        return("Content-Length - HAR")
    }
    if (grepl("har_sum_of_respbodysize_-_har_sum_of_bodyorcontent", label)) {
        return("HAR - Content-Length")
    }
    if (grepl("har_sum_of_respbodysize_-_res_sum_of_encoded", label)) {
        return("HAR - Res")
    }
    if (grepl("res_sum_of_encoded_-_har_sum_of_respbodysize", label)) {
        return("Res - HAR")
    }
    if (grepl("har_sum_of_contentsize_-_res_sum_of_decoded", label)) {
        return("HAR - Res decoded")
    }
    if (grepl("res_sum_of_decoded_-_har_sum_of_contentsize", label)) {
        return("Res - HAR decoded")
    }
    if (grepl("smart_total_page_size_-_har_sum_of_bodyorcontent", label)) {
        return("Page size - Content-Length")
    }
    if (grepl("har_sum_of_bodyorcontent_-_smart_total_page_size", label)) {
        return("Content-Length \n- Page size\n")
    }
    if (grepl("smart_total_page_size_-_har_sum_of_respbodysize", label)) {
        return("Page size - HAR")
    }
    if (grepl("har_sum_of_respbodysize_-_smart_total_page_size", label)) {
        return("HAR \n- Page size")
    }
    if (grepl("smart_total_page_size_-_res_sum_of_encoded", label)) {
        return("Page size - Res")
    }
    if (grepl("res_sum_of_encoded_-_smart_total_page_size", label)) {
        return("Res - Page size")
	} else {
        return(gsub("_", " ", label))
	}
}

fix.factors <- function(data) {
    if (class(data) == "factor") {
        return(fix.factor(data))
    } else if (class(data) == "data.frame") {
        for (i in seq(1, length(data))) {
            if (is.factor(data[[i]])) {
                data[[i]] = fix.factor(data[[i]])
            }
        }
    } else if (class(data) == "list") {
        for (i in seq(1, length(data))) {
            data[[i]] = fix.factors(data[[i]])
        }
    } else {
        str(data)
        cat("Warning: Data of class" + class(data) + "is neither dataframe nor list\n")
    }
    return(data)
}

fix.factor <- function(inputfactor) {
	return(factor(inputfactor, unique(inputfactor)))
}


check_metrics <- function(data, metrics, greater=FALSE, lower=FALSE, notequal=FALSE, allequal=FALSE, comparevalue=0, verbose=FALSE) {
    for (metric in metrics) {
        if (verbose) {
            cat("Checking", metrics, "\n")
        }
        if (class(data) == "list") {
            if (greater) {
                result = sapply(data, function(d) any(d[[metric]] > comparevalue))
            }
            if (lower) {
                result = sapply(data, function(d) any(d[[metric]] < comparevalue))
            }
            if (notequal) {
                result = sapply(data, function(d) any(d[[metric]] != comparevalue))
            }
            if (allequal) {
                cat("Checking if all", metric, "are equal\n")
                result = sapply(data, function(d) any (len(unique(d[[metric]])) > 1))
            }
        } else {
            if (greater) {
                result = any(data[[metric]] > comparevalue)
            }
            if (lower) {
                result = any(data[[metric]] < comparevalue)
            }
            if (notequal) {
                result = any(data[[metric]] != comparevalue)
            }
            if (allequal) {
                result = length(unique(data[[metric]])) > 1
            }
        }
        if (verbose) {
            cat("Result:", result, " (FALSE is good, it means that no value breaks the specified assumption)\n")
        }
        if (any(result)) {
            cat("\n!!! Non-conforming", metric, "for:\n")
            if (class(data) == "list") {
                print(names(result[result]))
            } else {
                cat(unique(levels(data$scenario)), "\n")
            }
            returnvalue = TRUE
        } else {
            returnvalue = FALSE
        }
    }
    if (verbose) {
        cat("\n")
    }
    return(returnvalue)
}

top_n <- function(data, top, n=10) {
    data = data[with(data, order(data[[top]], decreasing=T)),]
    return(head(data, n=n))
}

print_top_n <- function(data, metrics, printcolumns, ifbiggerthan=0, n=10) {
    for (metric in metrics) {
		if (any(data[[metric]] > ifbiggerthan)) {
			subsetdata = fix.factors(subset(data, data[[metric]] > ifbiggerthan))
			print(top_n(subsetdata, metric)[,c(metric, printcolumns)])
		}
    }
}

adjust_y_label <- function(ymax, ylabel) {
	if (ymax > 100000) {
		if (grepl("Bit", ylabel)) {
			ylabel=gsub("Bit","MBit",ylabel)
		} else {
			ylabel=paste(ylabel, "[M]")
		}
	} else if (ymax > 1000) {
		if (grepl("Bit", ylabel)) {
			ylabel=gsub("Bit","kBit",ylabel)
		} else {
			if (grepl("ms", ylabel)) {
				ylabel=gsub("ms","s",ylabel)
			} else {
				ylabel=paste(ylabel, " [k]")
			}
		}
    }
    return(ylabel)
}

draw_y_axis <- function(ymax, numlabels=5) {
	if (ymax > 100000) {
		yunit=10^6
	} else if (ymax > 1000) {
		yunit=10^3
	} else {
        yunit=1
    }

	labelmax = signif(ymax, 1)
	labels_at = seq(0, labelmax, length.out=numlabels)
	labels=labels_at/yunit

	axis(2, at=labels_at, labels=labels, las=1)
}

prepare_file <- function(plot = "terminal", filename="plot", cex=1, width=20, height=15, spacebelow=22) {
	if (plot == "pdf") {
		cat("Plotting pdf to", paste(filename, ".pdf", sep=""), "\n")
		prepare_pdf(paste(filename, ".pdf", sep=""), width=width, height=height, cex=cex)
		par(mar=c(spacebelow,5,2,1))
		if (cex == 1) {
			cex=1.5
		}
	} else if (plot == "eps") {
		cat("Plotting eps to", paste(filename, ".eps", sep=""), "\n")
		setEPS()
		postscript(paste(filename, ".eps", sep=""), height=height/3, width=width/3)
		par(mar=c(spacebelow,3,0.1,0.5))
		cex=1.5
    } else if (plot=="png") {
        # If font size "1" is given, set to 2, otherwise too small in PNG
        if (cex == 1) {
            cex=2
        }
        # Set PNG size based on given font size
        prepare_png(filename=paste(filename, ".png", sep=""), cex=cex, width=cex*600, height=cex*1000)
	} else {
		cat("Plotting to terminal\n")
		par(mar=c(spacebelow,4,2,1))
	}
}

boxplotmetrics <- function(data, metrics="actual_time", filename="boxplot", splitby=c("policy", "workload"), filterscenarios=c(), cex=1, spacebelow=22, mainlabel="", plot="terminal", ylabel="", yaxisincludezero=FALSE, can_omit_plotlabels=FALSE, log="", exclude="") {
    prepare_file(plot=plot, filename=filename, cex=cex, spacebelow=spacebelow)
    if (length(filterscenarios) > 0) {
        data = filter_scenarios(data, filterscenarios, split=splitby)
    }

	if (class(data) == "list") {
        data = do.call(rbind, data)
    }
    if (all(is.na(data[[metrics]]))) {
        cat("All data is NA -- cannot plot.\n")
        return()
    }
    splitfactors = data[[splitby[1]]]
    factor1length = length(levels(splitfactors))
    additionalsplitfactor = 1

    if (length(splitby) > 1) {
        for (i in seq(2, length(splitby))) {
            splitfactors = data[[splitby[i]]]:splitfactors
            additionalsplitfactor = additionalsplitfactor * length(levels(data[[splitby[i]]]))
        }
    }

	plotlabels=sapply(levels(splitfactors), function(x) plotlabel.human.readable(x, exclude=exclude))
	cat("Generated", length(plotlabels), "plot labels of maximum length", max(nchar(plotlabels)), ", spacebelow =", spacebelow, "\n")

	# If plot labels are too long and also multiline plotlabels will not fit
	if (max(nchar(plotlabels)) > 2*spacebelow && length(plotlabels) > 50 && can_omit_plotlabels) {
		factorlevels = sapply(splitby, function(x) length(levels(data[[x]])))
		excludefactor = splitby[which.min(factorlevels)]
		if (excludefactor == splitby[1]) {
			# Do not exclude first factor, it's probably too important
			excludefactor = splitby[2]
		}
		cat("These plot labels are too long. Trying to omit factor", excludefactor, "in the labels\n")
		plotlabels=sapply(levels(splitfactors), function(x) plotlabel.human.readable(x, exclude=excludefactor))
	}

	n = (factor1length + 1)*additionalsplitfactor
	xat = rep( c( rep(1, factor1length), 0), additionalsplitfactor) * 1:n
	xat = xat[xat>0]

	yaxt="s"

    ymax = max(data[[metrics]], na.rm=TRUE)
	ylim = c(min(data[[metrics]], na.rm=TRUE), ymax)
    if (yaxisincludezero && ylim[1] > 0) {
        ylim[1]=0
    }

    if (ylabel == "") {
        ylabel=paste(gsub("_", " ", metrics))
    }
	if (ymax > 10000) {
		yaxt="n"
        ylabel = adjust_y_label(ymax, ylabel)
        if (ymax > MAX_VALUE) {
            cat("Warning: ymax is unrealistically high:", ymax, "\nSetting max value to", MAX_VALUE, "\n")
            data[[metrics]][data[[metrics]] > MAX_VALUE] = 0
            ymax = max(data[[metrics]], na.rm=TRUE)
            ylim[2] = ymax
        }
	}

	boxplot(data[[metrics]] ~ splitfactors, at=xat, ylab=ylabel, yaxt=yaxt, ylim=ylim, xlab="", names=plotlabels, main=mainlabel, cex.lab=cex, cex.main=cex, cex.axis=cex, outcex=cex, las=2, log=log)

    if (yaxt == "n") {
        draw_y_axis(ymax)
    }

	if (plot == "pdf" | plot == "eps") {
		dev.off()
	}
}

summarizedata <- function(data, metrics, index="", onlynonzero=F, filterscenarios=c()) {
    if (length(filterscenarios) > 0) {
        data = filter_scenarios(data, filterscenarios)
    }
    for (metric in metrics) {
        cat("Summary of", metric)
        if (index != "") {
            cat(" indexed by", index, ":\n")
        } else {
            cat("\n")
        }

        if (class(data) == "data.frame") {
            if (!is.null(data[[index]])) {
                data = split(data, index)
            } else {
                data = list(data)
            }
        }
        if (class(data) == "list") {

            for (i in seq(1, length(data))) {
                dataitem = data[[i]]
                if (onlynonzero) {
                    if (all(dataitem[[metric]] == 0)) {
                        next
                    }
                }
                if (length(dataitem[[metric]]) == length(dataitem[[index]])) {
                    cat(metric, "for", plotlabel.human.readable(names(data)[i]), "\n")
                    summarylist = tapply(X=dataitem[[metric]], IND=fix.factors(dataitem[[index]]), FUN=summary);
                    print(summarylist[!sapply(summarylist, is.null)])
                } else {
                    if (index == "") {
                        print(summary(dataitem[[metric]]))
                    } else {
                        cat("Error: Metric", metric, "of length", length(dataitem[[metric]]), "but", index, "of length", length(dataitem[[index]]), "\n")
                    }
                }
            }
        }
        cat("\n")
    }
}


plot.cdf <- function(data, subsetdata=F, xlim=c(min(data), max(data)), xlabel="data", color="black", pch=15, cex=1, log="", ccdf=F, ylim=c(0,1), mainlabel="", xaxt="s") {
	data.ecdf=ecdf(data)
	data.knots=knots(data.ecdf)
	data.sel=round(seq(1, length(data.knots), length=10))
	data.sel2=round(seq(1, length(data.knots), length=10000))
	if (subsetdata) {
		data.plot=data.knots[data.sel2]
	} else {
		data.plot = data.knots
	}

	if (grepl("y",log) && ylim[1] == 0) {
		ylim[1] = min(data.ecdf(data.plot))
	}
	if (grepl("x", log) && xlim[1] <= 0) {
		xlim[1] = min(data.plot[data.plot > 0])
	}

	if (!ccdf) {
		plot(data.plot, data.ecdf(data.plot), log=log, xlim=xlim, type="l", col=color, ylim=ylim, main=NA, ann=FALSE, cex.axis=cex, xaxt=xaxt)
	} else {
		plot(sort(data.plot), 1-data.ecdf(sort(data.plot)), log=log, xlim=xlim, type="l", col=color, ylim=ylim, main=NA, ann=FALSE, cex.axis=cex, xaxt=xaxt)
	}
	if (xaxt == "n") {
		# Plot x axis
		axis(1, at = 10^seq(1, xlim[2]))
	}

	abline(h = c(0, 1), col = "gray45", lty = 2)
	#axis(1, at=c(0.5, 0.75, 1, 1.25, 1.5, 1.75, 2), labels=c("0.5", "0.75", "1", "1.25", "1.5", "1.75", "2"))

	line=2
	if (cex > 1) {
		line = cex+1
	}
	mtext(side=1, text=xlabel, line=line, cex=cex)
	mtext(side=2, text=ifelse(ccdf,"CCDF","ECDF"), line=line, cex=cex)
	if (mainlabel != "") {
		mtext(side=3, text=mainlabel, line=1, cex=cex)
	}
	if (!ccdf) {
		points(data.knots[data.sel], data.ecdf(data.knots[data.sel]), col=color, pch=pch)
	} else {
		points(data.knots[data.sel], 1-data.ecdf(data.knots[data.sel]), col=color, pch=pch)
	}
}

add.cdf <- function(data, subsetdata=F, color="gray45", pch=14, ccdf=F) {
	if (all(is.na(data))) {
		cat("Data is NA -- not plotting\n")
		return()
	}
	data.ecdf=ecdf(data)
	data.knots = knots(data.ecdf)
	data.sel = round(seq(1, length(data.knots), length=10))

	if (subsetdata) {
		data.sel2 = round(seq(1, length(data.knots), length=10000))
		data.plot = data.knots[data.sel2]
	} else {
		data.plot = data.knots
	}
	#data.sel = round(exp(seq(log(min(data.knots)), log(max(data.knots)), length=10)))
	if (!ccdf) {
		lines(data.plot, data.ecdf(data.plot), col=color)
		points(data.knots[data.sel], data.ecdf(data.knots[data.sel]), pch=pch, col=color)
	} else {
		lines(sort(data.plot), 1-data.ecdf(sort(data.plot)), col=color)
		points(data.knots[data.sel], 1-data.ecdf(data.knots[data.sel]), pch=pch, col=color)
	}
}

plot.cdf.list <- function(data, metrics="d", xlim=NULL, cex=1, log="", ccdf=F, xlabel="data", mainlabel="", subsetdata=F, legendposition="topleft") {
	colors=c("red", "darkorchid3", "cadetblue", "blue", "darkolivegreen4", "gray45", "black", "darkgoldenrod", "brown")
	pointtypes=c(4, 8, 18, 17, 16, 15, 14, 9, 12)
    if (is.null(xlim)) {
		if (!grepl("x", log)) {
			xlim = c(get_xmin(data, metrics), get_xmax(data, metrics))
		} else {
			xlim = c(get_xmin(data, metrics, log=T), get_xmax(data, metrics))
		}
    }
	xaxt="s"
	if (grepl("x", log)) {
		xaxt = "n"
	}
    plot.cdf(data[[1]][[metrics]], log=log, ccdf=ccdf, xlim=xlim, color=colors[1], pch=pointtypes[1], xlabel=xlabel, mainlabel=mainlabel, xaxt=xaxt, subsetdata=subsetdata)
    if (length(data) > 1) {
        for (i in seq(2, length(data))) {
            add.cdf(data[[i]][[metrics]], color=colors[i], pch=pointtypes[i], ccdf=ccdf, subsetdata=subsetdata)
        }
    }
	plotlabels=sapply(names(data), function(x) plotlabel.human.readable(x))

	legend(legendposition, legend=plotlabels, col=colors, pch=pointtypes, bty="n", cex=cex)
}

# Takes a list (e.g. of data frames), returns a matrix of its quantiles
compute.quantiles <- function(data, quantiles=c(0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95))
{
	q = sapply(data, function(x) quantile(x, probs=quantiles))
	q.matr = matrix(q, nrow=length(quantiles))
	rownames(q.matr)=quantiles
	colnames(q.matr)=names(data)
	return(q.matr)
}

# In a data set, compare a set of metrics with all other metrics in the set (by calculating their numeric difference)
# and put the result in the data set.
# Also return a list of (clumsy) labels for these differences
compute_compare_metrics <- function(data, orig_metrics, compare_metrics=orig_metrics[1:length(orig_metrics)], print=F, abs=F, exclude_lower_zero=F) {
    all_comparisons = c()
    if (print) {
		cat("\nOrig_metrics:", paste(orig_metrics), ", length:", length(orig_metrics), "\n")
    }
	baseline_metrics = orig_metrics
	if (abs) {
		baseline_metrics = baseline_metrics[1:(length(baseline_metrics)-1)]
	}
	for (i in seq(1, length(baseline_metrics))) {
		baseline = baseline_metrics[i]
		if (print) {
			cat("\ti =", i, "Baseline at index i: ", baseline, "\n")
		}
		if (abs) {
			compare_metrics = orig_metrics[(i+1):(length(orig_metrics))]
		} else {
			compare_metrics = orig_metrics
		}
		if (print) {
			cat("Compare_metrics from orig[i+1] to orig[len]:", paste(compare_metrics), "\n")
		}
		for (metric in compare_metrics) {
			if (print) {
				cat("Metric: ", metric, "\n")
			}
			if (is.na(metric)) {
				if (print) {
					cat("NA -- next\n")
				}
				next
			}
			if (metric == baseline) {
				if (print) {
					cat("Equal -- next!\n")
				}
				next
			}
			this_minus_that = paste(metric, "-", baseline, sep="_")
			all_comparisons = c(all_comparisons, this_minus_that)
			data[[this_minus_that]] = data[[metric]] - data[[baseline]]
			if (abs) {
				data[[this_minus_that]] = abs(data[[this_minus_that]])
			}
			if (exclude_lower_zero) {
				data[[this_minus_that]] = ifelse(data[[baseline]] < 0 | data[[metric]] < 0, NA, data[[this_minus_that]])
			}
		}
		if (print) {
			cat("\n")
		}
	}
	if (print) {
		cat("All comparisons done: ", paste(all_comparisons), "\n")
	}
	return(list(data = data, all_comparisons = all_comparisons))
}

# From dataset, compute a new data frame of differences that is easier to use for plotting
# The new data frame has the following columns:
# comparison: 	which two metrics are compared (may be the clumsy label computed by compute_compare_metrics)
# datadiff:   	the numeric difference of the two metrics in this particular case
# page:			which page was loaded in this case
# run:			which run this is
compute_comparison_dataframe <- function(data, all_comparisons, splitby=NA) {
	comparisondata = list()
	if (!is.na(splitby)) {
		splitdata = split(data, data[[splitby]])
	}
	for (comparison in all_comparisons) {
		if (!is.na(splitby)) {
			for (i in seq(1, length(splitdata))) {
				dataitem = splitdata[[i]]
				splitname = gsub(" ", "_", names(splitdata)[i])
				comparisonlabel = paste(comparison, splitname, sep="_")

				newdata = data.frame(comparison=comparisonlabel, datadiff=dataitem[[comparison]], page=dataitem$page, run=dataitem$run)
				comparisondata = c(comparisondata, list(newdata))
			}
		} else {
			newdata = data.frame(comparison=as.character(comparison), datadiff=data[[comparison]], page=data$page, run=data$run)
			comparisondata = c(comparisondata, list(newdata))
		}
	}
	return(do.call(rbind, comparisondata))
}

get_percentage <- function(data, metrics, min=NA, max = NA, eq=NA, print=F) {
	data = data[!is.na(data[[metrics]]),]
	datalength = nrow(data)
	if (!is.na(min)) {
		data = subset(data, data[[metrics]] > min)
	}
	if (!is.na(max)) {
		data = subset(data, data[[metrics]] < max)
	}
	if (!is.na(eq)) {
		data = subset(data, data[[metrics]] == eq)
	}
	if (print) {
		cat("Got", nrow(data), "/", datalength, "items =", nrow(data) / datalength * 100, "%\n")
	}
	return(nrow(data) / datalength * 100)
}

print_comparison_summary <- function(data, metrics) {
	if (all(is.na(data[[metrics]]))) {
		cat("All NA!\n")
		return()
	}
	lowerthan0 = get_percentage(data, metrics, max = 0)
	equalto0 = get_percentage(data, metrics, eq = 0)
	above0 = get_percentage(data, metrics, min = 0)
	cat(metrics, "\n")
	cat("is not NA:\t", round(nrow(data[!is.na(data[[metrics]]),]) / nrow(data) * 100, digits=2), "% of samples\n")
	cat("\tmatches:\t", round(equalto0, digits=2), "% of cases (in which it is not NA)\n")
	cat("\tmedian diff:\t", round(median(data[[metrics]], na.rm=T), digits=2), "\n")
	cat("\tquantiles:\t", round(lowerthan0, digits=2), "(<0)")
	cat("\t", round(lowerthan0, digits=2), "..", round(lowerthan0 + equalto0, digits=2), "(==0)")
	cat("\t", round(100 - above0, digits=2), "(>0)\n")
	if (any(data[[metrics]] != 0)) {
		cat("\tmin:\t\t", min(data[[metrics]], na.rm=T), "\n")
		cat("\tquantiles:\n")
		if (lowerthan0 > 10) {
			cat("\t\t10th:\t", round(quantile(data[[metrics]], 0.1, na.rm=T), digits=2), "\n")
		}
		if (above0 > 10) {
			cat("\t\t90th:\t", round(quantile(data[[metrics]], 0.9, na.rm=T), digits=2), "\n")
		}
		if (above0 > 1) {
			cat("\t\t99th:\t", round(quantile(data[[metrics]], 0.99, na.rm=T), digits=2), "\n")
		}
		if (above0 > 0.1) {
			cat("\t\t99.9th:\t", round(quantile(data[[metrics]], 0.999, na.rm=T), digits=2), "\n")
		}
		cat("\tmax:\t\t", max(data[[metrics]], na.rm=T), "\n")
	}
	cat("\n")
}

put_metrics_in_dataframe <- function(data, metrics) {
	data_list = list()
	for (m in metrics) {
		newdata = data.frame(metrics = as.character(m), value=data[[m]], page=data$page, run=data$run)
		data_list = c(data_list, list(newdata))
	}
	data_df = do.call(rbind, data_list)
	return(data_df)
}
