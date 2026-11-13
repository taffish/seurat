# Select the application, supported options and their runtime dependency closure.
args <- commandArgs(TRUE)
db <- installed.packages()
roots <- c("Seurat","SeuratObject","shiny","miniUI","plotly","htmlwidgets","SeuratData",
           "BPCells","glmGamPoi","MAST","SingleCellExperiment","harmony","leidenbase",
           "RcppParallel","hdf5r","arrow","sf","presto","R.utils","Rfast2","spls","pls",
           "destiny","ComplexHeatmap","circlize","blosc","RBioFormats","ggrastr","lmtest",
           "fitdistrplus","ape","rsvd","jsonlite","data.table","sp","tcltk","RcppEigen",
           "RcppProgress","RcppHNSW","RANN","RcppAnnoy","png","ragg")
stopifnot(getRversion() == "4.6.1", packageVersion("Seurat") == "6.0.0",
          packageVersion("SeuratObject") == "5.4.0", all(roots %in% rownames(db)))
deps <- tools::package_dependencies(roots, db=db, which=c("Depends","Imports","LinkingTo"), recursive=TRUE)
keys <- intersect(rownames(db), unique(c(roots, unlist(deps, use.names=FALSE))))
selected <- db[keys,,drop=FALSE]
stopifnot(all(selected[,"LibPath"] %in% c(.Library, "/usr/local/lib/R/site-library")))
writeLines(sort(selected[selected[,"LibPath"] == "/usr/local/lib/R/site-library","Package"]), args[1L])
write.table(selected[,c("Package","Version","Built","License")],args[2L],sep="\t",row.names=FALSE,quote=FALSE)
