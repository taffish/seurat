# seurat

`seurat` packages [Seurat](https://satijalab.org/seurat/) 6.0.0 for TAFFISH:
an R runtime for single-cell analysis, with upstream browser gadgets and
explicitly installed, reusable SeuratData datasets.

Package identity:

- name: `seurat`; command: `taf-seurat`; kind: `tool`
- TAFFISH version: `6.0.0-r1`
- image: `ghcr.io/taffish/seurat:6.0.0-r1`
- default command: `Rscript`; automatic command mode: enabled
- native platform: `linux/amd64`
- packaging license: Apache-2.0; upstream Seurat: MIT + file LICENSE

## What This App Packages

The app preserves the general upstream R API, rather than adding a fixed
analysis pipeline. Your script chooses the input, parameters and outputs.
It includes a foreground launcher for Seurat's own Shiny gadgets; RStudio
Server is neither needed nor included.

[Seurat 6.0.0](https://github.com/satijalab/seurat/releases/tag/v6.0.0)
adds scSLIDE-related methods and 10x Atera spatial input. Existing R scripts
can still use the RNA, SCT, BPCells and plotting entrypoints below. The
major version changes upstream APIs; record the Seurat version with outputs.

## Scope

Included capabilities are ordinary Seurat R workflows, SCTransform, the R
`uwot` UMAP path, BPCells-backed matrices, local matrix/HDF5 input, RDS/table
and static PNG/PDF output, standalone `HoverLocator` HTML widgets, and
Seurat's `IFeaturePlot`/`CellSelector`-style browser gadgets. Bundled
`pbmc_small` supports tiny offline examples.

The app does not supply a fixed-output TAFFISH analysis flow, Cell Ranger,
genome references, Signac/scATAC workflows, the Azimuth mapping application,
RStudio Server, an FIt-SNE executable, or a scientific Python environment.
Selectable SeuratData packages have their own capability boundaries below;
catalog membership does not supply every associated analysis dependency.

## Container Contents and Source Provenance

The package takes the unmodified Seurat package and its R dependency closure
from the official native amd64 image. It does not ship its RStudio server or a
second full R installation.

| Component | Source or identity |
| --- | --- |
| Official Seurat library | `satijalab/seurat:6.0.0@sha256:9cd7b1ae30adb89f5879c8cf36b6d3a2aa3586bdee81280edabb9349815960f7` |
| Runtime | `rocker/r-ver:4.6.1@sha256:780bc87219250a6dfffef6c812999731986fd94d8d5f7e572d1157c923d1b4bb`; R 4.6.1, SeuratObject 5.4.0, uwot 0.2.5 |
| Atera R bridge | [Bioconductor RBioFormats 1.12.0](https://bioconductor.org/packages/3.23/bioc/html/RBioFormats.html), GPL-3; source SHA256 `1f500fae0c0dc15e3b38d6a48ddea1868248e6685b9e21967fee6a313f6a961f` |
| Java reader | [OME Bio-Formats 8.5.0](https://downloads.openmicroscopy.org/bio-formats/8.5.0/), official GPL distribution; JAR SHA256 `c6e60665d53a334b66e4d635340151f403dfe57a64704c573dd4c03b873befb9` |

[The downstream loader patch](docker/rbioformats-offline.patch) changes the
version declaration and JAR lookup only. Instead of downloading 7.3.0 into
each user's cache, the bridge reads the fixed 8.5.0 JAR from the image and
fails if missing. The actual reader, pixel decoding and Seurat algorithms are
not patched. The upstream JAR retains its internal notices; corresponding
[OME sources](https://github.com/ome/bioformats/tree/v8.5.0), patched RBioFormats
source and the applied diff are identifiable from the image provenance.
Ubuntu packages are resolved from live Noble mirrors; a digest or source hash
guarantees identity, not continued availability of upstream packages.
The native amd64 runtime is 3,334,390,588 bytes (3.11 GiB by Docker inspect);
the compressed Apptainer SIF is 1,135,435,776 bytes (1.06 GiB). These measurements
include Java and the bundled reader, not separately installed SeuratData packages.
Use the packaged runtime for analysis, not for compiling additional R packages.

### Local Atera morphology

Use `LoadAtera("my-run")` for counts and coordinates. For a separately
requested channel in `morphology_2d/chNNNN_<channel>.ome.tif`:

```r
library(Seurat)
m <- ReadAtera("my-run", outs = "morphology", morphology.channel = "dapi",
               morphology.resolution = 1L, morphology.region = list(x=c(2,4), y=c(1,2.5)))$morphology
dim(m$image)       # [x, y]; region limits and origin are in microns
m$pixel.size
```

Resolution 1 is full resolution; without a level, Seurat chooses the smallest
overview. Cropping in microns needs `pixel_size` in `experiment.spatial`.
Give large slides a bounded region and sufficient memory. This is an offline
file reader, not an image viewer/server or a claim for every Bio-Formats format.

Packaged commands and paths:

- `R`, `Rscript`: R runtime; `seurat-runtime-info`: selected package versions.
- `seurat-resource`: selected fixed dataset installation and verification.
- `seurat-gadget`: foreground supervisor for a trusted upstream gadget script.
- `seurat-check`: independent offline packaging checks, not an analysis pipeline.
- `/opt/seurat/share/provenance/`: source checksums/URLs, selected R package
  inventories, runtime system packages and build-only header removal inventory.
- `/opt/seurat/share/testdata/`: synthetic smoke scripts.
- `/opt/seurat/resource-catalog/`: frozen SeuratData metadata, not datasets.

The retained package set includes `Matrix`, `ggplot2`, `patchwork`, `future`,
`sctransform`, `uwot`, `RANN`, `RcppAnnoy`, `RcppHNSW`, `RSpectra`, `hdf5r`,
`BPCells`, `glmGamPoi`, `MAST`, `SingleCellExperiment`, `harmony`, `leidenbase`
and `SeuratData`. Use `seurat-runtime-info` and the complete inventory for
precise versions rather than installing additional packages at runtime.

## Usage and Command Mode

After installing the app with `taf install seurat`:

```sh
taf-seurat --help
taf-seurat --version
taf-seurat -- --help
taf-seurat -- --version
taf-seurat Rscript --version
taf-seurat seurat-runtime-info
taf-seurat Rscript analysis.R
```

The first two commands are wrapper metadata. `-- --help` and `-- --version`
reach the default `Rscript`. A non-option-leading executable such as `Rscript`
or `seurat-resource` enters automatic command mode. Use the explicit
`Rscript analysis.R` form: a bare `analysis.R` is treated as a command.

Prefer an R script for expressions containing quotes or shell metacharacters.
Save this as `analysis.R`, then run the last command above:

```r
suppressPackageStartupMessages(library(Seurat))
setThreads(1)
data("pbmc_small")
saveRDS(pbmc_small, "example.seurat.rds")
write.table(pbmc_small[[]], "metadata.tsv", sep = "\t", quote = FALSE)
pdf("clusters.pdf")
print(DimPlot(pbmc_small))
dev.off()
png("clusters.png", width = 900, height = 700)
print(DimPlot(pbmc_small))
dev.off()
widget <- HoverLocator(DimPlot(pbmc_small))
htmlwidgets::saveWidget(widget, "hover.html", selfcontained = TRUE)
```

`hover.html` is an upstream interactive plot saved as a standalone file, not
a running Shiny service. Open the exported file in a browser; no port mapping
is needed on Docker, Podman or Apptainer. The bundled pandoc supports
`selfcontained = TRUE`. Saving a widget and running a gadget are separate
paths; a saved file does not preserve a live R session.

TAFFISH command arguments are compiled into shell text. For a filename
containing spaces, preserve a literal quoting layer, for example
`taf-seurat Rscript "'analysis with spaces.R'"`; ordinary shell quoting alone
may not preserve grouping in the generated command. Prefer simple script
names and put complicated expressions inside the script.

## Inputs and Output Notes

Inputs include local count matrices, 10x MEX directories, supported HDF5
files, RDS objects, BPCells directories and selected references. Choose the
matching upstream reader and assay semantics; an extension alone does not
establish compatibility.

TAFFISH exposes the working directory to the container. Run in a writable
project directory and use explicit output paths there. Docker/Podman preserve
the invoking UID/GID; files written only under container `/tmp` are disposable.
Your script controls input modification and output overwrite behavior. Record
input identities, seeds, thread counts, thresholds, resolutions and reference
choices with each analysis. Packaging smoke does not validate its conclusions.

## Backend Usage and Capability Matrix

Choose one backend for an ordinary script:

```sh
TAFFISH_CONTAINER_BACKEND=docker taf-seurat Rscript analysis.R
TAFFISH_CONTAINER_BACKEND=podman taf-seurat Rscript analysis.R
TAFFISH_CONTAINER_BACKEND=apptainer taf-seurat Rscript analysis.R
```

| Capability | Docker | Podman | Apptainer | Boundary |
| --- | --- | --- | --- | --- |
| CLI and static plots | Wrapper selects amd64 | Wrapper selects amd64 | Native amd64 Linux | Script output persists in the project directory; open standalone HTML in a browser |
| Prepared resources | Automatic read-only volume | Automatic read-only volume | Automatic read-only bind | Same fixed inventory; installation is separate |
| Resource installation | Existing host root mounted at `/resource-install` read-write | Same, with user namespace mapping | Existing host root bound read-write | Explicit helper operation, not normal analysis |
| Browser gadget | Loopback host publication; container binds `0.0.0.0` | Same | Shared-network loopback; no port mapping | Commands below; no authentication/TLS |

Docker/Podman on arm64 hosts require working amd64 emulation supplied by the
host engine. This is not native `linux/arm64`, and performance depends on that
engine. Apptainer is used on amd64 Linux; macOS or arm64-only environments can
use an amd64 Linux server via SSH. ARM-host amd64 emulation was not separately
validated for this candidate; it is not counted as a native platform PASS.

## Resources, Databases and Models

Ordinary analysis needs no downloaded model. User matrices, fitted SCT models
and analysis-specific references are project inputs/outputs, not automatically
shared global resources. `pbmc_small` is small bundled example data. Reusable
SeuratData datasets/reference packages are a separate resource family.

### Fixed selectable family

Catalog `seurat-data-20261004` freezes the upstream
[SeuratData metadata](https://seurat.nygenome.org/src/contrib/PACKAGES),
IDs, versions, URLs, licenses and upstream MD5 checksums. Select exact members;
there is no default whole-family download:

```sh
taf-seurat seurat-resource list
taf-seurat seurat-resource --help
```

For example, `pbmc3k@3.1.4` is a 93,780,025-byte archive (about 89.4 MiB),
before unpacking, installation, cache and retained-snapshot overhead. Other
members can be much larger; unknown sizes are not treated as zero. The helper
checks free space before/during download and before installation.

The catalog records CC BY 4.0 separately from software licenses; preserve
dataset attribution. `pbmcMultiome@0.1.4` requires unbundled Signac and is
marked `unsupported`; install and dry-run reject it before downloading.
The 11 Azimuth reference members are `storage-only`: fixed installation and
raw data access do not provide Azimuth analysis or `LoadData(type = "azimuth")`.
Other catalog members' mandatory package requirements fit this runtime, but
this is not a claim that every member has been scientifically validated.

### Personal installation and reuse

Automatic resource mounts accept physical paths containing only letters,
digits, `_`, `.`, `/`, `+` or `-`. Other characters are rejected instead of
being reinterpreted. Create the destination first:

```sh
SEURAT_RESOURCES="${XDG_DATA_HOME:-$HOME/.local/share}/taffish/resources/seurat/seurat-data-20261004"
mkdir -p "$SEURAT_RESOURCES"
```

Choose **one** backend below. Append `--dry-run` to preview; `--dataset` may
be repeated to select more members:

```sh
TAFFISH_CONTAINER_BACKEND=docker TAFFISH_SEURAT_RESOURCE_INSTALL_ROOT="$SEURAT_RESOURCES" taf-seurat seurat-resource install --dataset pbmc3k@3.1.4 --resource-root /resource-install
TAFFISH_CONTAINER_BACKEND=podman TAFFISH_SEURAT_RESOURCE_INSTALL_ROOT="$SEURAT_RESOURCES" taf-seurat seurat-resource install --dataset pbmc3k@3.1.4 --resource-root /resource-install
TAFFISH_CONTAINER_BACKEND=apptainer TAFFISH_SEURAT_RESOURCE_INSTALL_ROOT="$SEURAT_RESOURCES" taf-seurat seurat-resource install --dataset pbmc3k@3.1.4 --resource-root /resource-install
```

`TAFFISH_SEURAT_RESOURCE_INSTALL_ROOT` is installation-only: it maps the
existing host directory to `/resource-install` read-write and takes priority
over resource discovery. Do not leave it exported during analysis. A bare
install into the container's default home can disappear with the container.

Normal invocations select the first existing root in this order:

1. Explicit `TAFFISH_SEURAT_RESOURCE_PATH`, if set;
2. `${XDG_DATA_HOME:-$HOME/.local/share}/taffish/resources/seurat/seurat-data-20261004`;
3. `/usr/local/share/taffish/resources/seurat/seurat-data-20261004`;
4. `/opt/taffish/resources/seurat/seurat-data-20261004`.

The completed root is mounted read-only at `/opt/taffish-resources/seurat`.
The R site profile verifies it and adds `current/library` to `.libPaths()`.
An invalid explicit or earlier-priority root fails closed, rather than falling
back silently to another resource version.

```sh
taf-seurat seurat-resource verify --resource-root /opt/taffish-resources/seurat
taf-seurat Rscript use-data.R
```

For example, save this as `use-data.R`:

```r
library(Seurat)
library(SeuratData)
pbmc <- LoadData("pbmc3k")
saveRDS(pbmc, "pbmc3k.seurat.rds")
```

Use ordinary `Rscript`: `--vanilla` disables the resource site profile. Normal
startup uses the fixed local catalog without a writable manifest cache and
does not download absent datasets. Advanced users can explicitly opt R back
into the upstream remote catalog with a **container-side** variable:

```sh
TAFFISH_CONTAINER_BACKEND=docker taf-seurat env TAFFISH_SEURAT_RESOURCE_ALLOW_NETWORK=1 Rscript analysis.R
TAFFISH_CONTAINER_BACKEND=podman taf-seurat env TAFFISH_SEURAT_RESOURCE_ALLOW_NETWORK=1 Rscript analysis.R
TAFFISH_CONTAINER_BACKEND=apptainer taf-seurat env TAFFISH_SEURAT_RESOURCE_ALLOW_NETWORK=1 Rscript analysis.R
```

This bypasses the offline-catalog policy and is unnecessary for managed
installation/reuse. A host-only variable prefix is not forwarded consistently
by all backends; the explicit `env` automatic-command form above is required.

### Administrator-once system sharing

An administrator can create and own a versioned site root above, then run the
same explicit installation command from their authorized administrator
session with `SEURAT_RESOURCES` set to it. The site root and parent directories
must be searchable by readers (normally directories with mode `0755`).
Installed directories/files are readable by ordinary
users; download cache and installation lock remain installer-owned. Users
need no elevated privileges, download, installation or write access to reuse
the completed snapshot. Ordinary users reuse the administrator-installed
resources read-only; they do not own or modify the shared cache or snapshots.

For a nonstandard prepared root, set
`TAFFISH_SEURAT_RESOURCE_PATH=/safe/prepared/root`. Set
`TAFFISH_SEURAT_RESOURCE_AUTO_MOUNT=0` to disable discovery. Manual read-only
bind alternatives for site policy are:

```sh
TAFFISH_CONTAINER_BACKEND=docker TAFFISH_SEURAT_RESOURCE_AUTO_MOUNT=0 TAFFISH_DOCKER_RUN_ARGS="-v $SEURAT_RESOURCES:/opt/taffish-resources/seurat:ro" taf-seurat Rscript use-data.R
TAFFISH_CONTAINER_BACKEND=podman TAFFISH_SEURAT_RESOURCE_AUTO_MOUNT=0 TAFFISH_PODMAN_RUN_ARGS="-v $SEURAT_RESOURCES:/opt/taffish-resources/seurat:ro" taf-seurat Rscript use-data.R
TAFFISH_CONTAINER_BACKEND=apptainer TAFFISH_SEURAT_RESOURCE_AUTO_MOUNT=0 TAFFISH_APPTAINER_RUN_ARGS="--bind $SEURAT_RESOURCES:/opt/taffish-resources/seurat:ro" taf-seurat Rscript use-data.R
```

### Integrity and lifecycle

The helper downloads selected fixed versions over HTTPS, resumes owned partial
downloads where supported, verifies archive checksums, records downloaded
SHA256 and builds an installed file inventory. Private staging and an atomic
`current` pointer preserve the last completed snapshot on failure. Repeating
a verified selection is idempotent; adding a member preserves previous
members. A lock prevents concurrent writers.

`verify` checks identities and file hashes, not mere directory existence.
Corruption fails verification; `--force` permits an explicit administrator-led
reinstall. Through the installation bind,
`seurat-resource clear-cache --dry-run --resource-root /resource-install`
previews owned download-cache cleanup; omit `--dry-run` to perform it.
Installed and previous snapshots are not removed by cache cleanup. Retained
snapshots require deliberate administrator lifecycle management.

Choose species, tissue, modality and version explicitly. A representative installation is not full-family scientific validation or a system-directory deployment.

## Browser Gadgets

Seurat's interactive plotting/selection functions use Shiny and miniUI. The
launcher preserves those upstream interfaces. Save this trusted script as
`gadget.R` in the working directory:

```r
library(Seurat)
data("pbmc_small")
IFeaturePlot(pbmc_small, feature = "MS4A1")
```

Choose one backend; after `ready`, open the printed
`http://127.0.0.1:8787/` and keep the launcher in the foreground:

```sh
TAFFISH_CONTAINER_BACKEND=docker TAFFISH_DOCKER_RUN_ARGS='-p 127.0.0.1:8787:8787' taf-seurat seurat-gadget --script gadget.R --bind 0.0.0.0
TAFFISH_CONTAINER_BACKEND=podman TAFFISH_PODMAN_RUN_ARGS='-p 127.0.0.1:8787:8787' taf-seurat seurat-gadget --script gadget.R --bind 0.0.0.0
TAFFISH_CONTAINER_BACKEND=apptainer taf-seurat seurat-gadget --script gadget.R --bind 127.0.0.1 --port 8787
```

Docker/Podman listen on `0.0.0.0` **inside** the container while publishing
only host `127.0.0.1`. Apptainer normally shares the host network; keep its
listener on `127.0.0.1` and do not add Docker's `-p`. For a remote amd64 Linux
server, launch there and create a tunnel from your computer:

```sh
ssh -N -L 8787:127.0.0.1:8787 user@server
```

For an occupied host port, Docker/Podman can map `127.0.0.1:8788:8787` with
`--host-port 8788`; Apptainer can use `--port 8788`. Match the SSH tunnel and
browser port. `--host-port` changes the printed address, not the listener.

The script must call an upstream gadget: creating a Seurat object alone does
not start a server. For selections, save the documented upstream return value
after the gadget returns, into the mounted working directory. Closing the
browser is not a reliable stop/save command. Use the gadget's completion
control or Ctrl-C in the launcher; interruption does not guarantee that a
pending selection has been saved.

Before starting R, the launcher prints starting, URL, SSH, Ctrl-C and a private
internal log path. A separate `ready` confirms its child and Shiny endpoint.
It supervises the child, bounds startup, reports failure logs and cleans up
owned processes on Ctrl-C/TERM. Logs are private temporary files, not default
host outputs; capture terminal output if it must persist. Run only scripts
you trust. There is no authentication/TLS: never expose the service publicly.
Stop the attached service with Ctrl-C. For Apptainer, a TERM sent only to an
outer foreground terminal client is not equivalent to interrupting the attached
session.

### Development entrypoint

For a short standalone HTML export, save the `hover.R` example from
[`docs/help.md`](docs/help.md) in this source checkout and run:

```sh
taf run -b docker -- Rscript hover.R
```

This one-shot command writes a standalone file. The long-running browser
gadget has a different lifecycle.

With TAFFISH 0.11.0, `taf run` buffers the long-running GUI's output instead
of reliably showing the startup card immediately. It is not a supported
foreground GUI entrypoint for this release. From this app's source directory,
build first and use the generated wrapper (with `gadget.R` in that directory):

```sh
taf build
TAFFISH_CONTAINER_BACKEND=docker TAFFISH_DOCKER_RUN_ARGS='-p 127.0.0.1:8787:8787' target/taf-seurat-v6.0.0-r1 seurat-gadget --script gadget.R --bind 0.0.0.0
TAFFISH_CONTAINER_BACKEND=podman TAFFISH_PODMAN_RUN_ARGS='-p 127.0.0.1:8787:8787' target/taf-seurat-v6.0.0-r1 seurat-gadget --script gadget.R --bind 0.0.0.0
TAFFISH_CONTAINER_BACKEND=apptainer target/taf-seurat-v6.0.0-r1 seurat-gadget --script gadget.R --bind 127.0.0.1 --port 8787
```

The same localhost/SSH and trusted-script rules apply. This frontend boundary
does not change installed-wrapper usage. Killing only the outermost launcher
shell PID is not a supported service-manager stop contract.

## Optional and Online Boundaries

- Default `RunUMAP` uses R `uwot`. Explicit `umap-learn`, densMAP and
  graph-specific Python paths need a separate scientific Python environment.
  Python 3 here serves packaging helpers, not NumPy/SciPy/scikit-learn/UMAP;
  reticulate managed-environment auto-creation is disabled.
- Default `RunTSNE` uses Rtsne. `tsne.method = "FIt-SNE"` needs unbundled
  external `fast_tsne`; use the default R path.
- Signac and Azimuth are optional separate applications. A stored reference
  package does not install them or establish an end-to-end workflow.
- Symbol lookup (`UpdateSymbolList`, optional `AddModuleScore(search = TRUE)`),
  enrichment services and URL-based readers can require network and optional
  packages. They are not offline-local capabilities; use local inputs and
  default `search = FALSE` where appropriate.
- Specialized spatial/file formats can require additional upstream readers.
  Inspect the inventory; MEX/HDF5 smoke does not cover every optional format.

## Troubleshooting

- **Invalid resource root:** finish installation and run `verify`. An empty
  personal root can hide a complete site root; select the prepared root with
  `TAFFISH_SEURAT_RESOURCE_PATH` rather than silently accepting another version.
- **Dataset unavailable in R:** avoid `--vanilla`, confirm the member is
  installed and check capability/dependency status. Do not make a shared root
  writable by ordinary users as a workaround.
- **GUI never ready:** check the printed log tail, gadget call and free port.
  Docker/Podman need both host loopback publication and container `0.0.0.0`.
- **Output missing:** write to the mounted working directory, not `/tmp`, and
  execute exports after interactive completion.
- **High CPU or slow emulation:** set Seurat threads in the script and
  coordinate BLAS/future pools. Prefer native amd64 Linux for large jobs.
- **Special shell characters:** this is a shell-native wrapper, not an
  arbitrary-text serialization API. Put complex expressions and text in an R
  script or data file. With TAFFISH 0.11.0, avoid literal double quotes in the
  working-directory path; automatic working-directory binds do not reliably
  escape them. Shell-control characters can select a shell heredoc path, so a
  single shell-quoting pass does not guarantee that dollar signs stay literal.

## Testing

`seurat-check all` runs independent checks of the R runtime, tiny analysis,
threading, SCT, file IO, BPCells and standalone plotting. The manifest adds
scSLIDE methods, Atera counts/coordinates, lossless 8/16-bit JPEG2000 OME-TIFF
pyramids (every pixel in two channels/resolutions, crop and missing channel),
resource and GUI lifecycle tests. Full tests run outside Docker build; the
build itself checks identity/import and a tiny normalization only. These are
packaging checks, not scientific validation of a dataset.

## License and Citation

TAFFISH packaging/helpers: Apache-2.0. Seurat: MIT + file LICENSE. R, bundled
R/system packages and datasets keep their respective licenses; inventories
record package license metadata. RcppThread is retained from the fixed official library with
its license intact. Fixed-catalog datasets are CC BY 4.0 and require their
own attribution; no upstream scientific source or license text is patched.

Use `citation("Seurat")` in the running version. For the v5 methods cite Hao et al., *Dictionary learning for integrative,
multimodal and scalable single-cell analysis*, Nature Biotechnology (2023),
[DOI: 10.1038/s41587-023-01767-y](https://doi.org/10.1038/s41587-023-01767-y).
See [official installation guidance](https://satijalab.org/seurat/)
and method-specific upstream citation guidance for additional methods.
