#!/usr/bin/env python3
"""显式安装固定 SeuratData 成员；正常分析只读已完成的资源快照。"""

import argparse
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
import uuid

CATALOG_ID = "seurat-data-20261004"
CATALOG_SHA256 = "d7e5103be5bf79321ac591faa2ae6caa059676a787dc305a0ff1391129e3e928"
SCHEMA = "taffish.seurat.resources.v1"
RESERVE = 100 * 1024 * 1024
CATALOG_PATH = Path("/opt/seurat/seurat-resource-catalog.json")
if not CATALOG_PATH.is_file():
    CATALOG_PATH = Path(__file__).resolve().with_name("seurat-resource-catalog.json")


class ResourceError(Exception):
    pass


def digest(path, algorithm="sha256"):
    h = hashlib.new(algorithm)
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_catalog():
    if digest(CATALOG_PATH) != CATALOG_SHA256:
        raise ResourceError("bundled resource catalog checksum mismatch")
    return json.loads(CATALOG_PATH.read_text())


def render_packages(catalog):
    """保持固定身份/值；将上游展示折行恢复为SeuratData所需的逐行metadata。

    官方PACKAGES.rds保留Description中的逻辑换行；PACKAGES纯文本却按展示宽度
    折行。SeuratData按每行key:value解析，不能直接使用这种物理折行。本catalog的
    24成员只含下列固定metadata键，结果已逐项比对官方RDS，未改科学数据或依赖。
    """
    keys = r"seurat|species|system|ncells|tech|default\.dataset|disk\.datasets|other\.datasets|notes"
    records = []
    for member in catalog["members"]:
        lines = member["record"].splitlines()
        for start, line in enumerate(lines):
            if not line.startswith("Description: "):
                continue
            end = start + 1
            parts = [line[len("Description: "):].strip()]
            while end < len(lines) and lines[end].startswith((" ", "\t")):
                parts.append(lines[end].strip())
                end += 1
            description = " ".join(parts)
            fields = list(re.finditer(r"(?<!\S)(?:" + keys + r"):\s*", description))
            if not fields or fields[0].start() != 0:
                raise ResourceError(f"unrecognized fixed catalog Description: {member['id']}")
            logical = [description[field.start():fields[index + 1].start() if index + 1 < len(fields) else len(description)].strip()
                       for index, field in enumerate(fields)]
            lines[start:end] = ["Description: " + logical[0], *["        " + value for value in logical[1:]]]
            break
        records.append("\n".join(lines))
    return "\n\n".join(records) + "\n"


def default_root():
    data = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share")))
    return data / "taffish/resources/seurat" / CATALOG_ID


def regular(path):
    if not path.exists() or path.is_symlink() or not stat.S_ISREG(path.lstat().st_mode):
        raise ResourceError(f"resource file is missing, non-regular, or a symlink: {path}")


def safe_relative(value):
    p = Path(value)
    if p.is_absolute() or not p.parts or ".." in p.parts or "." in p.parts:
        raise ResourceError(f"unsafe resource inventory path: {value}")
    return p


def inventory(tree):
    result = {}
    for base, directories, files in os.walk(tree, followlinks=False):
        for name in directories:
            p = Path(base) / name
            if p.is_symlink():
                raise ResourceError(f"resource snapshot cannot contain symlinks: {p}")
        for name in files:
            p = Path(base) / name
            if p == tree / "manifest.json":
                continue
            regular(p)
            result[p.relative_to(tree).as_posix()] = {
                "bytes": p.stat().st_size,
                "sha256": digest(p),
            }
    return result


def current_snapshot(root):
    link = root / "current"
    if not link.is_symlink():
        raise ResourceError(f"resource root has no completed current snapshot: {root}")
    target = Path(os.readlink(link))
    if len(target.parts) != 2 or target.parts[0] != "snapshots" or not re.fullmatch(r"[0-9a-f]{32}", target.parts[1]):
        raise ResourceError("resource current link does not name a managed snapshot")
    if (root / "snapshots").is_symlink():
        raise ResourceError("resource snapshots directory must not be a symlink")
    snapshot = root / target
    if snapshot.is_symlink() or not snapshot.is_dir() or snapshot.resolve().parent != (root / "snapshots").resolve():
        raise ResourceError("invalid or missing resource snapshot")
    return snapshot


