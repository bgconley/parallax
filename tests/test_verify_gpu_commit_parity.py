import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_gpu_commit_parity_reports_mismatch_and_dirty_state(tmp_path: Path) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_ssh = fake_bin / "ssh"
    fake_ssh.write_text(
        "#!/usr/bin/env bash\n"
        "printf 'actual-sha\\n'\n"
        "printf ' M services/api/example.py\\n'\n"
    )
    fake_ssh.chmod(0o755)

    env = {
        **os.environ,
        "PATH": f"{fake_bin}:{os.environ['PATH']}",
        "PARALLAX_GPU_KEY": str(tmp_path / "fake-key"),
        "PARALLAX_GPU_HOST": "fake-host",
        "PARALLAX_GPU_REPO": "/fake/repo",
    }
    result = subprocess.run(
        ["bash", "scripts/verify_gpu_commit_parity.sh", "expected-sha"],
        cwd=REPO_ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert (
        "GPU checkout mismatch: expected expected-sha, got actual-sha; "
        "GPU checkout is dirty"
    ) in result.stderr
