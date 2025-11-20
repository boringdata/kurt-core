from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional


class Storage:
    """Abstract storage interface."""

    def list_dir(self, root: Path, path: Path) -> List[Dict]:
        raise NotImplementedError()

    def read_file(self, path: Path) -> str:
        raise NotImplementedError()

    def write_file(self, path: Path, content: str) -> None:
        raise NotImplementedError()

    def exists(self, path: Path) -> bool:
        raise NotImplementedError()


class LocalStorage(Storage):
    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = Path(project_root or Path.cwd()).resolve()

    def _abs(self, path: Path) -> Path:
        p = (self.project_root / path).resolve()
        if self.project_root not in p.parents and p != self.project_root:
            raise ValueError("Path outside of project root")
        return p

    def list_dir(self, root: Path, path: Path) -> List[Dict]:
        base = self._abs(path)
        entries = []
        try:
            for child in sorted(base.iterdir()):
                entries.append(
                    {
                        "name": child.name,
                        "path": str(child.relative_to(self.project_root)),
                        "is_dir": child.is_dir(),
                    }
                )
        except FileNotFoundError:
            return []
        return entries

    def read_file(self, path: Path) -> str:
        p = self._abs(path)
        with open(p, "r", encoding="utf-8") as f:
            return f.read()

    def write_file(self, path: Path, content: str) -> None:
        p = self._abs(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(content)

    def exists(self, path: Path) -> bool:
        p = self._abs(path)
        return p.exists()


class S3Storage(Storage):
    def __init__(self, bucket: str, prefix: str = ""):
        try:
            import s3fs

            self.fs = s3fs.S3FileSystem(anon=False)
        except Exception as e:
            raise RuntimeError("s3fs is required for S3 storage: install s3fs") from e
        self.bucket = bucket
        self.prefix = prefix.strip("/")

    def _key(self, path: Path) -> str:
        key = "/".join(filter(None, [self.prefix, str(path).lstrip("/")]))
        return f"{self.bucket}/{key}" if key else self.bucket

    def list_dir(self, root: Path, path: Path) -> List[Dict]:
        base = str(path).lstrip("/")
        prefix = "/".join(filter(None, [self.prefix, base]))
        files = self.fs.ls(self.bucket + "/" + prefix) if prefix else self.fs.ls(self.bucket)
        entries = []
        for f in files:
            name = f.split("/")[-1]
            is_dir = f.endswith("/")
            entries.append({"name": name, "path": f, "is_dir": is_dir})
        return entries

    def read_file(self, path: Path) -> str:
        key = self._key(path)
        with self.fs.open(key, "r") as f:
            return f.read()

    def write_file(self, path: Path, content: str) -> None:
        key = self._key(path)
        with self.fs.open(key, "w") as f:
            f.write(content)

    def exists(self, path: Path) -> bool:
        try:
            key = self._key(path)
            return self.fs.exists(key)
        except Exception:
            return False
