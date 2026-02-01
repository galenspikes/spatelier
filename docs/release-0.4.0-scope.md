# Release 0.4.0 – Scope of Fixes

**Branch:** `release/0.4.0` (from `develop`)  
**Goal:** Fix NAS-related test failures and Config/test hygiene so all tests pass; ship as 0.4.0.

---

## Push / branch status

- **Push `main`:** Do this manually (`git push origin main`). Push failed from this environment due to auth.
- **0.4.0 work:** Done on `release/0.4.0` branched from `develop`. Merge to `develop` when ready, then release 0.4.0 from `main` after merge.

---

## 1. Incomplete `Config` mock (NAS tests)

**Problem:** NAS tests use `Mock(spec=Config)` but do not set nested attributes (e.g. `config.database.sqlite_path`, `config.video.temp_dir`). Code paths (e.g. `MetadataExtractor`/`MetadataManager`) access these and raise `AttributeError`.

**Fix:** Use a real `Config()` where a full config is needed, or a helper that builds a minimal config (e.g. `tests/utils/config_helper` or fixtures) with at least:
- `config.video.temp_dir`
- `config.database.sqlite_path`
- `config.video.output_dir` if used

Apply in: `tests/unit/modules/test_nas_detection.py`, `tests/integration/test_nas_operations.py`, `tests/integration/test_nas_video_workflow.py` where `Mock(spec=Config)` is used.

---

## 2. Old API expectations on `VideoDownloadService`

**Problem:** Tests expect methods that no longer exist on `VideoDownloadService`:
- `download` → now `download_video`
- `_is_nas_path` → logic lives in `StorageAdapter.is_remote()` (e.g. `NASStorageAdapter`)
- `_get_temp_processing_dir` → `storage_adapter.get_temp_processing_dir()`
- `_move_file_to_final_destination` → `storage_adapter.move_file()`
- `_cleanup_temp_directory` → `storage_adapter.cleanup_temp_dir()`
- `download_playlist_with_transcription` → on `PlaylistService`, not `VideoDownloadService`
- `_transcribe_video`, `_embed_subtitles_into_video` → on `TranscriptionService`
- `_move_playlist_to_final_destination` → not present; playlist move is handled inside `PlaylistService` via storage adapter.

**Fix:**
- Add thin delegation methods on `VideoDownloadService` so existing tests keep working without rewriting every call:
  - `_is_nas_path(path)` → `self.storage_adapter.is_remote(path)`
  - `_get_temp_processing_dir(job_id)` → `self.storage_adapter.get_temp_processing_dir(job_id)`
  - `_move_file_to_final_destination(src, dest)` → `self.storage_adapter.move_file(src, dest)`
  - `_cleanup_temp_directory(temp_dir)` → `self.storage_adapter.cleanup_temp_dir(temp_dir)`
- Workflow tests that call `download`, `download_playlist_with_transcription`, `_transcribe_video`, `_embed_subtitles_into_video` on the download service: switch to the correct entry points:
  - Single video: `VideoDownloadService.download_video`
  - Playlist + transcription: `PlaylistService.download_playlist_with_transcription` or the corresponding use case
  - Transcription/subtitles: `TranscriptionService` methods or use case
- For `_move_playlist_to_final_destination`: either test `PlaylistService` + storage adapter for “move playlist dir”, or remove/skip the test if that API is not exposed; do not call a non-existent method on `VideoDownloadService`.

---

## 3. `TypeError: data must be str, not bytes` (pathlib)

**Problem:** Two failures where pathlib is given bytes instead of str (e.g. `Path.write_text()` given bytes).

**Locations:** `tests/performance/test_nas_performance.py` uses `nas_file_scenarios`; the `"video_file"` scenario has `"content": b"..."`. Calling `write_text(scenario["content"])` and `read_text()` on that causes the error.

**Fix:** In NAS performance tests, use `write_bytes`/`read_bytes` when `scenario["content"]` is bytes, and `write_text`/`read_text` when it is str.

---

## 4. Test files to touch

| Area | File | Changes |
|------|------|--------|
| Unit NAS | `tests/unit/modules/test_nas_detection.py` | Config mock → real Config or minimal mock with `database.sqlite_path`, `video.temp_dir`; keep calling delegation methods on `VideoDownloadService`. |
| Integration NAS | `tests/integration/test_nas_operations.py` | Same Config fix; replace `_move_playlist_to_final_destination` with test of `PlaylistService` or storage adapter move, or remove/skip. |
| Integration workflow | `tests/integration/test_nas_video_workflow.py` | Use `download_video`; use `PlaylistService` / `TranscriptionService` (or use cases) for playlist and transcription/subtitle flows; fix Config. |
| Performance NAS | `tests/performance/test_nas_performance.py` | Use `write_bytes`/`read_bytes` for byte content, `write_text`/`read_text` for str. |

---

## 5. Implementation order

1. Add delegation methods on `VideoDownloadService` (`_is_nas_path`, `_get_temp_processing_dir`, `_move_file_to_final_destination`, `_cleanup_temp_directory`).
2. Introduce a minimal NAS config helper or use `Config()` in NAS tests and fix all `Mock(spec=Config)` usages that need `database.sqlite_path` / `video.temp_dir`.
3. Fix `test_nas_operations`: Config + `_move_playlist_to_final_destination` (repoint or remove).
4. Fix `test_nas_video_workflow`: Config + use `download_video`, `PlaylistService`, `TranscriptionService` (or use cases).
5. Fix NAS performance tests: bytes vs str in file write/read.

After these, run the full NAS-related and performance test suites and fix any remaining failures before tagging 0.4.0.

---

## 6. Parametrize NAS path for tests (done)

- **Default root:** `/Volumes/NAS`. If it doesn’t exist, fall back to home dir, then tmp.
- **Subdir:** `.spatelier/tests/` under that root. Created if missing.
- **Implementation:** `tests/fixtures/nas_fixtures.py`: `get_nas_path_root()`, `get_nas_tests_path()`, `NAS_PATH_ROOT_DEFAULT`. No env var; all in code.
- **`nas_available`:** True only when the default NAS root exists (real NAS in use).

---

## 7. NAS write permission (done)

- **Execution:** Before using a remote path, we check writability with `storage_adapter.can_write_to(path)` (probe file create/delete). Used in `VideoDownloadService.download_video` and `PlaylistService.download_playlist`; on failure we return a clear error instead of failing later on move.
- **Tests:** `test_nas_dir_is_writable` and `test_nas_permissions_and_access` use the same check; if the path isn’t writable they skip with a message about NFS/SMB.
- **Why permission issues happen:** NFS/SMB from macOS can show permission errors due to uid/gid mapping, mount options (e.g. read-only), or share ACLs. That’s an environment/OS-level concern (e.g. NFS from Mac often can’t write without correct mount/export setup); the app fails fast and reports “Remote storage path is not writable” instead of failing mid-download.
