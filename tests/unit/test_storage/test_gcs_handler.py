"""
Unit tests for src/storage/gcs_handler.py

All GCS I/O is mocked via unittest.mock so tests run fully offline
with no GCP credentials required.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helper: create a mock GCS blob
# ---------------------------------------------------------------------------


def _make_blob(name: str, exists: bool = True, size: int = 1024):
    blob = MagicMock()
    blob.name = name
    blob.exists.return_value = exists
    blob.size = size
    blob.updated = None
    return blob


# ---------------------------------------------------------------------------
# Import the module under test
# ---------------------------------------------------------------------------

from src.storage.gcs_handler import GCSHandler, FAISS_FILES


# ===========================================================================
# GCSHandler — initialisation
# ===========================================================================


class TestGCSHandlerInit:
    def test_disabled_when_no_env_var(self, monkeypatch):
        """gcs_enabled is False when GCS_BUCKET_NAME is not set."""
        monkeypatch.delenv("GCS_BUCKET_NAME", raising=False)
        handler = GCSHandler()
        assert handler.gcs_enabled is False

    def test_enabled_when_env_var_set(self, monkeypatch):
        """gcs_enabled is True when GCS_BUCKET_NAME has a value."""
        monkeypatch.setenv("GCS_BUCKET_NAME", "my-test-bucket")
        handler = GCSHandler()
        assert handler.gcs_enabled is True
        assert handler.bucket_name == "my-test-bucket"

    def test_explicit_bucket_name_overrides_env(self, monkeypatch):
        """Explicit bucket_name argument takes priority over env var."""
        monkeypatch.setenv("GCS_BUCKET_NAME", "env-bucket")
        handler = GCSHandler(bucket_name="explicit-bucket")
        assert handler.bucket_name == "explicit-bucket"

    def test_custom_index_prefix(self):
        """Custom index_prefix is stored correctly."""
        handler = GCSHandler(bucket_name="b", index_prefix="custom/prefix")
        assert handler.index_prefix == "custom/prefix"

    def test_default_index_prefix(self):
        """Default index_prefix is 'faiss-index'."""
        handler = GCSHandler(bucket_name="b")
        assert handler.index_prefix == "faiss-index"


# ===========================================================================
# GCSHandler.index_exists
# ===========================================================================


class TestIndexExists:
    def test_returns_false_when_gcs_disabled(self, monkeypatch):
        """index_exists returns False immediately when GCS not configured."""
        monkeypatch.delenv("GCS_BUCKET_NAME", raising=False)
        handler = GCSHandler()
        assert handler.index_exists() is False

    @patch("src.storage.gcs_handler.GCSHandler._get_bucket")
    def test_returns_true_when_all_files_exist(self, mock_get_bucket):
        """index_exists returns True when both FAISS files are in the bucket."""
        bucket = MagicMock()
        mock_get_bucket.return_value = bucket
        bucket.blob.side_effect = lambda name: _make_blob(name, exists=True)

        handler = GCSHandler(bucket_name="test-bucket")
        assert handler.index_exists() is True

    @patch("src.storage.gcs_handler.GCSHandler._get_bucket")
    def test_returns_false_when_file_missing(self, mock_get_bucket):
        """index_exists returns False when one of the FAISS files is absent."""
        bucket = MagicMock()
        mock_get_bucket.return_value = bucket

        call_count = {"n": 0}

        def blob_side_effect(name):
            call_count["n"] += 1
            # First file exists, second does not
            return _make_blob(name, exists=(call_count["n"] == 1))

        bucket.blob.side_effect = blob_side_effect

        handler = GCSHandler(bucket_name="test-bucket")
        assert handler.index_exists() is False

    @patch("src.storage.gcs_handler.GCSHandler._get_bucket")
    def test_returns_false_on_gcs_error(self, mock_get_bucket):
        """index_exists returns False when GCS raises an exception."""
        mock_get_bucket.side_effect = RuntimeError("GCS connection failed")
        handler = GCSHandler(bucket_name="test-bucket")
        assert handler.index_exists() is False


# ===========================================================================
# GCSHandler.upload_faiss_index
# ===========================================================================


class TestUploadFaissIndex:
    def test_returns_false_when_gcs_disabled(self, monkeypatch, tmp_path):
        """upload_faiss_index returns False when GCS not configured."""
        monkeypatch.delenv("GCS_BUCKET_NAME", raising=False)
        handler = GCSHandler()
        result = handler.upload_faiss_index(str(tmp_path))
        assert result is False

    def test_returns_false_when_local_path_missing(self):
        """upload_faiss_index returns False when local path does not exist."""
        handler = GCSHandler(bucket_name="test-bucket")
        result = handler.upload_faiss_index("/nonexistent/path/db_faiss")
        assert result is False

    @patch("src.storage.gcs_handler.GCSHandler._get_bucket")
    def test_uploads_both_files_successfully(self, mock_get_bucket, tmp_path):
        """Both FAISS files are uploaded when they exist locally."""
        # Create mock local files
        for fname in FAISS_FILES:
            (tmp_path / fname).write_bytes(b"dummy data")

        bucket = MagicMock()
        mock_get_bucket.return_value = bucket
        blob = MagicMock()
        bucket.blob.return_value = blob

        handler = GCSHandler(bucket_name="test-bucket")
        result = handler.upload_faiss_index(str(tmp_path))

        assert result is True
        assert blob.upload_from_filename.call_count == len(FAISS_FILES)

    @patch("src.storage.gcs_handler.GCSHandler._get_bucket")
    def test_returns_false_when_index_file_missing(self, mock_get_bucket, tmp_path):
        """upload_faiss_index returns False when one FAISS file is missing locally."""
        # Only create one of the two required files
        (tmp_path / FAISS_FILES[0]).write_bytes(b"dummy data")
        # FAISS_FILES[1] intentionally not created

        handler = GCSHandler(bucket_name="test-bucket")
        result = handler.upload_faiss_index(str(tmp_path))
        assert result is False

    @patch("src.storage.gcs_handler.GCSHandler._get_bucket")
    def test_returns_false_on_upload_error(self, mock_get_bucket, tmp_path):
        """upload_faiss_index returns False when GCS upload raises an exception."""
        for fname in FAISS_FILES:
            (tmp_path / fname).write_bytes(b"dummy data")

        bucket = MagicMock()
        mock_get_bucket.return_value = bucket
        blob = MagicMock()
        blob.upload_from_filename.side_effect = Exception("network error")
        bucket.blob.return_value = blob

        handler = GCSHandler(bucket_name="test-bucket")
        result = handler.upload_faiss_index(str(tmp_path))
        assert result is False


# ===========================================================================
# GCSHandler.download_faiss_index
# ===========================================================================


class TestDownloadFaissIndex:
    def test_returns_false_when_gcs_disabled(self, monkeypatch, tmp_path):
        """download_faiss_index returns False when GCS not configured."""
        monkeypatch.delenv("GCS_BUCKET_NAME", raising=False)
        handler = GCSHandler()
        result = handler.download_faiss_index(str(tmp_path))
        assert result is False

    @patch("src.storage.gcs_handler.GCSHandler.index_exists", return_value=False)
    def test_returns_false_when_index_not_in_gcs(self, mock_exists, tmp_path):
        """download_faiss_index returns False when GCS index doesn't exist."""
        handler = GCSHandler(bucket_name="test-bucket")
        result = handler.download_faiss_index(str(tmp_path))
        assert result is False

    @patch("src.storage.gcs_handler.GCSHandler.index_exists", return_value=True)
    @patch("src.storage.gcs_handler.GCSHandler._get_bucket")
    def test_downloads_both_files_successfully(
        self, mock_get_bucket, mock_exists, tmp_path
    ):
        """Both FAISS files are downloaded and written locally."""
        bucket = MagicMock()
        mock_get_bucket.return_value = bucket
        dest_dir = tmp_path / "download_dest"

        def fake_download(filename):
            # Simulate writing files to disk
            Path(filename).write_bytes(b"fake faiss data")

        blob = MagicMock()
        blob.download_to_filename.side_effect = fake_download
        bucket.blob.return_value = blob

        handler = GCSHandler(bucket_name="test-bucket")
        result = handler.download_faiss_index(str(dest_dir))

        assert result is True
        assert blob.download_to_filename.call_count == len(FAISS_FILES)


