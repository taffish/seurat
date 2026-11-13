#!/usr/bin/env bash
# Prepare a minimal runtime from the pinned official R library. Only the
# RBioFormats loader is adapted; the Seurat package and pixel decoder are unmodified.
set -euo pipefail
provenance=/opt/seurat/share/provenance
jar_dir=/opt/seurat/share/bioformats
library=/opt/export/R
mkdir -p "$provenance" "$jar_dir" "$library"
scratch=$(mktemp -d /tmp/seurat-reader.XXXXXX)
trap 'rm -rf -- "$scratch"' EXIT
cd "$scratch"
fetch() {
    Rscript --vanilla -e 'a <- commandArgs(TRUE); options(timeout=600L); for (i in 1:3) { result <- try(utils::download.file(a[1],a[2],method="libcurl",mode="wb",quiet=TRUE),silent=TRUE); if (identical(result,0L)) quit(status=0L); Sys.sleep(i) }; stop("cannot fetch fixed upstream artifact")' "$1" "$2"
    printf '%s  %s\n' "$3" "$2" | sha256sum --check --strict -
    printf '%s  %s\n' "$3" "${2##*/}" >> "$provenance/sources.sha256"
    printf '%s\t%s\n' "${2##*/}" "$1" >> "$provenance/sources.tsv"
}
# The release URLs can disappear; the hashes fix identity, not availability.
fetch https://downloads.openmicroscopy.org/bio-formats/8.5.0/artifacts/bioformats_package.jar "$jar_dir/bioformats_package-8.5.0.jar" c6e60665d53a334b66e4d635340151f403dfe57a64704c573dd4c03b873befb9
fetch https://bioconductor.org/packages/3.23/bioc/src/contrib/RBioFormats_1.12.0.tar.gz RBioFormats_1.12.0.tar.gz 1f500fae0c0dc15e3b38d6a48ddea1868248e6685b9e21967fee6a313f6a961f
tar -xzf RBioFormats_1.12.0.tar.gz
patch --batch --fuzz=0 --forward -p1 -d RBioFormats < /tmp/rbioformats-offline.patch
install -m 644 /tmp/rbioformats-offline.patch "$provenance/"
# Retain the corresponding patched source and its notices alongside the binary.
tar -czf "$provenance/RBioFormats_1.12.0-taffish-reader.tar.gz" RBioFormats
Rscript --vanilla /tmp/select-libraries.R "$scratch/packages" "$provenance/dependencies.tsv"
while IFS= read -r pkg; do
    if [[ "$pkg" != RBioFormats ]]; then cp -a "/usr/local/lib/R/site-library/$pkg" "$library/"; fi
done < "$scratch/packages"
R CMD INSTALL --no-test-load --library="$library" RBioFormats
chmod 644 "$jar_dir/bioformats_package-8.5.0.jar"
find "$library" -mindepth 2 -maxdepth 2 -type d -name include -print > "$provenance/build-only-headers-removed.txt"
while IFS= read -r headers; do rm -rf -- "$headers"; done < "$provenance/build-only-headers-removed.txt"
