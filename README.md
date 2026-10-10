# seurat

`seurat` packages [Seurat](https://satijalab.org/seurat/) 5.6.0 for TAFFISH:
an R runtime for single-cell analysis, with upstream browser gadgets and
explicitly installed, reusable SeuratData datasets.

Package identity:

- name: `seurat`; command: `taf-seurat`; kind: `tool`
- TAFFISH version: `5.6.0-r1`
- image: `ghcr.io/taffish/seurat:5.6.0-r1`
- default command: `Rscript`; automatic command mode: enabled
- native platform: `linux/amd64`
- packaging license: Apache-2.0; upstream Seurat: MIT + file LICENSE

## What This App Packages

The app preserves the general upstream R API, rather than adding a fixed
analysis pipeline. Your script chooses the input, parameters and outputs.
It includes a foreground launcher for Seurat's own Shiny gadgets; RStudio
Server is neither needed nor included.

[Seurat 5.6.0](https://github.com/satijalab/seurat/releases/tag/v5.6.0)
expands C++ threading, exposed through `setThreads()` and `getThreads()`,
across normalization, variable-feature selection, scaling, PCA, neighbor and
clustering paths. It also fixes several BPCells, SCT residual and plotting
paths. This package does not change those scientific implementations or
promise identical floating-point results across thread counts, architectures
or older upstream versions.

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

This release uses a minimal source overlay instead of waiting for an official
Seurat 5.6.0 image. It retains the R package library from the immutable official
5.5.1 image, then compiles unmodified CRAN Seurat 5.6.0 and the newly required
RcppThread dependency. Other R packages are not broadly upgraded: existing
`uwot` 0.2.4 already satisfies Seurat 5.6.0.

| Component | Fixed source or runtime identity |
| --- | --- |
| Official R library baseline | `satijalab/seurat:5.5.1@sha256:048d965487afc2961c450879692281a73e24f6de47360ed2f11b31112ebd844e` |
| Runtime base | `rocker/r-ver:4.5.2@sha256:fd4ccdd3a4a6f7ef805e2daeee2a0fe3bf126bc231f36351223baecf5a595a4c` |
| R / SeuratObject | 4.5.2 / 5.4.0 |
| Seurat source | `Seurat_5.6.0.tar.gz`; SHA256 `8366190e8fe26e79efc18be5391308ff00cde673d298bc7b39e7a84816718f39` |
| RcppThread source | `RcppThread_2.4.0.tar.gz`; SHA256 `29e8955a0e1cad0775bcb6f29bde76f34cc2e1fa9c5f5d5d8d4962b91c3feaeb` |
| Preserved numerical dependencies | `uwot` 0.2.4; `RSpectra` 0.16.2 |

The source downloads use CRAN's versioned source paths and Archive fallback
with the same mandatory SHA256 checks. The build verifies the old library's
R/package identities first. Retaining R 4.5.2 preserves the baseline ABI;
this does not make arbitrary R-version libraries interchangeable. No upstream
scientific source or license text is patched.

Base images, source archives and the retained R library are fixed as above.
Ubuntu runtime packages are resolved from the distribution repository during
the build and inventoried; they are not all individually version-pinned.

Compiler dependencies stay in the build stage. Build-only R package headers
are removed after compilation and their removal is inventoried; R help,
vignettes, runtime data, JavaScript assets and fonts are retained. This is a
runtime image, not a development environment for compiling new R extensions.
Any dependency extension requires a separately built, validated image.

The final native amd64 candidate's Docker inspect size is 3,058,921,212 bytes
(about 2.849 GiB); the corresponding compressed SIF is 1,103,884,288 bytes
(about 1.028 GiB). These include the retained broad upstream R library, not
downloaded SeuratData datasets. Size/history and the installed tree were
inspected after cleanup; runtime data, plotting assets and licenses remain.

Packaged commands and paths:

- `R`, `Rscript`: R runtime; `seurat-runtime-info`: selected package versions.
- `seurat-resource`: selected fixed dataset installation and verification.
- `seurat-gadget`: foreground supervisor for a trusted upstream gadget script.
- `seurat-check`: independent offline packaging checks, not an analysis pipeline.
- `/opt/seurat/share/provenance/`: source checksums/URLs, before/after R package
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
| CLI and static plots | Wrapper selects amd64 | Wrapper selects amd64 | Native amd64 Linux | Native amd64 wrapper and persistent outputs validated on all three; maintainer confirmed local HTML rendering, hover and toolbar |
| Prepared resources | Automatic read-only volume | Automatic read-only volume | Automatic read-only bind | Same fixed inventory; installation is separate |
| Resource installation | Existing host root mounted at `/resource-install` read-write | Same, with user namespace mapping | Existing host root bound read-write | Explicit helper operation, not normal analysis |
| Browser gadget | Loopback host publication; container binds `0.0.0.0` | Same | Shared-network loopback; no port mapping | Commands below; no authentication/TLS |
| Native arm64 | Not provided | Not provided | Not provided | The retained official binary library is amd64 |

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

Choose species, tissue, modality and version explicitly. Complete-member
installation/loading and read-only sharing passed for `pbmc3k@3.1.4` on
all three backends, within the sharing-mechanism boundaries detailed under
Testing. No full-family validation or actual system-directory deployment is
claimed.

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
The final native amd64 candidate passed real-wrapper lifecycle and browser
interaction checks on all three backends: feature changes, Done completion,
PNG/RDS output, early/ready Ctrl-C, TERM and owned-process cleanup. Apptainer
TERM was tested through its non-TTY attached runtime client; interactive
terminal shutdown uses Ctrl-C. Sending TERM only to a foreground TTY
Apptainer client is not the same signal-forwarding contract.

### Development entrypoint

For a short standalone HTML export, save the `hover.R` example from
[`docs/help.md`](docs/help.md) in this source checkout and run:

```sh
taf run -b docker -- Rscript hover.R
```

This short generator passed on native amd64 Linux with the candidate image,
network disabled and a read-only container root; `hover.html` persists in
the working directory. Podman/Apptainer short `taf run` invocations were not
separately validated; installed/generated-wrapper HTML export passed on all
three backends. This is distinct from the long-running service below.

With TAFFISH 0.11.0, `taf run` buffers the long-running GUI's output instead
of reliably showing the startup card immediately. It is not a supported
foreground GUI entrypoint for this release. From this app's source directory,
build first and use the generated wrapper (with `gadget.R` in that directory):

```sh
taf build
TAFFISH_CONTAINER_BACKEND=docker TAFFISH_DOCKER_RUN_ARGS='-p 127.0.0.1:8787:8787' target/taf-seurat-v5.6.0-r1 seurat-gadget --script gadget.R --bind 0.0.0.0
TAFFISH_CONTAINER_BACKEND=podman TAFFISH_PODMAN_RUN_ARGS='-p 127.0.0.1:8787:8787' target/taf-seurat-v5.6.0-r1 seurat-gadget --script gadget.R --bind 0.0.0.0
TAFFISH_CONTAINER_BACKEND=apptainer target/taf-seurat-v5.6.0-r1 seurat-gadget --script gadget.R --bind 127.0.0.1 --port 8787
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

The final 5.6.0-r1 source candidate was built from the app-root context on
native amd64 Linux and tested on Docker 26.1.5, Podman 5.4.2 and Apptainer
1.5.3. The automated packaging checks below passed. On 2026-10-04 the
maintainer also confirmed local-file HTML rendering, hover and toolbar
behavior. The short-running Docker `taf run` HTML generator and the updated
wrapper help/version/compile checks also passed. This is not a publication
claim or a claim of full scientific validation.

- Build-time version/import/tiny normalization only; full plotting/GUI is
  runtime validation, not a strict image-build assertion.
- Independent offline identity/modules, workflow, threading, SCT/PCA,
  BPCells, plain/gzip MEX/HDF5, standalone HoverLocator HTML and negative checks.
- Fresh direct manifest probes on Docker/Podman read-only roots and a real
  read-only Apptainer SIF, without production binds or wrapper substitution.
- Real generated-wrapper metadata/command/argument checks, immutable inputs
  and actual-bind persistent PNG/PDF/RDS/TSV/HTML outputs.
- Resource install/inventory/negative cases, selected complete-member loading
  and ordinary-user read-only sharing.
- Real upstream gadget/browser interaction and startup/ready Ctrl-C/TERM,
  failure, timeout and occupied-port cases on the relevant backends.
- Final root-context native amd64 build, dependency closure, image size
  profile, canonical Action identity, dry-run and final target cleanup.

The exact manifest matrix passed 155 fresh/offline probes: 31 each on Docker
normal/read-only, Podman normal/read-only and a real read-only SIF built from
the same OCI candidate. All three generated-wrapper suites passed 17 core
checks each. Dynamic-library auditing covered 241 ELF files; RcppParallel's
private loader path was verified in a fresh R process rather than mistaken
for a missing system library.

The full selected `pbmc3k@3.1.4` member was installed through each real
wrapper's writable host bind, reinstalled idempotently, verified and loaded
read-only. Docker/Podman additionally loaded it as a distinct container UID
65534 without accessing the installer's private cache/lock. Apptainer used
the real ordinary host user. These are sharing-mechanism tests, not a claim
that `/usr/local/share` was provisioned on the test server or that every
catalog member has been scientifically validated.

The fixed SeuratData catalog preserves each Description metadata field on a
logical line. R always reads catalog metadata from the image and dataset
libraries from the verified prepared root; old prepared data can be reused
without rewriting it merely to repair metadata formatting.

Native arm64 is not declared; amd64 emulation is a separate evidence axis.
No backend exception is claimed here. The standalone HoverLocator HTML was
generated through all three wrappers; structural checks found embedded
runtime assets and no external runtime tag references. The automation
browser could not open local `file://` URLs, so local-file rendering, hover
and toolbar acceptance comes from the maintainer's 2026-10-04 confirmation.
That confirmation does not claim a disconnected-network reload or automated
browser console/network capture. Packaging tests do not replace production
scientific validation or user confirmation of new interactive results.

## License and Citation

TAFFISH packaging/helpers: Apache-2.0. Seurat: MIT + file LICENSE. R, bundled
R/system packages and datasets keep their respective licenses; inventories
record package license metadata. RcppThread uses original CRAN source with
its license intact. Fixed-catalog datasets are CC BY 4.0 and require their
own attribution; no upstream scientific source or license text is patched.

For Seurat v5 cite Hao et al., *Dictionary learning for integrative,
multimodal and scalable single-cell analysis*, Nature Biotechnology (2023),
[DOI: 10.1038/s41587-023-01767-y](https://doi.org/10.1038/s41587-023-01767-y).
See [official installation guidance](https://satijalab.org/seurat/articles/install_v5.html)
and method-specific upstream citation guidance for additional methods.