# ===========================================================================
# GCSHandler.download_to_temp
# ===========================================================================


class TestDownloadToTemp:
    def test_returns_none_when_gcs_disabled(self, monkeypatch):
        """download_to_temp returns None when GCS not configured."""
        monkeypatch.delenv("GCS_BUCKET_NAME", raising=False)
        handler = GCSHandler()
        result = handler.download_to_temp()
        assert result is None

    @patch("src.storage.gcs_handler.GCSHandler.index_exists", return_value=False)
    def test_returns_none_when_no_index(self, _):
        """download_to_temp returns None when no GCS index exists."""
        handler = GCSHandler(bucket_name="test-bucket")
        assert handler.download_to_temp() is None

    @patch("src.storage.gcs_handler.GCSHandler.download_faiss_index", return_value=True)
    @patch("src.storage.gcs_handler.GCSHandler.index_exists", return_value=True)
    def test_returns_temp_path_on_success(self, mock_exists, mock_download):
        """download_to_temp returns a valid temp directory path on success."""
        handler = GCSHandler(bucket_name="test-bucket")
        result = handler.download_to_temp()
        assert result is not None
        assert isinstance(result, str)


# ===========================================================================
# GCSHandler.get_index_metadata
# ===========================================================================


class TestGetIndexMetadata:
    def test_returns_empty_when_gcs_disabled(self, monkeypatch):
        """get_index_metadata returns exists=False dict when GCS disabled."""
        monkeypatch.delenv("GCS_BUCKET_NAME", raising=False)
        handler = GCSHandler()
        meta = handler.get_index_metadata()
        assert meta["exists"] is False

    @patch("src.storage.gcs_handler.GCSHandler.index_exists", return_value=False)
    def test_returns_empty_when_no_index(self, _):
        """get_index_metadata returns exists=False dict when no index in GCS."""
        handler = GCSHandler(bucket_name="test-bucket")
        meta = handler.get_index_metadata()
        assert meta["exists"] is False

    @patch("src.storage.gcs_handler.GCSHandler.index_exists", return_value=True)
    @patch("src.storage.gcs_handler.GCSHandler._get_bucket")
    def test_returns_metadata_when_index_exists(self, mock_get_bucket, mock_exists):
        """get_index_metadata returns correct keys including total_size_kb."""
        from datetime import datetime, timezone

        bucket = MagicMock()
        mock_get_bucket.return_value = bucket

        fake_time = datetime(2025, 1, 1, tzinfo=timezone.utc)
        blob = MagicMock()
        blob.size = 2048
        blob.updated = fake_time
        blob.reload.return_value = None
        bucket.blob.return_value = blob

        handler = GCSHandler(bucket_name="test-bucket")
        meta = handler.get_index_metadata()

        assert meta["exists"] is True
        assert meta["total_size_kb"] > 0
        assert meta["last_updated"] == fake_time
        assert len(meta["files"]) == len(FAISS_FILES)
