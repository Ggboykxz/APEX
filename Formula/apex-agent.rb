class ApexAgent < Formula
  desc "Universal AI coding agent — every model, one terminal"
  homepage "https://apex-agent.dev"
  url "https://github.com/Ggboykxz/APEX/archive/refs/tags/v1.3.0.tar.gz"
  sha256 "PLACEHOLDER_SHA256"
  license "MIT"
  head "https://github.com/Ggboykxz/APEX.git", branch: "main"

  depends_on "python@3.12"

  resource "apex-agent" do
    url "https://pypi.org/packages/source/a/apex-agent/apex-agent-1.3.0.tar.gz"
    sha256 "PLACEHOLDER_SHA256"
  end

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "APEX", shell_output("#{bin}/apex --version 2>&1", 0)
  end
end
