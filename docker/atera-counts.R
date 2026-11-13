suppressPackageStartupMessages(library(Seurat))
future::plan(future::sequential)
d <- commandArgs(TRUE)[[1]]
expected <- matrix(c(4,0,0,6,5,7),2L,dimnames=list(c("SignalA","SignalB"),as.character(1:3)))
a <- ReadAtera(d,outs=c("matrix","centroids"),bpcells.dir=FALSE)
stopifnot(isTRUE(all.equal(as.matrix(a$matrix[["Gene Expression"]]),expected)),
          identical(a$centroids$cell,as.character(1:3)), all(a$centroids$x == c(1,3,8)),
          all(a$centroids$y == c(2,5,13)))
cat("PASS Atera local counts and centroids\n")
object <- LoadAtera(d,bpcells.dir=FALSE)
stopifnot(inherits(object,"Seurat"), isTRUE(all.equal(as.matrix(LayerData(object,layer="counts")),expected)),
          identical(Images(object),"fov"))
cat("PASS LoadAtera default without morphology, no external data or network\n")
