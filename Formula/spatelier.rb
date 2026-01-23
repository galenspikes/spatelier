class Spatelier < Formula
  include Language::Python::Virtualenv

  desc "Personal tool library for video and music file handling"
  homepage "https://github.com/galenspikes/spatelier"
  url "https://github.com/galenspikes/spatelier/archive/refs/tags/v0.3.8.tar.gz"
  sha256 "25ffd3f8a41005dea13b8a4e43516bfe0830e699436b9ff14a7e4ce2d7b3fd2d"
  license "MIT"
  head "https://github.com/galenspikes/spatelier.git", branch: "main"

  depends_on "python@3.12"
  # ffmpeg is required: ffmpeg-python is just a wrapper that calls the system ffmpeg binary
  # Used for video/audio conversion, subtitle embedding, and metadata extraction
  depends_on "ffmpeg"
  depends_on "deno"  # Required by yt-dlp for YouTube SABR streaming

  def install
    venv = virtualenv_create(libexec, "python3.12")
    # Install pip using get-pip.py (ensurepip finds system pip with --system-site-packages)
    system "curl", "-sSL", "https://bootstrap.pypa.io/get-pip.py", "-o", "/tmp/get-pip.py"
    system libexec/"bin/python", "/tmp/get-pip.py", "--isolated", "--disable-pip-version-check"
    system libexec/"bin/pip", "install", "-v", buildpath
    bin.install_symlink libexec/"bin/spatelier"
  end

  test do
    system "#{bin}/spatelier", "--version"
  end
end
