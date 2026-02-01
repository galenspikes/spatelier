# Issue: Add `--no-max` option for playlist/channel downloads

**Title:** Add `--no-max` option for playlist/channel downloads

**Type:** Feature request

---

## Problem

`spatelier video download` for channels/playlists defaults to `--max-videos 10`. Users who want to download an entire channel (e.g. 545 videos) must pass a large number explicitly (e.g. `--max-videos 545`), which is awkward and requires knowing the count in advance.

## Proposed solution

Add a `--no-max` (or `--all`) option that means "no limit" for playlist/channel downloads:

- When `--no-max` is set, do not pass `playlistend` to yt-dlp (or equivalent), so all videos in the playlist/channel are downloaded.
- When `--no-max` is not set, keep current behavior: use `max_videos` (default 10) to set `playlistend`.
- If both `--no-max` and `--max-videos N` are given, either treat `--no-max` as overriding (no limit) or document that `--max-videos` takes precedence; recommend one in the implementation.

## Acceptance criteria

- [ ] New CLI option (e.g. `--no-max` or `--all`) for the download command(s) that support playlists/channels.
- [ ] When set, playlist/channel download has no video count limit.
- [ ] Help text updated; README or usage docs mention the option.

## Notes

- Current default: `max_videos: int = typer.Option(10, "--max-videos", "-m", ...)` in `cli/video.py`.
- Playlist service uses `ydl_opts["playlistend"] = max_videos` when `max_videos > 0` (`modules/video/services/playlist_service.py`). For "no max", omit `playlistend` or set it to `-1` per yt-dlp semantics.
