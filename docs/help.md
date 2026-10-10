seurat 5.6.0-r1

Purpose:
  Run Seurat R scripts, export objects/tables/plots or standalone HTML, and
  open live Shiny gadgets. Your script chooses the analysis; default: Rscript.

Usage:
  taf-seurat Rscript analysis.R
  taf-seurat -- --help
  taf-seurat -- --version
  taf-seurat seurat-runtime-info
  Put complex R expressions in a script. For a script name with spaces:
  taf-seurat Rscript "'analysis with spaces.R'"

Inputs and outputs:
  Supply local matrices, 10x MEX/HDF5, RDS or BPCells paths in your script.
  Write RDS/TSV/PNG/PDF/HTML in a writable project directory; /tmp is temporary.

Choose a backend:
  TAFFISH_CONTAINER_BACKEND=docker taf-seurat Rscript analysis.R
  TAFFISH_CONTAINER_BACKEND=podman taf-seurat Rscript analysis.R
  TAFFISH_CONTAINER_BACKEND=apptainer taf-seurat Rscript analysis.R
  Native platform: amd64 Linux. Docker/Podman select amd64 automatically;
  an arm64 host needs engine-provided emulation. Apptainer needs amd64 Linux.

Export a standalone interactive plot:
  Save hover.R containing these R lines:
    library(Seurat); data("pbmc_small")
    htmlwidgets::saveWidget(HoverLocator(DimPlot(pbmc_small)), "hover.html", selfcontained = TRUE)
  taf-seurat Rscript hover.R
  Use any backend above; open hover.html in a browser. No service/port needed.

Install an optional dataset once:
  taf-seurat seurat-resource list
  SEURAT_RESOURCES="${XDG_DATA_HOME:-$HOME/.local/share}/taffish/resources/seurat/seurat-data-20261004"
  mkdir -p "$SEURAT_RESOURCES"
  Choose one command; append --dry-run to preview. Downloads need network.
  TAFFISH_CONTAINER_BACKEND=docker TAFFISH_SEURAT_RESOURCE_INSTALL_ROOT="$SEURAT_RESOURCES" taf-seurat seurat-resource install --dataset pbmc3k@3.1.4 --resource-root /resource-install
  TAFFISH_CONTAINER_BACKEND=podman TAFFISH_SEURAT_RESOURCE_INSTALL_ROOT="$SEURAT_RESOURCES" taf-seurat seurat-resource install --dataset pbmc3k@3.1.4 --resource-root /resource-install
  TAFFISH_CONTAINER_BACKEND=apptainer TAFFISH_SEURAT_RESOURCE_INSTALL_ROOT="$SEURAT_RESOURCES" taf-seurat seurat-resource install --dataset pbmc3k@3.1.4 --resource-root /resource-install
  Resource host paths must use letters, digits, _, ., /, + or - only.

Reuse prepared resources:
  taf-seurat seurat-resource verify --resource-root /opt/taffish-resources/seurat
  taf-seurat Rscript use-data.R
  In use-data.R: library(SeuratData); pbmc <- LoadData("pbmc3k")
  Normal Rscript enables the resource profile; --vanilla disables it.
  Personal roots above and administrator-prepared site roots are discovered
  read-only. Set TAFFISH_SEURAT_RESOURCE_PATH=/safe/prepared/root to override.
  Set TAFFISH_SEURAT_RESOURCE_AUTO_MOUNT=0 to disable discovery.
  Do not export TAFFISH_SEURAT_RESOURCE_INSTALL_ROOT during normal analysis.
  Manual reuse instead of auto-discovery (choose one; root already prepared):
  TAFFISH_CONTAINER_BACKEND=docker TAFFISH_SEURAT_RESOURCE_AUTO_MOUNT=0 TAFFISH_DOCKER_RUN_ARGS="-v $SEURAT_RESOURCES:/opt/taffish-resources/seurat:ro" taf-seurat Rscript use-data.R
  TAFFISH_CONTAINER_BACKEND=podman TAFFISH_SEURAT_RESOURCE_AUTO_MOUNT=0 TAFFISH_PODMAN_RUN_ARGS="-v $SEURAT_RESOURCES:/opt/taffish-resources/seurat:ro" taf-seurat Rscript use-data.R
  TAFFISH_CONTAINER_BACKEND=apptainer TAFFISH_SEURAT_RESOURCE_AUTO_MOUNT=0 TAFFISH_APPTAINER_RUN_ARGS="--bind $SEURAT_RESOURCES:/opt/taffish-resources/seurat:ro" taf-seurat Rscript use-data.R
  See README for administrator-once installation and ordinary-user reuse.
  No dataset or model is downloaded during normal startup.

Open an upstream browser gadget:
  Save gadget.R containing these R lines:
    library(Seurat)
    data("pbmc_small")
    IFeaturePlot(pbmc_small, feature = "MS4A1")
  Docker:
    TAFFISH_CONTAINER_BACKEND=docker TAFFISH_DOCKER_RUN_ARGS='-p 127.0.0.1:8787:8787' taf-seurat seurat-gadget --script gadget.R --bind 0.0.0.0
  Podman:
    TAFFISH_CONTAINER_BACKEND=podman TAFFISH_PODMAN_RUN_ARGS='-p 127.0.0.1:8787:8787' taf-seurat seurat-gadget --script gadget.R --bind 0.0.0.0
  Apptainer (amd64 Linux; no port mapping):
    TAFFISH_CONTAINER_BACKEND=apptainer taf-seurat seurat-gadget --script gadget.R --bind 127.0.0.1 --port 8787
  After ready, open http://127.0.0.1:8787/ and keep the terminal running.
  Remote server: ssh -N -L 8787:127.0.0.1:8787 user@server
  Then open the same local URL. No authentication/TLS: keep access private.
  Stop with Ctrl-C; closing a browser tab is not a reliable stop/save action.
  Save returned selections in your script after the gadget returns.
  Startup prints a private temporary log path; errors include its log tail.

Immediate notes:
  Trusted R scripts only; default R uwot UMAP and Rtsne need no Python.
  Python UMAP/densMAP, FIt-SNE, Signac and Azimuth are not bundled.
  Resource list explains member limits. Limit CPU with Seurat setThreads(1).

More help:
  taf-seurat seurat-resource --help
  taf-seurat seurat-gadget --help
  https://github.com/taffish/seurat and https://satijalab.org/seurat/

Wrapper options:
  taf-seurat --help       Show this installed-wrapper help.
  taf-seurat --version    Show TAFFISH wrapper version.
  taf-seurat --compile    Print the generated wrapper shell.
