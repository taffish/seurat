# 固定共享资源的只读R启动配置；不下载，不写缓存，不替用户选择数据集。
local({
  fail <- function(message) {
    cat(paste0("seurat-resource: ", message, "\n"), file = stderr())
    # R启动文件中的stop可能仅打印错误后继续；这里必须明确非零退出。
    quit(save = "no", status = 74L, runLast = FALSE)
  }
  root <- Sys.getenv("TAFFISH_SEURAT_RESOURCE_ROOT", unset = "")
  explicit <- nzchar(root)
  if (!explicit) root <- "/opt/taffish-resources/seurat"
  catalog <- "/opt/seurat/resource-catalog"
  if (dir.exists(root)) {
    helper <- Sys.which("seurat-resource")
    if (!nzchar(helper)) fail("resource verifier executable is missing")
    checked <- tryCatch(
      system2(helper, c("verify", "--resource-root", shQuote(root)), stdout = TRUE, stderr = TRUE),
      error = function(e) fail(conditionMessage(e))
    )
    status <- attr(checked, "status")
    if (!is.null(status) && status != 0L) fail(paste(checked, collapse = "\n"))
    current <- normalizePath(file.path(root, "current"), mustWork = TRUE)
    .libPaths(c(file.path(current, "library"), .libPaths()))
    # 经完整校验的snapshot只扩展数据library。始终使用同catalog身份的镜像metadata，
    # 避免旧prepared snapshot中上游纯文本PACKAGES的展示折行破坏SeuratData解析。
  } else if (explicit) {
    fail(paste("explicit prepared resource root is missing:", root))
  }
  packages <- file.path(catalog, "src", "contrib", "PACKAGES")
  if (!file.exists(packages)) fail("fixed local SeuratData catalog is missing")
  remote <- identical(Sys.getenv("TAFFISH_SEURAT_RESOURCE_ALLOW_NETWORK"), "1")
  repo <- if (remote) "https://seurat.nygenome.org/" else
    paste0("file://", utils::URLencode(normalizePath(catalog, mustWork = TRUE)))
  options(SeuratData.repo.use = repo, SeuratData.manifest.cache = FALSE)
})
