# Public APIs on arbitrary generated numbers. No external references or samples.
suppressPackageStartupMessages(library(Seurat))
stopifnot(as.character(packageVersion("Seurat")) == "6.0.0")
setThreads(1L, verbose=FALSE)
future::plan(future::sequential)
set.seed(17)
x <- matrix(rnorm(14*80),nrow=14,dimnames=list(paste0("f",1:14),paste0("c",1:80)))
y <- seq_len(ncol(x)) + sin(seq_len(ncol(x)))
ok <- TRUE
probe <- function(name, fn) {
  tryCatch({fn(); cat("PASS",name,"\n")}, error=function(e) {
    cat("FAIL",name,":",conditionMessage(e),"\n"); ok <<- FALSE
  })
}
for (method in c("plsr","cppls","spls")) probe(paste("RunPLS",method), function() {
  d <- RunPLS(x,assay="RNA",Y=y,ncomp=2L,pls.function=method,verbose=FALSE)
  stopifnot(identical(dim(Embeddings(d)), c(80L,2L)), all(is.finite(Embeddings(d))))
})
probe("RunDiffusionMap", function() {
  d <- RunDiffusionMap(x,assay="RNA",ncomp=2L,metric="euclidean",verbose=FALSE)
  stopifnot(identical(dim(Embeddings(d)), c(80L,2L)), all(is.finite(Embeddings(d))))
})
probe("NormalizeChiSquared", function() {
  n <- matrix(c(4L,6L,2L,8L,2L,8L),nrow=2)
  expected <- outer(rowSums(n),colSums(n))/sum(n)
  stopifnot(isTRUE(all.equal(unname(NormalizeChiSquared(n,verbose=FALSE)),(n-expected)/sqrt(expected))))
})
probe("Atera runtime including optional morphology", function() {
  stopifnot(all(vapply(c("blosc","jsonlite","data.table","RBioFormats"),requireNamespace,logical(1),quietly=TRUE)))
})
if (!ok) quit(status=1)
