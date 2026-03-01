"""
GCS Handler — Google Cloud Storage persistence for FAISS vectorstore.

Handles upload/download of the FAISS index files (index.faiss + index.pkl)
to/from a GCS bucket. Gracefully no-ops when GCS is not configured so
local development works without any GCP credentials.

Authentication:
  - Cloud Run: automatic via instance metadata (no key file needed)
  - Local dev: run `gcloud auth application-default login` once
"""

import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional

from ..utils.logger import get_logger

logger = get_logger(__name__)

# FAISS index files that must be uploaded/downloaded together
FAISS_FILES = ["index.faiss", "index.pkl"]


class GCSHandler:
    """
    Manages FAISS vectorstore persistence via Google Cloud Storage.

    Usage:
        handler = GCSHandler()          # reads GCS_BUCKET_NAME from env
        if handler.gcs_enabled:
            handler.download_faiss_index("vectorstore/db_faiss")
            ...build/update index locally...
            handler.upload_faiss_index("vectorstore/db_faiss")
    """

    def __init__(
        self,
        bucket_name: Optional[str] = None,
        index_prefix: str = "faiss-index",
    ):
        """
        Initialize GCS handler.

        Args:
            bucket_name: GCS bucket name. Reads GCS_BUCKET_NAME env var if None.
            index_prefix: Folder prefix inside the bucket for index files.
        """
        self.bucket_name = bucket_name or os.getenv("GCS_BUCKET_NAME", "")
        self.index_prefix = index_prefix.rstrip("/")
        self._client = None
        self._bucket = None

        if self.gcs_enabled:
            logger.info(
                f"GCSHandler initialized — bucket: {self.bucket_name}, "
                f"prefix: {self.index_prefix}"
            )
        else:
            logger.info(
                "GCSHandler: GCS_BUCKET_NAME not set — running in local-only mode"
            )

    @property
    def gcs_enabled(self) -> bool:
        """True when a bucket name is configured."""
        return bool(self.bucket_name)

    def _get_bucket(self):
        """Lazy-initialise GCS client and bucket (avoids import cost when GCS disabled)."""
        if self._bucket is not None:
            return self._bucket

        try:
            from google.cloud import storage  # noqa: PLC0415

            self._client = storage.Client()
            self._bucket = self._client.bucket(self.bucket_name)
            return self._bucket
        except ImportError:
            raise RuntimeError(
                "google-cloud-storage is not installed. "
                "Run: uv add google-cloud-storage"
            )
        except Exception as e:
            # Catch DefaultCredentialsError and any other auth/connection errors.
            # Disable GCS gracefully so local dev still works without gcloud login.
            err_str = str(e)
            if (
                "credentials" in err_str.lower()
                or "default" in err_str.lower()
                or "auth" in err_str.lower()
            ):
                logger.warning(
                    f"GCS credentials not found — disabling GCS for this session. "
                    f"Run 'gcloud auth application-default login' to enable GCS locally. "
                    f"({err_str})"
                )
                self.bucket_name = ""  # disables gcs_enabled for all subsequent calls
                return None
            raise RuntimeError(
                f"Failed to connect to GCS bucket '{self.bucket_name}': {e}"
            ) from e

    def _blob_name(self, filename: str) -> str:
        """Return the full GCS object path for a given filename."""
        return f"{self.index_prefix}/{filename}"

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    def index_exists(self) -> bool:
        """
        Check whether both FAISS index files exist in GCS.

        Returns:
            bool: True if all index files present, False otherwise.
        """
        if not self.gcs_enabled:
            return False
        try:
            bucket = self._get_bucket()
            if bucket is None:
                return False
            for fname in FAISS_FILES:
                blob = bucket.blob(self._blob_name(fname))
                if not blob.exists():
                    logger.info(f"GCS: index file missing — {self._blob_name(fname)}")
                    return False
            logger.info("GCS: FAISS index exists in bucket")
            return True
        except Exception as e:
            logger.warning(f"GCS: could not check index existence: {e}")
            return False

    def upload_faiss_index(self, local_path: str) -> bool:
        """
        Upload FAISS index files from a local directory to GCS.

        Args:
            local_path: Local directory containing index.faiss and index.pkl
                        (e.g. "vectorstore/db_faiss")

        Returns:
            bool: True on success, False on failure.
        """
        if not self.gcs_enabled:
            logger.info("GCS: upload skipped — GCS not configured")
            return False

        local_dir = Path(local_path)
        if not local_dir.exists():
            logger.error(f"GCS upload failed: local path does not exist: {local_path}")
            return False

        try:
            bucket = self._get_bucket()
            if bucket is None:
                logger.info("GCS upload skipped — no credentials available")
                return False
            for fname in FAISS_FILES:
                local_file = local_dir / fname
                if not local_file.exists():
                    logger.error(f"GCS upload failed: missing file {local_file}")
                    return False

                blob = bucket.blob(self._blob_name(fname))
                blob.upload_from_filename(str(local_file))
                size_kb = local_file.stat().st_size / 1024
                logger.info(
                    f"GCS: uploaded {fname} ({size_kb:.1f} KB) → "
                    f"gs://{self.bucket_name}/{self._blob_name(fname)}"
                )

            logger.info(
                f"✅ GCS: FAISS index uploaded to gs://{self.bucket_name}/{self.index_prefix}/"
            )
            return True

        except Exception as e:
            logger.error(f"GCS upload failed: {e}")
            return False

    def download_faiss_index(self, local_path: str) -> bool:
        """
        Download FAISS index files from GCS to a local directory.

        Args:
            local_path: Local directory where files will be written
                        (created if it doesn't exist).

        Returns:
            bool: True on success, False on failure.
        """
        if not self.gcs_enabled:
            logger.info("GCS: download skipped — GCS not configured")
            return False

        if not self.index_exists():
            logger.info("GCS: no index found in bucket — skipping download")
            return False

        try:
            local_dir = Path(local_path)
            local_dir.mkdir(parents=True, exist_ok=True)

            bucket = self._get_bucket()
            if bucket is None:
                logger.info("GCS download skipped — no credentials available")
                return False
            for fname in FAISS_FILES:
                blob = bucket.blob(self._blob_name(fname))
                dest = local_dir / fname
                blob.download_to_filename(str(dest))
                size_kb = dest.stat().st_size / 1024
                logger.info(f"GCS: downloaded {fname} ({size_kb:.1f} KB) → {dest}")

            logger.info(f"✅ GCS: FAISS index downloaded to {local_path}")
            return True

        except Exception as e:
            logger.error(f"GCS download failed: {e}")
            return False

    def get_index_metadata(self) -> dict:
        """
        Return metadata about the GCS-stored index (last updated, sizes).

        Returns:
            dict with keys: exists, last_updated, total_size_kb, files
        """
        metadata = {
            "exists": False,
            "last_updated": None,
            "total_size_kb": 0.0,
            "files": {},
        }

        if not self.gcs_enabled or not self.index_exists():
            return metadata

        try:
            bucket = self._get_bucket()
            metadata["exists"] = True
            latest_updated = None

            for fname in FAISS_FILES:
                blob = bucket.blob(self._blob_name(fname))
                blob.reload()
                size_kb = blob.size / 1024 if blob.size else 0.0
                metadata["files"][fname] = {
                    "size_kb": round(size_kb, 1),
                    "updated": blob.updated,
                }
                metadata["total_size_kb"] += size_kb

                if blob.updated:
                    if latest_updated is None or blob.updated > latest_updated:
                        latest_updated = blob.updated

            metadata["last_updated"] = latest_updated
            metadata["total_size_kb"] = round(metadata["total_size_kb"], 1)

        except Exception as e:
            logger.warning(f"GCS metadata fetch failed: {e}")

        return metadata

    def download_to_temp(self) -> Optional[str]:
        """
        Download the FAISS index to a system temp directory.

        Returns:
            str: Path to the temp directory containing the index files,
                 or None if download failed.
        """
        if not self.gcs_enabled or not self.index_exists():
            return None

        tmp_dir = tempfile.mkdtemp(prefix="faiss_gcs_")
        success = self.download_faiss_index(tmp_dir)
        if success:
            return tmp_dir
        # Clean up on failure
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return None
