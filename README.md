# seurat

TAFFISH wrapper for [Seurat](https://satijalab.org/seurat/) 5.5.0, the Satija
Lab R toolkit for single-cell analysis. This app provides a general Seurat R
runtime, similar in role to `taf-scanpy` on the Python side. It is not the
future TAFFISH `scrnaseq-r` flow-facing helper toolkit.

## Package Identity

- name: `seurat`
- command: `taf-seurat`
- kind: `tool`
- TAFFISH version: `5.5.0-r1`
- container image: `ghcr.io/taffish/seurat:5.5.0-r1`
- upstream package source: `satijalab/seurat:5.5.0`
- runtime base: `rocker/r-ver:4.5.2`
- default command: `Rscript`
- native platform: `linux/amd64`
- TAFFISH wrapper license: Apache-2.0
- upstream Seurat license: MIT + file LICENSE

The upstream Satija Lab image and this TAFFISH image are `linux/amd64`. The
TAFFISH wrapper declares `--platform linux/amd64` for Docker and Podman so
Apple Silicon or other arm64 hosts can run it through amd64 emulation. This is
not native arm64 support.

## Installation

```sh
taf install seurat
taf-seurat --help
```

The app uses a thin TAFFISH container wrapper:

```taf
<taf-app:container:ghcr.io/taffish/seurat:5.5.0-r1$@[docker/podman: --platform linux/amd64]>
Rscript ::*ARGV*::
```

Wrapper-level help and version are separate from the R runtime:

```sh
taf-seurat --help
taf-seurat --version
taf-seurat -- --version
taf-seurat Rscript --version
taf-seurat seurat-runtime-info
```

Because `command_mode = true`, call commands in the container explicitly:

```sh
taf-seurat Rscript analysis.R
taf-seurat seurat-runtime-info
```

## Included Runtime

The image copies the official Satija Lab `satijalab/seurat:5.5.0` R package
library into a smaller `rocker/r-ver:4.5.2` runtime image. This keeps the
validated upstream Seurat package set but removes RStudio Server and other
layers that are not needed for command-line TAFFISH use. The build verifies:

- R 4.5.2
- Seurat 5.5.0
- SeuratObject 5.4.0
- required system libraries for all bundled site-library packages

`seurat-runtime-info` reports selected bundled packages. On the validated
runtime it includes core and common packages such as `Matrix`, `ggplot2`,
`patchwork`, `future`, `sctransform`, `uwot`, `RANN`, `RcppAnnoy`,
`RcppHNSW`, `RSpectra`, `hdf5r`, `BPCells`, `glmGamPoi`, `MAST`,
`SingleCellExperiment`, `harmony`, and `leidenbase`.

Some Satija/scRNA-seq ecosystem packages are not included in r1:

- `Signac`
- `Azimuth`
- `SeuratData`

Those are useful but carry separate data, modality, reference, or workflow
expectations. They should be added later only when a dedicated app or flow needs
them and the resource boundary is clear.

## Usage

Show TAFFISH help:

```sh
taf-seurat --help
```

Show Rscript version:

```sh
taf-seurat -- --version
taf-seurat Rscript --version
```

Print package versions:

```sh
taf-seurat seurat-runtime-info
```

Run a Seurat script:

```sh
taf-seurat Rscript analysis.R
```

Run a compact one-liner:

```sh
taf-seurat Rscript -e 'library(Seurat); packageVersion("Seurat")'
```

## Example

Create a tiny object and write it to RDS:

```sh
taf-seurat Rscript - <<'RS'
suppressPackageStartupMessages(library(Seurat))
counts <- matrix(c(1, 0, 3, 0, 2, 1, 5, 0, 0), nrow = 3)
rownames(counts) <- c("GeneA", "GeneB", "MT-GeneC")
colnames(counts) <- c("cell1", "cell2", "cell3")
obj <- CreateSeuratObject(counts = counts)
obj[["percent.mt"]] <- PercentageFeatureSet(obj, pattern = "^MT-")
saveRDS(obj, "tiny.seurat.rds")
RS
```

## Inputs And Outputs

Seurat is an R API rather than a single fixed CLI. Inputs and outputs are
controlled by the R script you run. Typical inputs include 10x matrix
directories, HDF5 matrices, text matrices, and RDS objects. Typical outputs
include Seurat `.rds` objects, marker tables, metadata tables, and static plots
written by R graphics or ggplot2.

For TAFFISH flow-facing, fixed-output helper commands, use a future
`taf-scrnaseq-r` app. This `taf-seurat` app deliberately preserves the general
Seurat runtime.

## Boundaries

r1 does not bundle Cell Ranger, genome references, prebuilt reference atlases,
Azimuth references, Signac/scATAC workflows, SeuratData datasets, or TAFFISH
`scrnaseq-r` helper commands.

It also does not replace manual biological interpretation. Seurat scripts can
generate QC, clustering, marker, integration, and annotation outputs, but users
and flows must record thresholds, resolutions, reference choices, and final
cell type decisions explicitly.

The image is still large because Seurat and its single-cell R dependencies are
large, but it is slimmer than directly deriving from the full official image.
Downstream flows should not install Seurat packages at runtime.

## Smoke Coverage

Smoke tests check:

- R, Seurat, and SeuratObject versions.
- `seurat-runtime-info` output.
- required core packages can be loaded.
- known absent optional packages are reported as `MISSING`.
- a tiny synthetic Seurat workflow runs offline:
  `CreateSeuratObject`, `PercentageFeatureSet`, `NormalizeData`,
  `FindVariableFeatures`, `ScaleData`, `RunPCA`, `FindNeighbors`,
  `FindClusters`, `RunUMAP`, `FindAllMarkers`, RDS export, marker table export,
  cluster table export, and PNG/PDF plots.

Each smoke test creates its own `/tmp/taf-seurat-*` workspace and does not use
network access, external references, atlases, or datasets.

## Citation

For Seurat v5, cite:

Hao et al. Dictionary learning for integrative, multimodal and scalable
single-cell analysis. Nature Biotechnology (2023). DOI:
10.1038/s41587-023-01767-y.