def verify(root, catalog=None):
    catalog = catalog or read_catalog()
    root = root.expanduser().resolve()
    snapshot = current_snapshot(root)
    return verify_snapshot(snapshot, catalog)


def verify_snapshot(snapshot, catalog):
    regular(snapshot / "manifest.json")
    receipt = json.loads((snapshot / "manifest.json").read_text())
    if receipt.get("schema") != SCHEMA or receipt.get("catalog") != catalog["catalog"]:
        raise ResourceError("resource manifest schema/catalog mismatch")
    if receipt.get("catalog_sha256") != CATALOG_SHA256:
        raise ResourceError("resource manifest belongs to a different catalog checksum")
    expected = {m["id"]: m for m in catalog["members"]}
    if not receipt.get("members"):
        raise ResourceError("empty resource member inventory")
    seen = set()
    for member in receipt["members"]:
        item = expected.get(member.get("id"))
        if not item or member["id"] in seen:
            raise ResourceError("unknown or duplicate resource member")
        for key in ("package", "version", "md5", "url", "license"):
            if member.get(key) != item[key]:
                raise ResourceError(f"resource member identity mismatch: {member['id']} {key}")
        if not re.fullmatch(r"[0-9a-f]{64}", member.get("archive_sha256", "")):
            raise ResourceError("resource archive SHA256 is missing")
        seen.add(member["id"])
        description = snapshot / "library" / member["package"] / "DESCRIPTION"
        regular(description)
        desc = description.read_text()
        if not re.search(r"(?m)^Package: " + re.escape(member["package"]) + r"\s*$", desc) or not re.search(r"(?m)^Version: " + re.escape(member["version"]) + r"\s*$", desc):
            raise ResourceError(f"installed R data-package identity mismatch: {member['id']}")
    recorded = receipt.get("inventory")
    if not isinstance(recorded, dict) or not recorded:
        raise ResourceError("resource file inventory is missing")
    for value in recorded:
        safe_relative(value)
    if inventory(snapshot) != recorded:
        raise ResourceError("resource snapshot checksum/inventory mismatch; choose a new root or use explicit --force reinstall")
    expected_packages = {x["package"] for x in receipt["members"]}
    if {p.name for p in (snapshot / "library").iterdir()} != expected_packages:
        raise ResourceError("resource library contains undeclared packages")
    return snapshot, receipt


def choose(catalog, selectors):
    choices = {member["id"]: member for member in catalog["members"]}
    selected = {}
    for selector in selectors:
        name, sep, version = selector.partition("@")
        name = name.removesuffix(".SeuratData")
        member = choices.get(name)
        if member is None or (sep and version != member["version"]):
            raise ResourceError(f"unknown fixed resource selector {selector!r}; use list for this catalog")
        selected[name] = member
    if not selected:
        raise ResourceError("at least one explicit --dataset ID[@VERSION] is required; there is no download-all default")
    assert_installable(selected.values())
    return list(selected.values())


def capability(member):
    """上游catalog保持原样；此处仅说明当前封装的实际软件依赖边界。"""
    if member["id"] == "pbmcMultiome":
        return {"status": "unsupported", "reason": "pbmcMultiome 0.1.4 requires Signac >= 1.6.0, which is not bundled in this Seurat app. Use a separately prepared Signac environment; no resource download was started."}
    if member.get("description", "").startswith("Azimuth Reference:"):
        return {"status": "storage-only", "reason": "Fixed reference resource installation/storage is available. Azimuth analysis and SeuratData::LoadData(type='azimuth') require the separately packaged Azimuth runtime; it is not bundled here. Raw-resource use is user-directed and not a claim of full Azimuth compatibility."}
    return {"status": "available", "reason": "Catalog mandatory package dependencies are included. Only representative resources are tested; dataset-specific scientific workflows are not all validated."}


def assert_installable(members):
    for member in members:
        surface = capability(member)
        if surface["status"] == "unsupported":
            raise ResourceError(f"unsupported resource {member['id']}@{member['version']}: {surface['reason']}")


def available_space(directory, required):
    free = shutil.disk_usage(directory).free
    if free < required:
        raise ResourceError(f"insufficient resource disk space: free={free}, required={required} bytes")


