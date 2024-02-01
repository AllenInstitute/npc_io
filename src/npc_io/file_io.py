"""
Tools for working with Open Ephys raw data files.
"""

from __future__ import annotations

import contextlib
import logging
import os
import pathlib
import shutil
import subprocess
from typing import Any, Literal, Union

import crc32c
import upath
from typing_extensions import TypeAlias

logger = logging.getLogger(__name__)

PathLike: TypeAlias = Union[str, bytes, os.PathLike, pathlib.Path, upath.UPath]


def from_pathlike(pathlike: PathLike) -> upath.UPath:
    """
    >>> from_pathlike('s3://aind-data-bucket/experiment2_Record Node 102#probeA.png')
    S3Path('s3://aind-data-bucket/experiment2_Record Node 102#probeA.png')

    >>> from_pathlike('s3://codeocean-s3datasetsbucket-1u41qdg42ur9/4797cab2-9ea2-4747-8d15-5ba064837c1c/postprocessed/experiment1_Record Node 102#Neuropix-PXI-100.ProbeA-AP_recording1/template_metrics/params.json')
    S3Path('s3://codeocean-s3datasetsbucket-1u41qdg42ur9/4797cab2-9ea2-4747-8d15-5ba064837c1c/postprocessed/experiment1_Record Node 102#Neuropix-PXI-100.ProbeA-AP_recording1/template_metrics/params.json')
    """
    if isinstance(pathlike, upath.UPath):
        return pathlike
    path: str = os.fsdecode(pathlike)
    # UPath will do rsplit('#')[0] on path
    if "#" in (p := pathlib.Path(path)).name:
        return upath.UPath(path).with_name(p.name)
    if "#" in p.parent.as_posix():
        if p.parent.as_posix().count("#") > 1:
            raise ValueError(
                f"Path {p} contains multiple '#' in a parent dirs, which we don't have a fix for yet"
            )
        for parent in p.parents:
            if "#" in parent.name:
                # we can't create or join the problematic `#`, so we have to 'discover' it
                new = upath.UPath(path).with_name(parent.name)
                for part in p.relative_to(parent).parts:
                    result = next(
                        new.glob(part),
                        None,
                    )  # we can't create or join the problem-#, so we have to 'discover' it
                    if result is None:
                        raise FileNotFoundError(
                            f"In attempting to handle a path containing '#', we couldn't find {path}"
                        )
                    new = result
                return new
    return upath.UPath(path)


def checksum(path: PathLike) -> str:
    path = from_pathlike(path)
    hasher = crc32c.crc32c

    def formatted(x) -> str:
        return f"{x:08X}"

    blocks_per_chunk = 4096
    multi_part_threshold_gb = 0.2
    if file_size(path) < multi_part_threshold_gb * 1024**3:
        return formatted(hasher(path.read_bytes()))
    hash = 0

    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(blocks_per_chunk), b""):
            hash = hasher(chunk, hash)
    checksum = formatted(hash)
    logger.debug(f"{hasher} checksum of {path}: {checksum}")
    return checksum


def checksums_match(*paths: PathLike) -> bool:
    checksums = tuple(checksum(p) for p in paths)
    return all(c == checksums[0] for c in checksums)


def copy(src: PathLike, dest: PathLike, max_attempts: int = 2) -> None:
    """Copy `src` to `dest` with checksum validation.

    - copies recursively if `src` is a directory
    - if dest already exists, checksums are compared, copying is skipped if they match
    - attempts to copy up to 3 times if checksums don't match
    - replaces existing symlinks with actual files
    - creates parent dirs if needed
    """
    src, dest = from_pathlike(src), from_pathlike(dest)

    if dest.exists() and dest.is_symlink():
        dest.unlink()  # we'll replace symlink with src file

    if src.is_dir():  # copy files recursively
        for path in src.iterdir():
            copy(path, dest / path.name)
        return

    if (
        not dest.suffix
    ):  # dest is a folder, but might not exist yet so can't use `is_dir`
        dest = dest / src.name
    dest.parent.mkdir(parents=True, exist_ok=True)

    if not dest.exists():
        shutil.copy2(src, dest)
        logger.debug(f"Copied {src} to {dest}")

    for _ in range(max_attempts):
        if checksums_match(src, dest):
            break
        shutil.copy2(src, dest)
    else:
        raise OSError(
            f"Failed to copy {src} to {dest} with checksum-validation after {max_attempts} attempts"
        )
    logger.debug(f"Copy of {src} at {dest} validated with checksum")


