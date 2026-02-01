# Issue: Bad file descriptor when downloading to NAS (filename characters)

**Title:** Bad file descriptor when downloading to NAS — sanitize filenames (special characters)

**Type:** Bug

---

## Problem

When downloading playlists/channels to a NAS path (e.g. SMB share), some videos reach **100% downloaded** but then fail with:

```
ERROR: Unable to download video: [Errno 9] Bad file descriptor
```

The download leaves `.mp4.part` files instead of completed `.mp4` files.

**Observed:** Failures coincided with video titles that contain **special characters** that are problematic on NAS/SMB, e.g.:

- **`#`** (hash/pound): `Video Title #tag1 #tag2 [VIDEO_ID].mp4.part`
- **`|`** (pipe): `Video Title | Part 1 [VIDEO_ID].mp4.part` — pipe is invalid on Windows and can break SMB/NAS rename or final write
- Any filename where the title (from `%(title)s`) includes characters that the target filesystem does not handle during write/rename

**Hypothesis:** Special characters in the filename (e.g. `#`, `|`, or others) cause the final write or rename (`.part` → `.mp4`) to fail on the NAS/SMB filesystem, resulting in "Bad file descriptor." We want to **check for and sanitize special characters** in output filenames. Our sanitizers currently replace `<>:"/\|?*` but **do not** replace `#`; and the per-video path is built by yt-dlp from the raw title, so any character yt-dlp leaves in place can trigger the bug on NAS.

## Scope

- **Where:** Playlist/channel downloads (and single-video downloads) when the **output path is on a NAS/SMB share**.
- **When:** Video title (used in `outtmpl` as `%(title)s`) contains **special characters** that are problematic on the target filesystem (e.g. `#`, `|`, or others that NAS/SMB handle poorly during rename or final write).
- **Current behavior:** `playlist_service._sanitize_filename` and `utils.helpers.safe_filename` replace `<>:"/\|?*` only (no `#`). The **per-video** filename is produced by yt-dlp from `outtmpl`; yt-dlp’s default title sanitization may leave `#` and other chars in place.
- **Repro:** Download a playlist to a NAS path where at least one video has special characters in the title (e.g. `#` or `|`); observe 100% then "Bad file descriptor" and leftover `.mp4.part` files.

## Proposed solution

1. **Enable yt-dlp filename restriction**  
   Add `restrictfilenames`: True to yt-dlp options in:
   - `modules/video/services/playlist_service.py` (`_build_playlist_ydl_opts`)
   - `modules/video/services/download_service.py` (`_build_ydl_opts`)  
   So yt-dlp sanitizes the title (replaces special/problematic chars with underscores) when building the output path.

2. **Check for special characters in our sanitizers**  
   Ensure we replace all characters that can break NAS/SMB (e.g. `#`, and any others not already covered):
   - `playlist_service._sanitize_filename`: extend regex to include `#` (and any other chars that need sanitizing).
   - `utils.helpers.safe_filename`: add `#` to `invalid_chars`.  
   Keeps playlist folder names and any other paths we build safe for NAS/SMB.

## Acceptance criteria

- [ ] Playlist/channel download to NAS no longer fails with "Bad file descriptor" for videos whose titles contain special characters (e.g. `#`, `|`, or others that trigger the bug).
- [ ] No leftover `.mp4.part` files for those videos; completed `.mp4` files are written and renamed successfully.
- [ ] We check for / sanitize special characters in output filenames so NAS/SMB writes and renames succeed.
- [ ] Existing behavior for local disk and for titles without special chars is unchanged (no regression).

## Notes

- yt-dlp: `--restrict-filenames` / `restrictfilenames` replaces invalid filename characters with underscores.
- Our outtmpl: `%(title)s [%(id)s].%(ext)s` — the title comes from yt-dlp; with `restrictfilenames` it will be sanitized before use in the path.