@contextlib.contextmanager
def install_lock(root):
    root.mkdir(parents=True, exist_ok=True)
    if not root.is_dir():
        raise ResourceError("resource root is not a directory")
    path = root / ".install.lock"
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode) or os.fstat(fd).st_uid != os.getuid():
            raise ResourceError("resource lock is not a regular file owned by this installer")
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ResourceError("resource install lock is busy; another installer is active") from exc
        yield
    finally:
        os.close(fd)


def download(member, cache, force=False, opener=urllib.request.urlopen):
    """只下载catalog的HTTPS来源；测试可注入本地响应，不放宽公开URL/checksum。"""
    name = f"{member['package']}_{member['version']}_{member['md5']}.tar.gz"
    completed = cache / name
    partial = cache / (name + ".part")
    for path in (completed, partial):
        if path.exists() or path.is_symlink():
            regular(path)
            if path.stat().st_uid != os.getuid():
                raise ResourceError("resource cache must be owned by this installer")
    if completed.exists():
        if digest(completed, "md5") == member["md5"]:
            return completed
        if not force:
            raise ResourceError("corrupt cached resource archive; --force explicitly discards this selected archive")
        completed.unlink()
    if force and partial.exists():
        partial.unlink()
    if not member["url"].startswith("https://seurat.nygenome.org/src/contrib/"):
        raise ResourceError("resource source is outside the fixed official HTTPS repository")
    available_space(cache, 5 * (member["bytes"] or RESERVE) + RESERVE)
    last_error = None
    for attempt in range(3):
        # HTTP在最后一个数据块后断开时，完整.part可直接校验复用，避免Range=EOF的416。
        if partial.exists() and digest(partial, "md5") == member["md5"]:
            os.replace(partial, completed)
            return completed
        offset = partial.stat().st_size if partial.exists() else 0
        request = urllib.request.Request(member["url"], headers={"User-Agent": "TAFFISH-Seurat-resource/5.6.0", **({"Range": f"bytes={offset}-"} if offset else {})})
        try:
            with opener(request, timeout=60) as response:
                if not response.geturl().startswith("https://seurat.nygenome.org/src/contrib/"):
                    raise ResourceError("resource download redirected outside the fixed official HTTPS repository")
                resumed = offset and response.status == 206
                if resumed and not response.headers.get("Content-Range", "").startswith(f"bytes {offset}-"):
                    raise ResourceError("resource resume response has the wrong byte range")
                if response.status not in (200, 206):
                    raise ResourceError(f"unexpected resource HTTP status {response.status}")
                length = response.headers.get("Content-Length")
                if length:
                    available_space(cache, 5 * (int(length) + (offset if resumed else 0)) + RESERVE)
                with partial.open("ab" if resumed else "wb") as output:
                    for chunk in iter(lambda: response.read(1024 * 1024), b""):
                        available_space(cache, RESERVE + len(chunk))
                        output.write(chunk)
                    output.flush()
                    os.fsync(output.fileno())
            if digest(partial, "md5") != member["md5"]:
                raise ResourceError("downloaded resource checksum mismatch; partial retained for diagnosis, use --force to restart")
            os.replace(partial, completed)
            return completed
        except ResourceError:
            raise
        except (OSError, urllib.error.URLError) as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(attempt + 1)
    raise ResourceError(f"resource download failed after 3 bounded attempts; resumable partial retained: {last_error}")


def archive_space(archive, package):
    """R安装前校验tar边界；数据包不得包含路径逃逸、symlink或设备。"""
    total = 0
    with tarfile.open(archive, "r:gz") as source:
        for member in source:
            p = safe_relative(member.name.rstrip("/"))
            if p.parts[0] != package or not (member.isdir() or member.isfile()):
                raise ResourceError(f"unsafe resource archive member: {member.name}")
            total += member.size
    return total


