class Spatelier < Formula
  include Language::Python::Virtualenv

  desc "Personal tool library for video and music file handling"
  homepage "https://github.com/galenspikes/spatelier"
  url "https://github.com/galenspikes/spatelier/archive/refs/tags/v0.3.1.tar.gz"
  sha256 "790fc95efa839fe1a7c20bd2d6d5e80f9a9f43e49da67d3ed790a8b5428f6459"
  license "MIT"
  head "https://github.com/galenspikes/spatelier.git", branch: "main"

  depends_on "python@3.12"
  # ffmpeg is required: ffmpeg-python is just a wrapper that calls the system ffmpeg binary
  # Used for video/audio conversion, subtitle embedding, and metadata extraction
  depends_on "ffmpeg"
  depends_on "deno"  # Required by yt-dlp for YouTube SABR streaming

  def install
    python3 = "python3.12"
    venv = virtualenv_create(libexec, python3)

    # Install the package with all dependencies from pyproject.toml
    system libexec/"bin/pip", "install", "-v", buildpath

    # Install entry point script
    bin.install libexec/"bin/spatelier"
  end

  test do
    system "#{bin}/spatelier", "--version"
  end
end
