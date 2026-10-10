#!/usr/bin/env bash
# Build-only, fixed upstream source overlay. No scientific source patches.
set -euo pipefail
scratch=$(mktemp -d /tmp/seurat-source-build.XXXXXX)
trap 'rm -rf -- "$scratch"' EXIT
mkdir -p /opt/seurat/share/provenance
cd "$scratch"
Rscript --vanilla -e 'stopifnot(as.character(getRversion()) == "4.5.2"); stopifnot(as.character(packageVersion("Seurat")) == "5.5.1"); stopifnot(as.character(packageVersion("SeuratObject")) == "5.4.0")'
Rscript --vanilla -e 'stopifnot(as.character(packageVersion("uwot")) == "0.2.4", as.character(packageVersion("RSpectra")) == "0.16.2")'
Rscript --vanilla -e 'p <- installed.packages(); write.table(p[,c("Package","Version","Built")], "/opt/seurat/share/provenance/dependencies-before.tsv", sep="\t", row.names=FALSE, quote=FALSE)'
while read -r checksum archive; do
    package=${archive%%_*}
    primary="https://cran.r-project.org/src/contrib/$archive"
    fallback="https://cran.r-project.org/src/contrib/Archive/$package/$archive"
    if ! curl --fail --location --retry 3 --connect-timeout 30 --max-time 600 "$primary" -o "$archive"; then
        curl --fail --location --retry 3 --connect-timeout 30 --max-time 600 "$fallback" -o "$archive"
    fi
    printf '%s  %s\n' "$checksum" "$archive" | sha256sum --check --strict -
    printf '%s  %s\n' "$checksum" "$archive" >> /opt/seurat/share/provenance/sources.sha256
    printf '%s\t%s\t%s\n' "$archive" "$primary" "$fallback" >> /opt/seurat/share/provenance/sources.tsv
    R CMD INSTALL --no-multiarch "$archive"
done <<'SOURCES'
29e8955a0e1cad0775bcb6f29bde76f34cc2e1fa9c5f5d5d8d4962b91c3feaeb RcppThread_2.4.0.tar.gz
8366190e8fe26e79efc18be5391308ff00cde673d298bc7b39e7a84816718f39 Seurat_5.6.0.tar.gz
SOURCES
Rscript --vanilla -e 'stopifnot(as.character(packageVersion("Seurat")) == "5.6.0", as.character(packageVersion("uwot")) == "0.2.4", as.character(packageVersion("RcppThread")) == "2.4.0"); p <- installed.packages(); write.table(p[,c("Package","Version","Built","License")], "/opt/seurat/share/provenance/dependencies.tsv", sep="\t", row.names=FALSE, quote=FALSE)'
