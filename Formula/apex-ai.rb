class ApexAi < Formula
  desc "Universal AI coding agent — every model, one terminal"
  homepage "https://apex-ai.dev"
  url "https://github.com/Ggboykxz/APEX/archive/refs/tags/v1.0.0.tar.gz"
  # SHA256 calculated from v1.0.0 release tarball
  sha256 "9ebfc371649174dc86a1e9207cf806ad00afba2253fa85dc36636613644d466c"
  license "MIT"
  head "https://github.com/Ggboykxz/APEX.git", branch: "main"

  depends_on "python@3.12"

  resource "apex-ai" do
    url "https://pypi.org/packages/source/a/apex-ai/apex-ai-1.0.0.tar.gz"
    sha256 "5dbe9b69ffca46b4ac66bd6dd1cb871fcfa52d3071e17ed77a7a16b7987beae5"
  end

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "1.0.0", shell_output("#{bin}/apex --version 2>&1", 0)
  end
end
