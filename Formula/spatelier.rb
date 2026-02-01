class Spatelier < Formula
  include Language::Python::Virtualenv

  desc "Personal tool library for video and music file handling"
  homepage "https://github.com/galenspikes/spatelier"
  url "https://github.com/galenspikes/spatelier/archive/refs/tags/v0.4.2.tar.gz"
  sha256 "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
  license "MIT"
  head "https://github.com/galenspikes/spatelier.git", branch: "main"

  # skip_clean does not prevent "fix install linkage"; av's pre-built dylibs have header space
  # too small for Homebrew's path rewrite. Install still works; ignore the linkage warning.
  skip_clean "libexec"

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
    system libexec/"bin/pip", "install", "-v", "#{buildpath}[web]"
    # Install Chromium for Playwright so YouTube cookie refresh works
    system libexec/"bin/playwright", "install", "chromium"
    bin.install_symlink libexec/"bin/spatelier"
  end

  test do
    system "#{bin}/spatelier", "--version"
  end
end
