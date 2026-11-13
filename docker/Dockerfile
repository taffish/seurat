FROM satijalab/seurat:6.0.0@sha256:9cd7b1ae30adb89f5879c8cf36b6d3a2aa3586bdee81280edabb9349815960f7 AS libraries
COPY docker/install-sources.sh docker/select-libraries.R docker/rbioformats-offline.patch /tmp/
RUN bash /tmp/install-sources.sh

FROM rocker/r-ver:4.6.1@sha256:780bc87219250a6dfffef6c812999731986fd94d8d5f7e572d1157c923d1b4bb AS runtime

ENV DEBIAN_FRONTEND=noninteractive

# Ubuntu Noble uses live package mirrors: package revisions and availability can drift.
# See the installed dpkg inventory; base digests do not freeze apt indexes.
RUN set -eux; \
    sed -i 's|http://archive.ubuntu.com|https://archive.ubuntu.com|g; s|http://security.ubuntu.com|https://security.ubuntu.com|g' /etc/apt/sources.list.d/ubuntu.sources; \
    apt-get -o Acquire::Retries=3 -o Acquire::ForceIPv4=true -o APT::Update::Error-Mode=any update; \
    apt-get -o Acquire::Retries=3 -o Acquire::ForceIPv4=true install -y --no-install-recommends \
      bash \
      ca-certificates \
      curl \
      openjdk-21-jre-headless \
      libblosc1 \
      libgomp1 \
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

ENV JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64
RUN printf '%s\n' "$JAVA_HOME/lib/server" > /etc/ld.so.conf.d/seurat-java.conf && ldconfig
COPY --from=libraries /opt/export/R /usr/local/lib/R/site-library
COPY --from=libraries /opt/seurat/share /opt/seurat/share
COPY docker/seurat_runtime_info.R /usr/local/bin/seurat-runtime-info
COPY docker/seurat_smoke.R /opt/seurat/share/testdata/seurat_smoke.R
COPY docker/seurat_checks.R /opt/seurat/share/testdata/seurat_checks.R
COPY docker/seurat-v6.R docker/atera-counts.R docker/atera-morphology.R /opt/seurat/share/testdata/
COPY docker/atera/ /opt/seurat/share/testdata/atera/
COPY docker/seurat-check.py /usr/local/bin/seurat-check
COPY docker/seurat-gadget.py /usr/local/bin/seurat-gadget
COPY docker/seurat_gadget_server.R docker/seurat_gadget_smoke.py /opt/seurat/
COPY docker/seurat-resource.py docker/seurat_resource_smoke.py docker/seurat-resource-catalog.json docker/seurat-resource-profile.R /opt/seurat/
COPY docker/seurat-resource-PACKAGES /opt/seurat/resource-catalog/src/contrib/PACKAGES

RUN set -eux; \
    chmod a+rX -R /opt/seurat; \
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
ENV TAFFISH_VERSION=6.0.0-r1
