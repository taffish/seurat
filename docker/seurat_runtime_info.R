#!/usr/bin/env Rscript

args <- commandArgs(trailingOnly = TRUE)

if (any(args %in% c("-h", "--help"))) {
  cat("seurat-runtime-info 5.5.0-r1\n")
  cat("\n")
  cat("Print bundled R, Seurat, SeuratObject, and selected runtime package versions.\n")
  cat("\n")
  cat("Usage:\n")
  cat("  seurat-runtime-info [--help] [--version]\n")
  quit(status = 0)
}

if (any(args %in% c("-v", "--version"))) {
  cat("seurat-runtime-info 5.5.0-r1\n")
  quit(status = 0)
}

pkg_version <- function(pkg) {
  if (requireNamespace(pkg, quietly = TRUE)) {
    as.character(utils::packageVersion(pkg))
  } else {
    "MISSING"
  }
}

rows <- data.frame(
  component = c(
    "R",
    "Seurat",
    "SeuratObject",
    "Matrix",
    "ggplot2",
    "patchwork",
    "future",
    "sctransform",
    "uwot",
    "RANN",
    "RcppAnnoy",
    "RcppHNSW",
    "RSpectra",
    "hdf5r",
    "BPCells",
    "glmGamPoi",
    "MAST",
    "SingleCellExperiment",
    "harmony",
    "leidenbase",
    "Signac",
    "Azimuth",
    "SeuratData"
  ),
  version = c(
    as.character(getRversion()),
    pkg_version("Seurat"),
    pkg_version("SeuratObject"),
    pkg_version("Matrix"),
    pkg_version("ggplot2"),
    pkg_version("patchwork"),
    pkg_version("future"),
    pkg_version("sctransform"),
    pkg_version("uwot"),
    pkg_version("RANN"),
    pkg_version("RcppAnnoy"),
    pkg_version("RcppHNSW"),
    pkg_version("RSpectra"),
    pkg_version("hdf5r"),
    pkg_version("BPCells"),
    pkg_version("glmGamPoi"),
    pkg_version("MAST"),
    pkg_version("SingleCellExperiment"),
    pkg_version("harmony"),
    pkg_version("leidenbase"),
    pkg_version("Signac"),
    pkg_version("Azimuth"),
    pkg_version("SeuratData")
  )
)

utils::write.table(rows, file = stdout(), sep = "\t", row.names = FALSE, quote = FALSE)
