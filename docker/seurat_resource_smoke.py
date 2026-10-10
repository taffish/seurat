#!/usr/bin/env python3
"""资源机制的离线tiny测试；synthetic catalog绝不冒充真实SeuratData资源。"""

import argparse
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
from unittest.mock import patch


MODULE_PATH = Path("/opt/seurat/seurat-resource.py")
if not MODULE_PATH.is_file():
    MODULE_PATH = Path(__file__).resolve().with_name("seurat-resource.py")
spec = importlib.util.spec_from_file_location("seurat_resource", MODULE_PATH)
resource = importlib.util.module_from_spec(spec)
spec.loader.exec_module(resource)


def rejected(call, message):
    try:
        call()
    except resource.ResourceError as exc:
        assert message in str(exc), str(exc)
    else:
        raise AssertionError("expected rejection: " + message)


def fixture(temporary, real_r_data=False):
    package = "fixture.SeuratData"
    archive = temporary / "fixture.tar.gz"
    contents = {
        "DESCRIPTION": "Package: fixture.SeuratData\nVersion: 1.0.0\nTitle: Tiny Offline Resource Fixture\nDescription: Synthetic resource fixture, not a published biological dataset.\nAuthors@R: person('TAFFISH', 'Maintainers', email='maintainer@example.invalid', role=c('aut','cre'))\nLicense: CC BY 4.0\nEncoding: UTF-8\n",
        "NAMESPACE": "export(resource_fixture)\n",
        "R/fixture.R": "resource_fixture <- function() data.frame(cell=c('a','b'), count=c(1L,2L))\n",
    }
    data_file = temporary / "fixture.rda"
    if real_r_data:
        result = subprocess.run(["Rscript", "--vanilla", "-e",
            "m <- matrix(c(1L,0L,2L,3L,1L,0L),nrow=3,dimnames=list(c('a','b','c'),c('cell1','cell2')));fixture <- SeuratObject::CreateSeuratObject(counts=m);save(fixture,file=commandArgs(TRUE)[1])",
            str(data_file)], cwd=temporary, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        assert result.returncode == 0, result.stdout
    with tarfile.open(archive, "w:gz") as output:
        for relative, value in contents.items():
            data = value.encode()
            info = tarfile.TarInfo(package + "/" + relative)
            info.size = len(data)
            info.mode = 0o644
            output.addfile(info, io.BytesIO(data))
        if real_r_data:
            data = data_file.read_bytes()
            info = tarfile.TarInfo(package + "/data/fixture.rda")
            info.size = len(data)
            info.mode = 0o644
            output.addfile(info, io.BytesIO(data))
    member = {"id": "fixture", "package": package, "version": "1.0.0", "license": "CC BY 4.0",
              "url": "https://seurat.nygenome.org/src/contrib/fixture.SeuratData_1.0.0.tar.gz",
              "md5": resource.digest(archive, "md5"), "bytes": archive.stat().st_size,
              "description": "Synthetic offline-only test resource",
              "record": "Package: fixture.SeuratData\nVersion: 1.0.0\nTitle: Tiny Offline Fixture\nLicense: CC BY 4.0\nNeedsCompilation: no\nDescription: species: synthetic\n        default.dataset: raw\n        other.datasets: fixture"}
    catalog = {"catalog": "synthetic-smoke-not-production", "members": resource.read_catalog()["members"] + [member]}
    return archive, member, catalog, contents


class Response:
    def __init__(self, data, url, offset=0, fail=False):
        self.data = io.BytesIO(data[offset:])
        self.url = url
        self.status = 206 if offset else 200
        self.headers = {"Content-Length": str(len(data) - offset), "Content-Range": f"bytes {offset}-{len(data)-1}/{len(data)}"}
        self.fail = fail
        self.reads = 0

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def geturl(self):
        return self.url

    def read(self, size):
        self.reads += 1
        if self.fail and self.reads > 1:
            raise urllib.error.URLError("synthetic connection interruption")
        return self.data.read(min(size, 100) if self.fail else size)


def run(unit=False):
    catalog = resource.read_catalog()
    assert len(catalog["members"]) == 24
    assert {m["license"] for m in catalog["members"]} == {"CC BY 4.0"}
    normalized_packages = resource.render_packages(catalog)
    assert "Description: species: human\n        system: adipose\n        ncells: 160075\n        tech: scRNA-seq and sNuc-seq" in normalized_packages
    bundled_packages = Path("/opt/seurat/resource-catalog/src/contrib/PACKAGES")
    if not bundled_packages.is_file():
        bundled_packages = MODULE_PATH.with_name("seurat-resource-PACKAGES")
    assert bundled_packages.read_text() == normalized_packages
    with tempfile.TemporaryDirectory(prefix="taf-seurat-resource-") as temp:
        temporary = Path(temp)
        assert stat.S_IMODE(temporary.stat().st_mode) == 0o700
        plan_root = temporary / "must not be created"
        command = [sys.executable, str(MODULE_PATH), "install", "--dataset", "pbmc3k@3.1.4", "--resource-root", str(plan_root), "--dry-run"]
        plan = subprocess.run(command, check=True, stdout=subprocess.PIPE, text=True)
        assert json.loads(plan.stdout)["members"][0]["license"] == "CC BY 4.0"
        assert not plan_root.exists()
        rejected(lambda: resource.choose(catalog, []), "explicit --dataset")
        rejected(lambda: resource.choose(catalog, ["pbmc3k@999"]), "unknown fixed")
        rejected(lambda: resource.choose(catalog, ["pbmcMultiome@0.1.4"]), "Signac >= 1.6.0")
        unsupported_root = temporary / "unsupported-must-not-exist"
        for dry_run in (True, False):
            rejected_command = [sys.executable, str(MODULE_PATH), "install", "--dataset", "pbmcMultiome@0.1.4", "--resource-root", str(unsupported_root)]
            if dry_run:
                rejected_command.append("--dry-run")
            blocked = subprocess.run(rejected_command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            assert blocked.returncode != 0 and "unsupported resource pbmcMultiome@0.1.4" in blocked.stdout
            assert "Signac >= 1.6.0" in blocked.stdout and not unsupported_root.exists()
        listed = subprocess.run([sys.executable, str(MODULE_PATH), "list"], check=True, stdout=subprocess.PIPE, text=True).stdout
        assert "pbmcMultiome@0.1.4\tunsupported" in listed
        assert "pbmcref@1.0.0\tstorage-only" in listed
        reference_plan = subprocess.run([sys.executable, str(MODULE_PATH), "install", "--dataset", "pbmcref@1.0.0", "--resource-root", str(plan_root), "--dry-run"], check=True, stdout=subprocess.PIPE, text=True)
        assert json.loads(reference_plan.stdout)["members"][0]["capability"]["status"] == "storage-only"
        assert not plan_root.exists()
        if not unit:
            raw_repository = temporary / "raw-repository/src/contrib"
            raw_repository.mkdir(parents=True)
            (raw_repository / "PACKAGES").write_text("\n\n".join(m["record"] for m in catalog["members"]) + "\n")
            positive_repository = temporary / "normalized-repository/src/contrib"
            positive_repository.mkdir(parents=True)
            (positive_repository / "PACKAGES").write_text(normalized_packages)
            catalog_probe = "options(SeuratData.repo.use=paste0('file://',commandArgs(TRUE)[1]),SeuratData.manifest.cache=FALSE);suppressPackageStartupMessages(library(SeuratData));stopifnot(nrow(SeuratData::AvailableData())==24L);cat('SEURATDATA_FIXED_CATALOG_ATTACH_PASS\\n')"
            broken_catalog = subprocess.run(["Rscript", "--vanilla", "-e", catalog_probe, str(raw_repository.parent.parent)], cwd=temporary, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            assert broken_catalog.returncode != 0 and "subscript out of bounds" in broken_catalog.stdout, broken_catalog.stdout
            fixed_catalog = subprocess.run(["Rscript", "--vanilla", "-e", catalog_probe, str(positive_repository.parent.parent)], cwd=temporary, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            assert fixed_catalog.returncode == 0 and "SEURATDATA_FIXED_CATALOG_ATTACH_PASS" in fixed_catalog.stdout, fixed_catalog.stdout
        archive, member, synthetic, contents = fixture(temporary, real_r_data=not unit)
        # 普通UID可能从不可遍历的镜像WORKDIR启动；R安装必须在自己的已创建library内运行。
        install_library = temporary / "explicit-install-cwd"
        install_library.mkdir()
        with patch.object(resource.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "")) as executed:
            resource.r_install(archive, install_library)
        assert executed.call_args.kwargs["cwd"] == str(install_library)
        malicious = temporary / "malicious.tar.gz"
        with tarfile.open(malicious, "w:gz") as output:
            info = tarfile.TarInfo("../escape")
            info.size = 1
            output.addfile(info, io.BytesIO(b"x"))
        rejected(lambda: resource.archive_space(malicious, member["package"]), "unsafe resource inventory path")
        data = archive.read_bytes()
        cache = temporary / "cache"
        cache.mkdir(mode=0o700)
        calls = []

        def interrupted(request, timeout):
            offset = int(request.get_header("Range", "bytes=0-").split("=")[1].split("-")[0])
            calls.append(offset)
            return Response(data, request.full_url, offset, fail=(len(calls) == 1))

        sleep = resource.time.sleep
        resource.time.sleep = lambda _: None
        try:
            cached = resource.download(member, cache, opener=interrupted)
        finally:
            resource.time.sleep = sleep
        assert calls == [0, 100], calls
        assert cached.read_bytes() == data
        resource.download(member, cache, opener=lambda *a, **k: (_ for _ in ()).throw(AssertionError("cached archive should not redownload")))
        cached.write_bytes(b"corrupt")
        rejected(lambda: resource.download(member, cache), "corrupt cached")
        resource.download(member, cache, force=True, opener=lambda request, timeout: Response(data, request.full_url))
        assert cached.read_bytes() == data
        root = temporary / "prepared root"
        downloads = []

        def downloader(selected, destination, force=False):
            downloads.append(selected["id"])
            return archive

        def fake_install(source, library):
            for relative, value in contents.items():
                target = library / member["package"] / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(value)

        installer = fake_install if unit else resource.r_install
        previous = os.umask(0o077)
        try:
            snapshot = resource.install(root, [member], synthetic, downloader=downloader, installer=installer)
            current = os.umask(0o077)
            assert current == 0o077, "installer must restore caller umask"
        finally:
            os.umask(previous)
        assert stat.S_IMODE(root.stat().st_mode) == 0o755
        assert stat.S_IMODE((root / ".download-cache").stat().st_mode) == 0o700
        for base, directories, files in os.walk(snapshot):
            assert stat.S_IMODE(Path(base).stat().st_mode) == 0o755
            for name in files:
                assert stat.S_IMODE((Path(base) / name).stat().st_mode) == 0o644
        resource.verify(root, synthetic)
        again = resource.install(root, [member], synthetic, downloader=downloader, installer=installer)
        assert snapshot == again and downloads == ["fixture"]
        rejected(lambda: resource.verify(root, catalog), "schema/catalog mismatch")
        with resource.install_lock(root):
            rejected(lambda: resource.install(root, [member], synthetic, downloader=downloader, installer=installer), "lock is busy")
        old = os.readlink(root / "current")

        def failing_install(source, library):
            raise resource.ResourceError("synthetic installation failure")

        rejected(lambda: resource.install(root, [member], synthetic, force=True, downloader=downloader, installer=failing_install), "synthetic installation failure")
        assert os.readlink(root / "current") == old
        assert not list((root / "snapshots").glob(".staging-*"))
        resource.verify(root, synthetic)
        description = snapshot / "library" / member["package"] / "DESCRIPTION"
        original = description.read_bytes()
        description.write_bytes(original + b"\nTampered: yes\n")
        rejected(lambda: resource.verify(root, synthetic), "checksum/inventory mismatch")
        description.write_bytes(original)
        (snapshot / "unexpected").write_text("foreign file")
        rejected(lambda: resource.verify(root, synthetic), "checksum/inventory mismatch")
        (snapshot / "unexpected").unlink()
        resource.verify(root, synthetic)
        sentinel = temporary / "sentinel"
        sentinel.write_text("untouched")
        (snapshot / "escape").symlink_to(sentinel)
        rejected(lambda: resource.verify(root, synthetic), "symlink")
        (snapshot / "escape").unlink()
        assert sentinel.read_text() == "untouched"
        description.write_bytes(original + b"\nBroken: yes\n")
        repaired = resource.install(root, [member], synthetic, force=True, downloader=downloader, installer=installer)
        assert repaired != snapshot and snapshot.exists(), "force repair retains the previous snapshot"
        resource.verify(root, synthetic)
        snapshot = repaired
        if not unit:
            env = os.environ.copy()
            env.update(R_PROFILE="/dev/null", R_PROFILE_USER="/dev/null", R_LIBS_USER=str(snapshot / "library"))
            checked = subprocess.run(["Rscript", "--vanilla", "-e", ".libPaths(c(commandArgs(TRUE)[1],.libPaths()));options(SeuratData.repo.use=paste0('file://',commandArgs(TRUE)[2]),SeuratData.manifest.cache=FALSE);suppressPackageStartupMessages(library(SeuratData));stopifnot(identical(fixture.SeuratData::resource_fixture()$count,c(1L,2L)));obj <- SeuratData::LoadData('fixture');stopifnot(inherits(obj,'Seurat'),nrow(obj)==3L,ncol(obj)==2L);bad <- tryCatch({SeuratData::LoadData('ifnb');FALSE},error=function(e) grepl('Cannot find dataset',conditionMessage(e),fixed=TRUE));stopifnot(bad);cat('SEURATDATA_REAL_LOAD_DATA_PASS\\n')", str(snapshot / "library"), str(snapshot / "catalog")], cwd=temporary, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            if checked.returncode:
                print(checked.stdout, file=sys.stderr)
                raise AssertionError("installed tiny resource R function failed")
            assert "SEURATDATA_REAL_LOAD_DATA_PASS" in checked.stdout, checked.stdout
        broken = temporary / "broken root"
        broken.mkdir()
        rejected(lambda: resource.verify(broken, synthetic), "no completed current snapshot")
    print("SEURAT_RESOURCE_SMOKE_PASS" + (" unit-only" if unit else " real-R-install"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--unit", action="store_true", help="local unit-only diagnosis without R; not the release runtime gate")
    run(unit=parser.parse_args().unit)
