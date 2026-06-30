FROM satijalab/seurat:5.5.1 AS upstream

FROM rocker/r-ver:4.5.2

ENV DEBIAN_FRONTEND=noninteractive

RUN set -eux; \
    apt-get -o Acquire::Retries=3 update; \
    apt-get -o Acquire::Retries=3 install -y --no-install-recommends \
      bash \
      ca-certificates \
      curl \
      grep \
      libblas3 \
      libbz2-1.0 \
      libcairo2 \
      libcurl4t64 \
      libfftw3-double3 \
      libfontconfig1 \
      libfreetype6 \
      libfribidi0 \
      libgdal34t64 \
      libgeos-c1t64 \
      libgit2-1.7 \
      libglpk40 \
      libgsl27 \
      libharfbuzz0b \
      libharfbuzz-icu0 \
      libhdf5-103-1t64 \
      libicu74 \
      libjpeg-turbo8 \
      liblapack3 \
      liblzma5 \
      libpng16-16t64 \
      libproj25 \
      libssl3t64 \
      libtiff6 \
      libudunits2-0 \
      libuv1t64 \
      libwebpdemux2 \
      libwebpmux3 \
      libxml2 \
      pandoc \
      zlib1g; \
    rm -rf /var/lib/apt/lists/*

COPY --from=upstream /usr/local/lib/R/site-library /usr/local/lib/R/site-library
COPY docker/seurat_runtime_info.R /usr/local/bin/seurat-runtime-info
COPY docker/seurat_smoke.R /opt/seurat/share/testdata/seurat_smoke.R

RUN set -eux; \
    chmod +x /usr/local/bin/seurat-runtime-info /opt/seurat/share/testdata/seurat_smoke.R; \
    Rscript -e 'stopifnot(as.character(getRversion()) == "4.5.2"); stopifnot(as.character(packageVersion("Seurat")) == "5.5.1"); stopifnot(as.character(packageVersion("SeuratObject")) == "5.4.0")'; \
    Rscript -e 'pkgs <- c("Seurat","SeuratObject","Matrix","ggplot2","patchwork","future","sctransform","uwot","RANN","RcppAnnoy","RcppHNSW","RSpectra","hdf5r","BPCells","glmGamPoi","MAST","SingleCellExperiment","harmony","leidenbase","SeuratData"); missing <- pkgs[!vapply(pkgs, requireNamespace, logical(1), quietly=TRUE)]; if (length(missing)) stop(paste("missing", paste(missing, collapse=",")))'; \
    seurat-runtime-info --version | grep -F 'seurat-runtime-info 5.5.1-r1' >/dev/null; \
    seurat-runtime-info | grep -F "$(printf 'Seurat\t5.5.1')" >/dev/null; \
    seurat-runtime-info | grep -F "$(printf 'SeuratObject\t5.4.0')" >/dev/null; \
    seurat-runtime-info | grep -F "$(printf 'SeuratData\t0.2.2.9002')" >/dev/null; \
    tmp=/tmp/taf-seurat-build-smoke; \
    rm -rf "${tmp}"; \
    Rscript /opt/seurat/share/testdata/seurat_smoke.R "${tmp}"; \
    test -s "${tmp}/seurat_smoke.rds"; \
    test -s "${tmp}/markers.tsv"; \
    test -s "${tmp}/clusters.tsv"; \
    test -s "${tmp}/plots/umap.png"; \
    test -s "${tmp}/plots/qc_violin.pdf"; \
    grep -F 'Seurat' "${tmp}/versions.tsv" >/dev/null; \
    rm -rf "${tmp}"

WORKDIR /root

ENV SEURAT_HOME=/opt/seurat
ENV SEURAT_TESTDATA=/opt/seurat/share/testdata
ENV TAFFISH_ENV=TAFFISH
ENV TAFFISH_NAME=seurat
