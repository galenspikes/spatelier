class Spatelier < Formula
  include Language::Python::Virtualenv

  desc "Personal tool library for video and music file handling"
  homepage "https://github.com/galenspikes/spatelier"
  url "https://github.com/galenspikes/spatelier/archive/refs/tags/v0.3.7.tar.gz"
  sha256 "9ee38e5ed73c87bb5b7e31f13126868ece4ff768440719534e739961f4b60e51"
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

    # Install pip, setuptools, and wheel using ensurepip (bundled with Python)
    system libexec/"bin/python", "-m", "ensurepip", "--upgrade"

    # Install the package with all dependencies from pyproject.toml
    # Installing from source directory should automatically install dependencies
    system libexec/"bin/pip", "install", buildpath

    # Install entry point script
    bin.install_symlink libexec/"bin/spatelier"
  end

  test do
    system "#{bin}/spatelier", "--version"
  end
end