def move(src: PathLike, dest: PathLike, **rmtree_kwargs) -> None:
    """Copy `src` to `dest` with checksum validation, then delete `src`."""
    src, dest = from_pathlike(src), from_pathlike(dest)
    copy(src, dest)
    if src.is_dir():
        shutil.rmtree(src, **rmtree_kwargs)
    else:
        src.unlink()
    logger.debug(f"Deleted {src}")


def symlink(src: PathLike, dest: PathLike) -> None:
    """Create symlink at `dest` pointing to file at `src`.

    - creates symlinks recursively if `src` is a directory
    - creates parent dirs if needed (as folders, not symlinks)
    - skips if symlink already exists and points to `src`
    - replaces existing file or symlink pointing to a different location
    """
    src, dest = from_pathlike(src), from_pathlike(dest)
    if src.is_dir():
        for path in src.iterdir():
            symlink(src, dest / path.name)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_symlink() and dest.resolve() == src.resolve():
        logger.debug(f"Symlink already exists to {src} from {dest}")
        return
    with contextlib.suppress(FileNotFoundError):
        dest.unlink()
    with contextlib.suppress(FileExistsError):
        dest.symlink_to(src)
    logger.debug(f"Created symlink to {src} from {dest}")


def size(path: PathLike) -> int:
    """Return the size of a file or directory in bytes"""
    path = from_pathlike(path)
    return dir_size(path) if path.is_dir() else file_size(path)


def size_gb(path: PathLike) -> float:
    """Return the size of a file or directory in GB"""
    return round(size(path) / 1024**3, 1)


def ctime(path: PathLike) -> float:
    path = from_pathlike(path)
    with contextlib.suppress(AttributeError):
        return path.stat().st_ctime
    with contextlib.suppress(AttributeError):
        return path.stat()["LastModified"].timestamp()
    raise RuntimeError(f"Could not get size of {path}")


def file_size(path: PathLike) -> int:
    path = from_pathlike(path)
    with contextlib.suppress(AttributeError):
        return path.stat().st_size
    with contextlib.suppress(AttributeError):
        return path.stat()["size"]
    raise RuntimeError(f"Could not get size of {path}")


def dir_size(path: PathLike) -> int:
    """Return the size of a directory in bytes"""
    path = from_pathlike(path)
    if not path.is_dir():
        raise ValueError(f"{path} is not a directory")
    dir_size = 0
    dir_size += sum(file_size(f) for f in path.rglob("*") if f.is_file())
    return dir_size


def dir_size_gb(path: PathLike) -> float:
    """Return the size of a directory in GB"""
    return round(dir_size(path) / 1024**3, 1)


def free_gb(path: PathLike) -> float:
    "Return free space at `path`, to .1 GB. Raises FileNotFoundError if `path` not accessible."
    path = from_pathlike(path)
    return round(shutil.disk_usage(path).free / 1024**3, 1)

def run_and_save_notebook(
    notebook_path: PathLike,
    save_path: PathLike,
    env: dict[str, Any] | None = None,
    format: Literal["markdown", "notebook", "script", "html", "pdf"] = "notebook",
) -> upath.UPath:
    """Use jupyter nbconvert to run a specific notebook file in a subprocess,
    saving the output to a new file.

    - to pass parameters to the notebook, pass them here with the `env` dict, and load
      them from the `os.environ` dict in the notebook
    - `format` can be specified - available options are here:
      https://nbconvert.readthedocs.io/en/latest/usage.html#supported-output-formats
    """
    notebook_path = from_pathlike(notebook_path)
    assert (notebook_path).exists()
    save_path = from_pathlike(save_path)
    if save_path.is_dir():
        save_path.mkdir(exist_ok=True, parents=True)
        save_path = save_path / notebook_path.name

    subprocess.run(  # pragma: no cover
        f"jupyter nbconvert --to {format} --execute --allow-errors --output {save_path.as_posix()}  {notebook_path.as_posix()}",
        check=True,
        shell=True,
        capture_output=False,
        env=env,
    )  # pragma: no cover
    return save_path


if __name__ == "__main__":
    from npc_io import testmod

    testmod()
