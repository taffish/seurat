#!/usr/bin/env Rscript
# 各 mode 独立生成 fixture；临时根及诊断回放由 seurat-check 管理。
args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 2L) stop("usage: seurat_checks.R MODE PRIVATE_ROOT", call. = FALSE)
mode <- args[[1]]
root <- normalizePath(args[[2]], mustWork = TRUE)
check <- function(ok, message) if (!isTRUE(ok)) stop(message, call. = FALSE)
same_shape <- function(object, expected) {
  actual <- dim(object)
  length(actual) == length(expected) && all(actual == expected)
}

identity <- function() {
  check(as.character(getRversion()) == "4.5.2", "unexpected R version")
  versions <- c(Seurat = "5.6.0", SeuratObject = "5.4.0", uwot = "0.2.4", RcppThread = "2.4.0")
  for (pkg in names(versions)) {
    check(as.character(utils::packageVersion(pkg)) == versions[[pkg]], paste("unexpected version:", pkg))
  }
}

load_seurat <- function() {
  suppressPackageStartupMessages(library(Seurat))
  Seurat::setThreads(1L, verbose = FALSE)
  future::plan(future::sequential)
}

fixture <- function(ngenes = 160L, ncells = 60L) {
  set.seed(560)
  means <- rep(seq(0.5, 8, length.out = ngenes), ncells)
  depth <- rep(rep(c(0.7, 1, 1.5), length.out = ncells), each = ngenes)
  x <- matrix(stats::rnbinom(ngenes * ncells, mu = means * depth, size = 2), nrow = ngenes,
              dimnames = list(paste0("Gene", seq_len(ngenes)), paste0("Cell", seq_len(ncells))))
  Matrix::Matrix(x, sparse = TRUE)
}

must_fail <- function(expr, pattern) {
  failure <- tryCatch({ force(expr); NULL }, error = function(e) e)
  check(inherits(failure, "error"), "negative check unexpectedly succeeded")
  check(grepl(pattern, conditionMessage(failure), ignore.case = TRUE),
        paste("unexpected negative error:", conditionMessage(failure)))
}

