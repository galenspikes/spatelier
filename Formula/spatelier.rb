class Spatelier < Formula
  include Language::Python::Virtualenv

  desc "Personal tool library for video and music file handling"
  homepage "https://github.com/galenspikes/spatelier"
  url "https://github.com/galenspikes/spatelier/archive/refs/tags/v0.2.0.tar.gz"
  sha256 "bfe48124cbb08616cefab217b3e2e7d84852f22d32a758643109035b7bdda6a1" # Update after first release
  license "MIT"
  head "https://github.com/galenspikes/spatelier.git", branch: "main"

  depends_on "python@3.12"
  # ffmpeg is required: ffmpeg-python is just a wrapper that calls the system ffmpeg binary
  # Used for video/audio conversion, subtitle embedding, and metadata extraction
  depends_on "ffmpeg"

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