def r_install(archive, library):
    env = os.environ.copy()
    for key in list(env):
        if key.startswith("TAFFISH_SEURAT_RESOURCE"):
            del env[key]
    env.update(R_PROFILE="/dev/null", R_PROFILE_USER="/dev/null", R_ENVIRON_USER="/dev/null", R_LIBS_USER=str(library))
    result = subprocess.run(["R", "CMD", "INSTALL", "--no-test-load", "--library=" + str(library), str(archive)], cwd=str(library), env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if result.returncode:
        print(result.stdout[-16000:], file=sys.stderr)
        raise ResourceError(f"R resource package installation failed, exit={result.returncode}")


def normalize_permissions(tree):
    for base, directories, files in os.walk(tree, followlinks=False):
        os.chmod(base, 0o755)
        for name in directories:
            if (Path(base) / name).is_symlink():
                raise ResourceError("installed resource contains a directory symlink")
        for name in files:
            p = Path(base) / name
            regular(p)
            os.chmod(p, 0o644)


def install(root, members, catalog, force=False, downloader=download, installer=r_install):
    # 必须在resolve/mkdir/cache/lock/download之前执行，失败不能留下似已安装的目录。
    assert_installable(members)
    root = root.expanduser().resolve()
    if root == Path("/") or root == Path.home():
        raise ResourceError("use a dedicated resource root, not / or the home directory")
    original_umask = os.umask(0o022)
    stage = None
    new_link = None
    try:
        with install_lock(root):
            existing = []
            snapshot = None
            if (root / "current").exists() or (root / "current").is_symlink():
                # --force只能修复本helper管理的快照，不覆盖foreign文件或外链。
                current_snapshot(root)
                try:
                    snapshot, receipt = verify(root, catalog)
                    existing = receipt["members"]
                except (ResourceError, ValueError):
                    if not force:
                        raise
                    print("Explicit --force: rebuilding only requested members; old snapshots remain untouched.", file=sys.stderr)
            by_id = {m["id"]: m for m in existing}
            requested = {m["id"] for m in members}
            if snapshot and requested <= set(by_id) and not force:
                print("Resource installation already complete; checksums verified; no download.")
                return snapshot
            cache = root / ".download-cache"
            if cache.is_symlink():
                raise ResourceError("resource cache must not be a symlink")
            cache.mkdir(mode=0o700, exist_ok=True)
            if cache.stat().st_uid != os.getuid() or stat.S_IMODE(cache.stat().st_mode) != 0o700:
                raise ResourceError("resource cache must be private mode 0700 and owned by installer")
            revisions = root / "snapshots"
            if revisions.is_symlink():
                raise ResourceError("resource snapshots directory must not be a symlink")
            revisions.mkdir(mode=0o755, exist_ok=True)
            stage = Path(tempfile.mkdtemp(prefix=".staging-", dir=revisions))
            library = stage / "library"
            if snapshot:
                size = sum(x["bytes"] for x in receipt["inventory"].values())
                available_space(root, size + RESERVE)
                shutil.copytree(snapshot / "library", library)
            else:
                library.mkdir()
            for member in members:
                if member["id"] in by_id and not force:
                    continue
                archive = downloader(member, cache, force=force)
                available_space(root, 2 * archive_space(archive, member["package"]) + RESERVE)
                destination = library / member["package"]
                if destination.exists():
                    shutil.rmtree(destination)
                installer(archive, library)
                by_id[member["id"]] = {k: member[k] for k in ("id", "package", "version", "license", "md5", "url")}
                by_id[member["id"]].update(archive_sha256=digest(archive), archive_bytes=archive.stat().st_size)
            repo = stage / "catalog/src/contrib"
            repo.mkdir(parents=True)
            (repo / "PACKAGES").write_text(render_packages(catalog))
            (stage / "ATTRIBUTION.txt").write_text(
                "SeuratData resources from https://seurat.nygenome.org/\n"
                "Dataset license: CC BY 4.0, https://creativecommons.org/licenses/by/4.0/\n"
                "Original package metadata, data documentation and citation are retained in library/.\n"
                "Installation repackages data without changing its scientific content. Cite each dataset.\n"
            )
            normalize_permissions(stage)
            receipt = {"schema": SCHEMA, "catalog": catalog["catalog"], "catalog_sha256": CATALOG_SHA256,
                       "members": sorted(by_id.values(), key=lambda m: m["id"]), "inventory": inventory(stage)}
            (stage / "manifest.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
            os.chmod(stage / "manifest.json", 0o644)
            verify_snapshot(stage, catalog)
            final = revisions / uuid.uuid4().hex
            os.rename(stage, final)
            stage = None
            new_link = root / (".current-" + uuid.uuid4().hex)
            new_link.symlink_to(final.relative_to(root))
            os.replace(new_link, root / "current")
            new_link = None
            verified, _ = verify(root, catalog)
            print(f"Resource installation complete: {verified}")
            return verified
    finally:
        if new_link is not None and new_link.is_symlink():
            new_link.unlink()
        if stage is not None and stage.is_dir():
            shutil.rmtree(stage)
        os.umask(original_umask)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Install explicitly selected fixed SeuratData datasets into a personal/site shared root. No datasets are bundled or selected by default.")
    parser.add_argument("action", choices=("list", "install", "verify", "clear-cache"))
    parser.add_argument("--dataset", action="append", default=[], help="explicit catalog member ID[@VERSION], repeatable")
    parser.add_argument("--resource-root", type=Path, default=default_root(), help="persistent host-bound root; default personal XDG data directory")
    parser.add_argument("--dry-run", action="store_true", help="print the offline installation plan without creating directories/downloading")
    parser.add_argument("--force", action="store_true", help="explicitly reinstall selected members/restart corrupt selected archives; old snapshots are retained")
    args = parser.parse_args(argv)
    try:
        catalog = read_catalog()
        if args.action == "list":
            if args.dataset or args.force:
                parser.error("list does not accept --dataset/--force")
            print(json.dumps({k: catalog[k] for k in ("catalog", "source", "license_url", "size_note")}, indent=2))
            for m in catalog["members"]:
                surface = capability(m)
                print(f"{m['id']}@{m['version']}\t{surface['status']}\t{m['license']}\t{m['bytes'] if m['bytes'] is not None else 'unknown'} bytes\t{m['description']}\t{surface['reason']}")
        elif args.action == "verify":
            if args.dataset or args.dry_run or args.force:
                parser.error("verify accepts only --resource-root")
            snapshot, receipt = verify(args.resource_root, catalog)
            print(json.dumps({"status": "verified", "snapshot": str(snapshot), "members": [m["id"] for m in receipt["members"]]}, sort_keys=True))
        elif args.action == "install":
            members = choose(catalog, args.dataset)
            if args.dry_run:
                plan = {"catalog": catalog["catalog"], "catalog_sha256": CATALOG_SHA256,
                        "resource_root": str(args.resource_root.expanduser().absolute()), "members": [{**{k: m[k] for k in ("id", "version", "url", "md5", "license", "bytes")}, "capability": capability(m)} for m in members],
                        "size_policy": catalog["size_note"], "license_url": catalog["license_url"],
                        "integrity": "Frozen catalog SHA256; official archive MD5 over HTTPS; downloaded SHA256 and installed-tree SHA256 in receipt.",
                        "retention": "Private resumable cache and prior complete snapshots are retained. clear-cache removes only owned regular cache files under this root.",
                        "network": "Only explicit install downloads; normal analysis uses the local read-only catalog/library."}
                print(json.dumps(plan, indent=2))
            else:
                print(f"Persistent resource destination: {args.resource_root}. In a container, use an actual writable host bind.", file=sys.stderr)
                install(args.resource_root, members, catalog, force=args.force)
        else:
            if args.dataset or args.force:
                parser.error("clear-cache does not accept --dataset/--force")
            root = args.resource_root.expanduser().resolve()
            verify(root, catalog)
            with install_lock(root):
                cache = root / ".download-cache"
                if cache.is_symlink() or not cache.is_dir() or cache.stat().st_uid != os.getuid():
                    raise ResourceError("cache must be an owned non-symlink directory")
                files = list(cache.iterdir())
                for item in files:
                    regular(item)
                    if item.stat().st_uid != os.getuid() or not re.fullmatch(r"[A-Za-z0-9.]+_[0-9.]+_[0-9a-f]{32}\.tar\.gz(?:\.part)?", item.name):
                        raise ResourceError("unrecognized cache entry; refusing cleanup")
                for item in files:
                    if not args.dry_run:
                        item.unlink()
                    print(("Would remove " if args.dry_run else "Removed ") + str(item))
        return 0
    except (ResourceError, OSError, ValueError, tarfile.TarError) as exc:
        print(f"seurat-resource: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