if (mode == "identity") {
  identity()
  v <- system2("seurat-runtime-info", "--version", stdout = TRUE, stderr = TRUE)
  check(is.null(attr(v, "status")) && identical(v, "seurat-runtime-info 5.6.0-r1"), "runtime helper version failed")
} else if (mode == "modules") {
  packages <- c("Seurat", "SeuratObject", "Matrix", "ggplot2", "patchwork", "future", "sctransform",
                "uwot", "RANN", "RcppAnnoy", "RcppHNSW", "RcppThread", "RcppEigen", "RcppProgress",
                "RSpectra", "hdf5r", "BPCells", "glmGamPoi", "MAST", "SingleCellExperiment",
                "harmony", "leidenbase", "SeuratData", "shiny", "miniUI", "plotly", "RcppParallel", "tcltk")
  missing <- packages[!vapply(packages, requireNamespace, logical(1), quietly = TRUE)]
  check(!length(missing), paste("missing/import-failed packages:", paste(missing, collapse = ", ")))
  check(as.character(utils::packageVersion("SeuratData")) == "0.2.2.9002", "unexpected SeuratData version")
} else if (mode == "buildtime") {
  identity()
  load_seurat()
  x <- matrix(c(1, 0, 3, 0, 2, 1, 5, 0, 2, 1, 1, 3), nrow = 3L,
              dimnames = list(c("A", "B", "C"), c("a", "b", "c", "d")))
  obj <- NormalizeData(CreateSeuratObject(counts = x), verbose = FALSE)
  check(same_shape(obj, c(3L, 4L)), "tiny object dimensions failed")
  check(all(is.finite(as.matrix(LayerData(obj, layer = "data")))), "tiny normalize failed")
} else if (mode == "threading") {
  load_seurat()
  x <- fixture()
  setThreads(1L, verbose = FALSE)
  a <- NormalizeData(CreateSeuratObject(counts = x), verbose = FALSE)
  setThreads(2L, verbose = FALSE)
  check(getThreads(verbose = FALSE) == 2L, "setThreads/getThreads failed")
  b <- NormalizeData(CreateSeuratObject(counts = x), verbose = FALSE)
  check(isTRUE(all.equal(as.matrix(LayerData(a, layer = "data")),
                         as.matrix(LayerData(b, layer = "data")), tolerance = 1e-7)),
        "threaded normalization differs beyond tolerance")
  b <- FindVariableFeatures(b, nfeatures = 30L, verbose = FALSE)
  b <- ScaleData(b, verbose = FALSE)
  # 5.6.0 RunPCA 会静默回退 irlba；单独探测固定版本的新内核，防止误称覆盖。
  kernel <- getFromNamespace("EigenGramPCA", "Seurat")
  gram <- kernel(as.matrix(LayerData(b, layer = "scale.data")), npcs = 6L,
                 weight_by_var = TRUE, nthreads = 2L)
  check(same_shape(gram$embeddings, c(ncol(x), 6L)) && all(is.finite(gram$embeddings)),
        "new Gram PCA kernel invalid")
  b <- RunPCA(b, npcs = 6L, verbose = FALSE)
  p <- Embeddings(b, "pca")
  check(same_shape(p, c(ncol(x), 6L)) && all(is.finite(p)), "threaded PCA shape/finite check failed")
  setThreads(1L, verbose = FALSE)
  check(getThreads(verbose = FALSE) == 1L, "thread reset failed")
} else if (mode == "sct") {
  load_seurat()
  obj <- CreateSeuratObject(counts = fixture(300L, 90L))
  setThreads(2L, verbose = FALSE)
  obj <- SCTransform(obj, ncells = 90L, variable.features.n = 60L, vst.flavor = "v2", verbose = FALSE)
  check("SCT" %in% Assays(obj), "SCT assay missing")
  residuals <- LayerData(obj, assay = "SCT", layer = "scale.data")
  check(nrow(residuals) > 0L && ncol(residuals) == 90L && all(is.finite(residuals)), "SCT residuals invalid")
  check(length(obj[["SCT"]]@SCTModel.list) > 0L, "SCT model missing")
  obj <- RunPCA(obj, assay = "SCT", npcs = 5L, verbose = FALSE)
  check(same_shape(Embeddings(obj, "pca"), c(90L, 5L)) && all(is.finite(Embeddings(obj, "pca"))),
        "SCT PCA invalid")
  saveRDS(obj, file.path(root, "sct.rds"))
  check(inherits(readRDS(file.path(root, "sct.rds")), "Seurat"), "SCT RDS round trip failed")
} else if (mode == "bpcells") {
  load_seurat()
  x <- fixture()
  bpdir <- file.path(root, "bpcells-counts")
  BPCells::write_matrix_dir(mat = x, dir = bpdir)
  disk <- BPCells::open_matrix_dir(bpdir)
  check(inherits(disk, "IterableMatrix") && same_shape(disk, dim(x)), "BPCells reopen failed")
  check(isTRUE(all.equal(as.matrix(disk), as.matrix(x), tolerance = 1e-12)), "BPCells count round trip failed")
  obj <- CreateSeuratObject(counts = disk)
  obj <- NormalizeData(obj, verbose = FALSE)
  check(inherits(LayerData(obj, layer = "data"), "IterableMatrix"), "BPCells normalization unexpectedly densified")
  obj <- AddModuleScore(obj, features = list(rownames(x)[1:5]), nbin = 4L, ctrl = 5L,
                        name = "tiny_module", seed = 560L, search = FALSE)
  check(length(obj$tiny_module1) == ncol(x) && all(is.finite(obj$tiny_module1)), "BPCells module score invalid")
  obj <- FindVariableFeatures(obj, nfeatures = 30L, verbose = FALSE)
  check(length(VariableFeatures(obj)) > 0L, "BPCells variable features missing")
} else if (mode == "io") {
  load_seurat()
  x <- fixture(20L, 12L)
  folder <- file.path(root, "tenx")
  dir.create(folder, mode = "0700")
  Matrix::writeMM(x, file.path(folder, "matrix.mtx"))
  writeLines(colnames(x), file.path(folder, "barcodes.tsv"))
  utils::write.table(data.frame(id = rownames(x), name = rownames(x)), file.path(folder, "genes.tsv"),
                     sep = "\t", row.names = FALSE, col.names = FALSE, quote = FALSE)
  plain <- Read10X(folder)
  check(isTRUE(all.equal(as.matrix(plain), as.matrix(x))), "Read10X round trip failed")
  compressed <- file.path(root, "tenx-gzip")
  dir.create(compressed, mode = "0700")
  write_gzip <- function(lines, path) {
    connection <- gzfile(path, open = "wt")
    on.exit(close(connection))
    writeLines(lines, connection)
  }
  write_gzip(readLines(file.path(folder, "matrix.mtx")), file.path(compressed, "matrix.mtx.gz"))
  write_gzip(colnames(x), file.path(compressed, "barcodes.tsv.gz"))
  write_gzip(paste(rownames(x), rownames(x), "Gene Expression", sep = "\t"),
             file.path(compressed, "features.tsv.gz"))
  zipped <- Read10X(compressed)
  check(isTRUE(all.equal(as.matrix(zipped), as.matrix(x))), "Read10X gzip round trip failed")
  path <- file.path(root, "counts.h5")
  file <- hdf5r::H5File$new(path, mode = "w")
  group <- file$create_group("matrix")
  group[["data"]] <- x@x
  group[["indices"]] <- x@i
  group[["indptr"]] <- x@p
  group[["shape"]] <- dim(x)
  group[["barcodes"]] <- colnames(x)
  features <- group$create_group("features")
  features[["id"]] <- rownames(x)
  features[["name"]] <- rownames(x)
  features[["feature_type"]] <- rep("Gene Expression", nrow(x))
  features[["genome"]] <- rep("synthetic", nrow(x))
  file$close_all()
  h5 <- Read10X_h5(path)
  check(isTRUE(all.equal(as.matrix(h5), as.matrix(x))), "Read10X_h5 round trip failed")
} else if (mode == "static") {
  load_seurat()
  data("pbmc_small", package = "SeuratObject")
  widget <- HoverLocator(DimPlot(pbmc_small, reduction = "tsne"),
                         information = FetchData(pbmc_small, vars = "MS4A1"))
  check(inherits(widget, "plotly") && inherits(widget, "htmlwidget"), "HoverLocator widget missing")
  html <- file.path(root, "hover.html")
  check(!file.exists(html), "static output already exists")
  htmlwidgets::saveWidget(widget, html, selfcontained = TRUE)
  check(file.info(html)$size > 10000, "standalone widget output too small")
  text <- paste(readLines(html, warn = FALSE), collapse = "\n")
  check(grepl("plotly", text, fixed = TRUE) && grepl("MS4A1", text, fixed = TRUE),
        "widget runtime or real feature content missing")
} else if (mode == "negative") {
  load_seurat()
  must_fail(setThreads(0L, verbose = FALSE), "positive integer")
  must_fail(Read10X_h5(file.path(root, "missing.h5")), "File not found")
  obj <- CreateSeuratObject(counts = fixture())
  must_fail(RunPCA(obj, npcs = 5L, verbose = FALSE), "variable features|scaled|scale.data")
  check(!file.exists(file.path(root, "missing.h5")), "negative test created missing input")
} else {
  stop(paste("unknown check mode:", mode), call. = FALSE)
}
cat(sprintf("SEURAT_CHECK %s PASS\n", mode))
