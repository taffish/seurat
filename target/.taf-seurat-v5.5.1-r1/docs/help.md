seurat 5.5.1-r1

TAFFISH wrapper for Seurat 5.5.1, the Satija Lab R toolkit for single-cell
analysis. This app provides a general Seurat R runtime. It is not the future
TAFFISH scrnaseq-r flow-facing helper toolkit.

TAFFISH wrapper usage:
  taf-seurat --help
  taf-seurat --version
  taf-seurat -- --version
  taf-seurat Rscript --version
  taf-seurat Rscript analysis.R
  taf-seurat seurat-runtime-info

Default command:
  Rscript

Helper commands:
  seurat-runtime-info
      Print bundled R, Seurat, SeuratObject, and selected runtime package
      versions as TSV.

Examples:
  taf-seurat seurat-runtime-info

  taf-seurat Rscript analysis.R

  taf-seurat Rscript -e 'library(Seurat); packageVersion("Seurat")'

  taf-seurat Rscript - <<'RS'
  suppressPackageStartupMessages(library(Seurat))
  counts <- matrix(c(1, 0, 3, 0, 2, 1, 5, 0, 0), nrow = 3)
  rownames(counts) <- c("GeneA", "GeneB", "MT-GeneC")
  colnames(counts) <- c("cell1", "cell2", "cell3")
  obj <- CreateSeuratObject(counts = counts)
  obj[["percent.mt"]] <- PercentageFeatureSet(obj, pattern = "^MT-")
  saveRDS(obj, "tiny.seurat.rds")
  RS

Included runtime:
  R 4.5.2
  Seurat 5.5.1
  SeuratObject 5.4.0
  Matrix, ggplot2, patchwork, future, sctransform, uwot, RANN, RcppAnnoy,
  RcppHNSW, RSpectra, hdf5r, BPCells, glmGamPoi, MAST,
  SingleCellExperiment, harmony, leidenbase, SeuratData, and their
  dependencies.

  The image copies the official Satija Lab Seurat 5.5.1 R package library into
  a smaller rocker/r-ver 4.5.2 command-line runtime. It does not include
  RStudio Server.

Not included in r1:
  Signac
  Azimuth
  SeuratData datasets
  Cell Ranger
  genome references
  prebuilt reference atlases
  TAFFISH scrnaseq-r helper commands

Platform boundary:
  The upstream Satija Lab package source and this TAFFISH image are
  linux/amd64. This app declares Docker and Podman --platform linux/amd64 so
  arm64 hosts can run it through amd64 emulation. This is not native
  linux/arm64 support.

Inputs and outputs:
  Seurat is an R API, not a fixed CLI. Your R script controls inputs and
  outputs. Typical inputs include 10x matrix directories, HDF5 matrices, text
  matrices, and RDS objects. Typical outputs include Seurat RDS objects, marker
  tables, metadata tables, and static plots.

Boundaries:
  r1 preserves the general upstream Seurat runtime. It does not implement
  TAFFISH flow-facing import/qc/filter/analysis/marker helper commands; those
  belong in a future taf-scrnaseq-r app.

  SeuratData is available as an R package in the official Satija Lab 5.5.1
  package set, but datasets are not bundled. This app does not download
  references, atlases, models, SeuratData datasets, or Azimuth references
  during normal use or smoke. It does not replace manual biological
  interpretation.

Citation:
  Hao et al. Dictionary learning for integrative, multimodal and scalable
  single-cell analysis. Nature Biotechnology (2023). DOI:
  10.1038/s41587-023-01767-y.
