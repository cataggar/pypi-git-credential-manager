#!/usr/bin/env python3
"""Download GCM release assets and repackage them as Python wheels."""

# /// script
# requires-python = ">=3.12"
# dependencies = ["requests"]
# ///

import hashlib
import io
import stat
import sys
import tarfile
import tempfile
import zipfile
from base64 import urlsafe_b64encode
from pathlib import Path

import requests  # type: ignore[import-untyped]

IMPORT_NAME = "git_credential_manager"
DIST_NAME = "git_credential_manager"
GCM_REPO = "git-ecosystem/git-credential-manager"

PLATFORMS = {
    "gcm-linux-x64": {
        "ext": ".tar.gz",
        "tag": "manylinux_2_17_x86_64.manylinux2014_x86_64",
        "binary": "git-credential-manager",
    },
    "gcm-linux-arm64": {
        "ext": ".tar.gz",
        "tag": "manylinux_2_17_aarch64.manylinux2014_aarch64",
        "binary": "git-credential-manager",
    },
    "gcm-osx-x64": {
        "ext": ".tar.gz",
        "tag": "macosx_10_15_x86_64",
        "binary": "git-credential-manager",
    },
    "gcm-osx-arm64": {
        "ext": ".tar.gz",
        "tag": "macosx_11_0_arm64",
        "binary": "git-credential-manager",
    },
    "gcm-win-x64": {
        "ext": ".zip",
        "tag": "win_amd64",
        "binary": "git-credential-manager.exe",
    },
    "gcm-win-arm64": {
        "ext": ".zip",
        "tag": "win_arm64",
        "binary": "git-credential-manager.exe",
    },
    "gcm-win-x86": {
        "ext": ".zip",
        "tag": "win32",
        "binary": "git-credential-manager.exe",
    },
}


def sha256_digest(data: bytes) -> str:
    """Return url-safe base64 sha256 digest (no padding)."""
    return urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()


def download_asset(version: str, platform_key: str, ext: str) -> bytes:
    """Download a GCM release asset."""
    asset_name = f"{platform_key}-{version}{ext}"
    url = f"https://github.com/{GCM_REPO}/releases/download/v{version}/{asset_name}"
    print(f"  Downloading {asset_name} ...")
    resp = requests.get(url, allow_redirects=True, timeout=300)
    resp.raise_for_status()
    return resp.content


def extract_archive(data: bytes, ext: str, dest: Path) -> Path:
    """Extract archive and return the directory containing the files."""
    if ext == ".tar.gz":
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tf:
            tf.extractall(dest, filter="data")
    elif ext == ".zip":
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            zf.extractall(dest)

    # If archive has a single top-level directory, use that
    items = list(dest.iterdir())
    if len(items) == 1 and items[0].is_dir():
        return items[0]
    return dest


def _is_executable(path: Path, binary_name: str) -> bool:
    """Check if a file should be marked executable in the wheel."""
    name = path.name
    if name == binary_name:
        return True
    # Shared libraries and executables without extensions
    if name.endswith((".so", ".dylib")) or "." not in name:
        return True
    return False


_EXEC_ATTR = (
    stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH
) << 16
_FILE_ATTR = (stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH) << 16


def build_wheel(version: str, platform_key: str, info: dict[str, str], dist_dir: Path) -> Path:
    """Build a single platform wheel."""
    ext = info["ext"]
    platform_tag = info["tag"]
    binary_name = info["binary"]

    data = download_asset(version, platform_key, ext)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Extract archive
        source_dir = extract_archive(data, ext, tmpdir / "extracted")

        # Collect wheel entries: (arcname, data_bytes, is_executable)
        entries: list[tuple[str, bytes, bool]] = []

        # Add __init__.py
        init_py = Path(__file__).resolve().parent.parent / "python" / IMPORT_NAME / "__init__.py"
        entries.append(
            (f"{IMPORT_NAME}/__init__.py", init_py.read_bytes(), False)
        )

        # Add all files from the extracted archive
        for fpath in sorted(source_dir.rglob("*")):
            if not fpath.is_file():
                continue
            rel = fpath.relative_to(source_dir).as_posix()
            arcname = f"{IMPORT_NAME}/{rel}"
            executable = _is_executable(fpath, binary_name)
            entries.append((arcname, fpath.read_bytes(), executable))

        # dist-info directory
        dist_info_dir = f"{DIST_NAME}-{version}.dist-info"

        readme_path = Path(__file__).resolve().parent.parent / "README.md"
        readme_text = readme_path.read_text(encoding="utf-8")

        metadata = (
            f"Metadata-Version: 2.4\n"
            f"Name: git-credential-manager\n"
            f"Version: {version}\n"
            f"Summary: Git Credential Manager repackaged as Python wheels\n"
            f"Home-page: https://github.com/git-ecosystem/git-credential-manager\n"
            f"License: MIT\n"
            f"Requires-Python: >=3.9\n"
            f"Description-Content-Type: text/markdown\n"
            f"\n"
            f"{readme_text}"
        )
        entries.append((f"{dist_info_dir}/METADATA", metadata.encode(), False))

        wheel_meta = (
            f"Wheel-Version: 1.0\n"
            f"Generator: build_wheels.py\n"
            f"Root-Is-Purelib: false\n"
            f"Tag: py3-none-{platform_tag}\n"
        )
        entries.append((f"{dist_info_dir}/WHEEL", wheel_meta.encode(), False))

        entry_points = f"[console_scripts]\ngit-credential-manager = {IMPORT_NAME}:main\n"
        entries.append(
            (f"{dist_info_dir}/entry_points.txt", entry_points.encode(), False)
        )

        # Build RECORD
        records: list[str] = []
        for arcname, file_data, _ in entries:
            digest = sha256_digest(file_data)
            records.append(f"{arcname},sha256={digest},{len(file_data)}")
        records.append(f"{dist_info_dir}/RECORD,,")
        record_data = ("\n".join(records) + "\n").encode()
        entries.append((f"{dist_info_dir}/RECORD", record_data, False))

        # Write wheel zip
        wheel_name = f"{DIST_NAME}-{version}-py3-none-{platform_tag}.whl"
        wheel_path = dist_dir / wheel_name
        with zipfile.ZipFile(wheel_path, "w", zipfile.ZIP_DEFLATED) as whl:
            for arcname, file_data, executable in entries:
                zi = zipfile.ZipInfo(arcname)
                zi.compress_type = zipfile.ZIP_DEFLATED
                zi.external_attr = _EXEC_ATTR if executable else _FILE_ATTR
                whl.writestr(zi, file_data)

        print(f"  Built {wheel_name} ({wheel_path.stat().st_size / 1024 / 1024:.1f} MB)")
        return wheel_path


def main() -> None:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <version>")
        print(f"Example: {sys.argv[0]} 2.7.3")
        sys.exit(1)

    version = sys.argv[1]
    dist_dir = Path("dist")
    dist_dir.mkdir(exist_ok=True)

    print(f"Building wheels for GCM v{version}\n")

    wheels: list[Path] = []
    for platform_key, info in PLATFORMS.items():
        print(f"[{platform_key}]")
        wheel = build_wheel(version, platform_key, info, dist_dir)
        wheels.append(wheel)
        print()

    print(f"Done! {len(wheels)} wheels in {dist_dir}/")
    for w in wheels:
        print(f"  {w.name}")


if __name__ == "__main__":
    main()
