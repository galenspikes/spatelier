class Spatelier < Formula
  include Language::Python::Virtualenv

  desc "Personal tool library for video and music file handling"
  homepage "https://github.com/galenspikes/spatelier"
  url "https://github.com/galenspikes/spatelier/archive/refs/tags/v0.3.5.tar.gz"
  sha256 "fd429717971819342d187b1d182f024b69c13b0f3044d8a1a2ba6195663b5781"
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

    # Install pip in the venv (virtualenv_create uses --without-pip by default)
    system python3, "-m", "pip", "install", "--python", libexec/"bin/python", "pip", "setuptools", "wheel"

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
