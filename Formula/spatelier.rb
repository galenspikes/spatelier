class Spatelier < Formula
  include Language::Python::Virtualenv

  desc "Personal tool library for video and music file handling"
  homepage "https://github.com/galenspikes/spatelier"
  url "https://github.com/galenspikes/spatelier/archive/refs/tags/v0.3.6.tar.gz"
  sha256 "4ba2e92432649ea78c6071f5a646d17a4d3f9e44c8e5871653b6b8d04c18a967"
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
