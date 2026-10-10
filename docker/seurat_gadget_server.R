# Configure upstream Shiny entry points without replacing Seurat algorithms or UI.
local({
  script <- Sys.getenv("SEURAT_GADGET_SCRIPT")
  host <- Sys.getenv("SEURAT_GADGET_BIND")
  port <- suppressWarnings(as.integer(Sys.getenv("SEURAT_GADGET_PORT")))
  started <- Sys.getenv("SEURAT_GADGET_STARTED")
  stopifnot(file.exists(script), host %in% c("127.0.0.1", "0.0.0.0"),
            length(port) == 1L, !is.na(port), port > 0L, port < 65536L,
            nzchar(started), dir.exists(dirname(started)))

# paneViewer uses options(viewer); plain runApp uses shiny.launch.browser.
# The callback only records successful listener creation, never opens a browser.
  record_started <- function(url, ...) {
    temporary <- paste0(started, ".tmp")
    writeLines(url, temporary, useBytes = TRUE)
    if (!file.rename(temporary, started)) stop("Could not record Shiny listener readiness")
    invisible(NULL)
  }
  options(shiny.host = host, shiny.port = port, viewer = record_started,
          shiny.launch.browser = record_started,
          shinygadgets.showdialog = function(name, url, ...) record_started(url))

# The site profile (including prepared-resource discovery) remains active.
# Do not chdir: script-relative input/output behavior stays explicitly controlled
# by the user's working directory and script. Temporary Shiny state uses TMPDIR.
  source(script, local = .GlobalEnv, chdir = FALSE, echo = FALSE)
})
