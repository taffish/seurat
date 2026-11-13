# Known-pixel checks on independent, synthetic lossless JPEG2000 OME-TIFFs.
suppressPackageStartupMessages(library(Seurat))
future::plan(future::sequential)
fixture <- commandArgs(TRUE)[1L]
if (is.na(fixture)) fixture <- "/opt/seurat/share/testdata/atera"
stopifnot(identical(as.character(RBioFormats::BioFormats.version()),"8.5.0"),
          as.character(packageVersion("RBioFormats")) == "1.12.0")
expected <- function(k, l, x, y) outer(x-1L,y-1L,
    if (k == 0L) function(x,y) 8 + 2*x + 3*y + 13*(l-1)
    else function(x,y) 40000 + 17*x + 31*y + 301*(l-1))
get <- function(channel,...) Seurat::ReadAtera(fixture,outs="morphology",bpcells.dir=FALSE,
                                              morphology.channel=channel,...)$morphology
for (k in 0:1) {
  for (l in 1:2) {
    nx <- 48L %/% l; ny <- 32L %/% l
    m <- get(k,morphology.resolution=l)
    stopifnot(identical(as.integer(dim(m$image)),c(nx,ny)), all(as.matrix(m$image) == expected(k,l,1:nx,1:ny)),
              m$resolution == l, m$n.resolutions == 2, m$pixel.size == 0.5*l, all(m$origin == 0))
  }
  m <- get(c("dapi","marker")[k+1L])
  stopifnot(m$resolution == 2L, all(as.matrix(m$image) == expected(k,2,1:24,1:16)))
}
m <- get("marker",morphology.resolution=1L,morphology.region=list(x=c(2,4),y=c(1,2.5)))
stopifnot(all(as.matrix(m$image) == expected(1,1,5:9,3:6)),all(m$origin == c(2,1)))
e <- tryCatch({get("absent"); NULL},error=conditionMessage)
stopifnot(is.character(e),grepl("No morphology image",e,fixed=TRUE))
cache <- tools::R_user_dir("RBioFormats","cache")
stopifnot(!length(list.files(cache,pattern="\\.jar$",recursive=TRUE)))
cat("PASS Atera, OME 8.5.0: 8/16-bit, both channel indices, every pixel at each pyramid level, crop, coordinates and missing channel\n")
