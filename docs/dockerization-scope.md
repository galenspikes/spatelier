# Dockerization scope

Branch: `feature/dockerization`  
Related: [GitHub Issue #3 — Provide official Docker image](https://github.com/galenspikes/spatelier/issues/3)

---

## Goals

- Run spatelier in a container so users (e.g. on QNAP via Container Station) can run it without installing Python, pip, or system deps.
- Single image that supports: video/playlist download, transcription, config and downloads on mounted volumes.

## Runtime requirements (from Formula / pyproject)

- **Python:** 3.10+ (3.12 preferred for parity with Homebrew).
- **System:** ffmpeg (video/audio), deno (optional, for yt-dlp JS/challenge solving).
- **Pip:** spatelier + deps; include `[web]` and Chromium by default so YouTube cookie refresh works out of the box (same as Homebrew).

## Image design (to be decided)

| Item | Options / notes |
|------|------------------|
| **Base image** | `python:3.12-slim` (small); or distro with ffmpeg in repos (e.g. Debian/Ubuntu) so we can `apt install ffmpeg`. |
| **ffmpeg** | Install from base distro (`apt install ffmpeg`) or use image that includes it. |
| **deno** | Optional; install if we want yt-dlp EJS/challenge solving in container. |
| **Package install** | `pip install spatelier[web]` and `playwright install chromium` so cookie refresh works (larger image, same UX as Homebrew). |
| **Entrypoint** | `spatelier` (CLI). Default command can be `--help` or leave unset so user passes subcommand. |
| **User** | Prefer non-root user in container; ensure volume mounts are writable. |

## Volumes / mounts

- **Config:** e.g. `~/.config/spatelier` or app data dir — mount so config and DB persist.
- **Downloads:** mount host directory (or NAS path) as download output directory so files appear on host/QNAP.
- Cookie refresh: covered by including [web] + Chromium in the image (no extra mount needed for typical use).

## QNAP / Container Station

- Image should be usable on QNAP (Linux, typically x86_64 or aarch64).
- Users run container with volume mounts for config and downloads; optional env for output path.
- Document in README or separate doc: example `docker run` and QNAP Container Station steps.

## Out of scope (for now)

- Docker Compose (can add later if needed).
- Kubernetes/Helm (not in initial scope).

## Next steps

1. Add a minimal `Dockerfile` (base image, ffmpeg, pip install spatelier, entrypoint).
2. Add `.dockerignore` to keep build context small.
3. Test image locally: `docker build -t spatelier .` and `docker run --rm spatelier --version`.
4. Document in README: how to run with volume mounts for config and downloads.
5. (Optional) Publish image to GitHub Container Registry (ghcr.io) or Docker Hub; link from README.
