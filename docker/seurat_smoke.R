#!/usr/bin/env Rscript

args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 1) {
  stop("usage: seurat_smoke.R OUTDIR", call. = FALSE)
}

outdir <- args[[1]]
if (file.exists(outdir)) {
  stop("OUTDIR already exists; choose a new output directory", call. = FALSE)
}
if (!dir.create(outdir, recursive = TRUE, mode = "0700")) {
  stop("cannot create OUTDIR", call. = FALSE)
}
dir.create(file.path(outdir, "plots"), mode = "0700")

suppressPackageStartupMessages({
  library(Seurat)
  library(ggplot2)
  library(Matrix)
})

setThreads(1L, verbose = FALSE)
future::plan(future::sequential)

set.seed(550)

genes <- c(paste0("MT-Gene", sprintf("%02d", 1:3)), paste0("Gene", sprintf("%02d", 1:57)))
cells <- paste0("cell", sprintf("%03d", 1:45))
groups <- rep(c("type_a", "type_b", "type_c"), each = 15)

counts <- matrix(
  stats::rpois(length(genes) * length(cells), lambda = 1),
  nrow = length(genes),
  ncol = length(cells),
  dimnames = list(genes, cells)
)

marker_blocks <- list(
  type_a = paste0("Gene", sprintf("%02d", 1:6)),
  type_b = paste0("Gene", sprintf("%02d", 7:12)),
  type_c = paste0("Gene", sprintf("%02d", 13:18))
)

for (group in names(marker_blocks)) {
  idx <- which(groups == group)
  counts[marker_blocks[[group]], idx] <- counts[marker_blocks[[group]], idx] +
    matrix(stats::rpois(length(marker_blocks[[group]]) * length(idx), lambda = 5),
           nrow = length(marker_blocks[[group]]))
}

counts <- Matrix::Matrix(counts, sparse = TRUE)
obj <- CreateSeuratObject(counts = counts, project = "TAF_SEURAT_SMOKE", min.cells = 0, min.features = 0)
obj$synthetic_group <- groups
obj[["percent.mt"]] <- PercentageFeatureSet(obj, pattern = "^MT-")

obj <- NormalizeData(obj, verbose = FALSE)
obj <- FindVariableFeatures(obj, selection.method = "vst", nfeatures = 30, verbose = FALSE)
obj <- ScaleData(obj, verbose = FALSE)
obj <- RunPCA(obj, npcs = 10, verbose = FALSE)
obj <- FindNeighbors(obj, dims = 1:10, verbose = FALSE)
obj <- FindClusters(obj, resolution = 0.6, verbose = FALSE)
obj <- suppressWarnings(suppressMessages(
  RunUMAP(
    obj,
    dims = 1:10,
    n.neighbors = 10,
    min.dist = 0.25,
    umap.method = "uwot",
    metric = "cosine",
    seed.use = 550,
    verbose = FALSE
  )
))

umap <- Embeddings(obj, reduction = "umap")
stopifnot(identical(dim(umap), c(length(cells), 2L)), all(is.finite(umap)))
stopifnot(nrow(Embeddings(obj, reduction = "pca")) == length(cells),
          all(is.finite(Embeddings(obj, reduction = "pca"))),
          length(Idents(obj)) == length(cells), !anyNA(Idents(obj)))
clusters <- data.frame(
  cell = colnames(obj),
  synthetic_group = obj$synthetic_group,
  seurat_cluster = as.character(Idents(obj)),
  UMAP_1 = umap[, 1],
  UMAP_2 = umap[, 2],
  row.names = NULL
)
utils::write.table(clusters, file.path(outdir, "clusters.tsv"), sep = "\t", row.names = FALSE, quote = FALSE)

Idents(obj) <- obj$synthetic_group
markers <- FindAllMarkers(obj, only.pos = TRUE, min.pct = 0.1, logfc.threshold = 0.1, verbose = FALSE)
if (nrow(markers) == 0) {
  stop("marker table is empty", call. = FALSE)
}
utils::write.table(markers, file.path(outdir, "markers.tsv"), sep = "\t", row.names = FALSE, quote = FALSE)

saveRDS(obj, file.path(outdir, "seurat_smoke.rds"))
roundtrip <- readRDS(file.path(outdir, "seurat_smoke.rds"))
stopifnot(inherits(roundtrip, "Seurat"), identical(dim(roundtrip), dim(obj)))

versions <- data.frame(
  component = c("R", "Seurat", "SeuratObject"),
  version = c(
    as.character(getRversion()),
    as.character(utils::packageVersion("Seurat")),
    as.character(utils::packageVersion("SeuratObject"))
  )
)
utils::write.table(versions, file.path(outdir, "versions.tsv"), sep = "\t", row.names = FALSE, quote = FALSE)

p_umap <- DimPlot(obj, reduction = "umap", group.by = "synthetic_group") +
  ggtitle("TAFFISH Seurat smoke UMAP")
ggsave(file.path(outdir, "plots", "umap.png"), p_umap, width = 5, height = 4, dpi = 150)
ggsave(file.path(outdir, "plots", "umap.pdf"), p_umap, width = 5, height = 4)

p_qc <- VlnPlot(obj, features = c("nFeature_RNA", "nCount_RNA", "percent.mt"), pt.size = 0, ncol = 3)
ggsave(file.path(outdir, "plots", "qc_violin.png"), p_qc, width = 8, height = 3.5, dpi = 150)
ggsave(file.path(outdir, "plots", "qc_violin.pdf"), p_qc, width = 8, height = 3.5)

outputs <- c("seurat_smoke.rds", "markers.tsv", "clusters.tsv", "versions.tsv",
             "plots/umap.png", "plots/umap.pdf", "plots/qc_violin.png", "plots/qc_violin.pdf")
stopifnot(all(file.info(file.path(outdir, outputs))$size > 0L))

cat("seurat smoke ok\n")
