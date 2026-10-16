"""Exercise the published dependency metadata with an offline package resolver."""

import shutil
import subprocess
from importlib.metadata import requires
from zipfile import ZipFile

import pytest
from packaging.requirements import Requirement


@pytest.mark.parametrize(
    "resolution,expected_version", [("highest", "1.28.1"), ("lowest", "1.4.1")]
)
def test_mcp_dependency_resolution(tmp_path, resolution, expected_version):
    """Fresh installs must choose the supported SDK, even if MCP 2.x is available."""
    uv = shutil.which("uv")
    if uv is None:
        pytest.skip("uv is required to exercise dependency resolution")

    requirement = next(
        raw for raw in requires("mcpdoc") if Requirement(raw).name == "mcp"
    )
    requirements = tmp_path / "requirements.in"
    requirements.write_text(requirement, encoding="utf-8")

    # Only metadata is needed: these wheels are resolved, never installed.
    for version in ["1.4.0", "1.4.1", "1.28.1", "2.0.0", "2.3.0"]:
        dist_info = f"mcp-{version}.dist-info"
        with ZipFile(tmp_path / f"mcp-{version}-py3-none-any.whl", "w") as wheel:
            wheel.writestr(
                f"{dist_info}/METADATA",
                f"Metadata-Version: 2.1\nName: mcp\nVersion: {version}\n"
                "Provides-Extra: cli\n",
            )
            wheel.writestr(
                f"{dist_info}/WHEEL",
                "Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
            )
            wheel.writestr(f"{dist_info}/RECORD", "")

    result = subprocess.run(
        [
            uv,
            "pip",
            "compile",
            "--offline",
            "--no-index",
            "--find-links",
            str(tmp_path),
            "--resolution",
            resolution,
            str(requirements),
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    resolved = [line for line in result.stdout.splitlines() if line.startswith("mcp==")]
    assert resolved == [f"mcp=={expected_version}"]
