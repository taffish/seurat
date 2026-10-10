FROM satijalab/seurat:5.5.1@sha256:048d965487afc2961c450879692281a73e24f6de47360ed2f11b31112ebd844e AS upstream

FROM rocker/r-ver:4.5.2@sha256:fd4ccdd3a4a6f7ef805e2daeee2a0fe3bf126bc231f36351223baecf5a595a4c AS runtime-base

ENV DEBIAN_FRONTEND=noninteractive

RUN set -eux; \
    apt-get -o Acquire::Retries=3 update; \
    apt-get -o Acquire::Retries=3 install -y --no-install-recommends \
      bash \
      ca-certificates \
      curl \
      fonts-dejavu-core \
      grep \
      libatomic1 \
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
      libtcl8.6 \
      libtiff6 \
      libtk8.6 \
      libudunits2-0 \
      libuv1t64 \
      libwebpdemux2 \
      libwebpmux3 \
      libxml2 \
      pandoc \
      python3 \
      zlib1g; \
    apt-get purge -y \
      g++ g++-13 g++-13-x86-64-linux-gnu g++-x86-64-linux-gnu \
      gcc gcc-13 gcc-13-x86-64-linux-gnu gcc-x86-64-linux-gnu \
      gfortran gfortran-13 gfortran-13-x86-64-linux-gnu gfortran-x86-64-linux-gnu \
      cpp cpp-13 cpp-13-x86-64-linux-gnu cpp-x86-64-linux-gnu make \
      libstdc++-13-dev libgcc-13-dev libgfortran-13-dev \
      libopenblas-dev libopenblas-pthread-dev libblas-dev liblapack-dev libtiff-doc; \
    rm -rf /var/lib/apt/lists/*

FROM runtime-base AS libraries

COPY --from=upstream /usr/local/lib/R/site-library /usr/local/lib/R/site-library
COPY docker/install-sources.sh /tmp/install-sources.sh
RUN set -eux; \
    apt-get -o Acquire::Retries=3 update; \
    apt-get -o Acquire::Retries=3 install -y --no-install-recommends \
      g++ gfortran make libblas-dev liblapack-dev; \
    MAKEFLAGS=-j2 bash /tmp/install-sources.sh; \
    find /usr/local/lib/R/site-library -mindepth 2 -maxdepth 2 -type d -name include \
      -print > /opt/seurat/share/provenance/build-only-headers-removed.txt; \
    while IFS= read -r headers; do rm -rf -- "$headers"; done < /opt/seurat/share/provenance/build-only-headers-removed.txt; \
    rm -rf /var/lib/apt/lists/* /tmp/install-sources.sh

FROM runtime-base AS runtime

COPY --from=libraries /usr/local/lib/R/site-library /usr/local/lib/R/site-library
COPY --from=libraries /opt/seurat/share/provenance /opt/seurat/share/provenance
COPY docker/seurat_runtime_info.R /usr/local/bin/seurat-runtime-info
COPY docker/seurat_smoke.R /opt/seurat/share/testdata/seurat_smoke.R
COPY docker/seurat_checks.R /opt/seurat/share/testdata/seurat_checks.R
COPY docker/seurat-check.py /usr/local/bin/seurat-check
COPY docker/seurat-gadget.py /usr/local/bin/seurat-gadget
COPY docker/seurat_gadget_server.R docker/seurat_gadget_smoke.py /opt/seurat/
COPY docker/seurat-resource.py docker/seurat_resource_smoke.py docker/seurat-resource-catalog.json docker/seurat-resource-profile.R /opt/seurat/
COPY docker/seurat-resource-PACKAGES /opt/seurat/resource-catalog/src/contrib/PACKAGES

RUN set -eux; \
    chmod 755 /usr/local/bin/seurat-runtime-info /usr/local/bin/seurat-check /usr/local/bin/seurat-gadget /opt/seurat/seurat-resource.py; \
    ln -s /opt/seurat/seurat-resource.py /usr/local/bin/seurat-resource; \
    printf '\nsource("/opt/seurat/seurat-resource-profile.R")\n' >> /usr/local/lib/R/etc/Rprofile.site; \
    dpkg-query -W > /opt/seurat/share/provenance/system-packages.tsv; \
    seurat-check buildtime

WORKDIR /tmp

ENV SEURAT_HOME=/opt/seurat
ENV SEURAT_TESTDATA=/opt/seurat/share/testdata
ENV PYTHONDONTWRITEBYTECODE=1
ENV RETICULATE_USE_MANAGED_VENV=no
ENV TAFFISH_ENV=TAFFISH
ENV TAFFISH_NAME=seurat
