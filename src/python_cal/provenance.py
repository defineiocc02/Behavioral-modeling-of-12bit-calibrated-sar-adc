"""
provenance.py — 运行溯源与可复现性 (P0)

每次运行生成唯一 run_manifest.json，包含：
  - run_id (UUID + timestamp)
  - git commit hash
  - config/topology/decoder hash
  - imported module paths
  - terminal 物理参数
  - random seed
  - FFT/DC/MC 配置
"""
import os, sys, json, hashlib, uuid, subprocess, importlib
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict


def _get_git_commit(repo_dir: str) -> str:
    """获取当前 git commit hash"""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_dir, capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "unknown"


def _get_git_state(repo_dir: str) -> dict:
    """记录分支与工作树状态，避免旧结果被误认作当前代码结果。"""
    state = {
        "branch": "unknown",
        "dirty": None,
        "status_short": "unknown",
        "status_count": None,
        "status_truncated": False,
    }
    try:
        root_result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=repo_dir, capture_output=True, text=True, timeout=5,
        )
        git_cwd = root_result.stdout.strip() if root_result.returncode == 0 else repo_dir
        branch = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=git_cwd, capture_output=True, text=True, timeout=5,
        )
        status = subprocess.run(
            ["git", "status", "--short"],
            cwd=git_cwd, capture_output=True, text=True, timeout=5,
        )
        if branch.returncode == 0:
            state["branch"] = branch.stdout.strip() or "detached"
        if status.returncode == 0:
            lines = status.stdout.splitlines()
            state["status_count"] = len(lines)
            max_lines = 200
            state["status_truncated"] = len(lines) > max_lines
            state["status_short"] = "\n".join(lines[:max_lines])
            state["dirty"] = bool(lines)
    except Exception:
        pass
    return state


def _hash_file(filepath: str) -> str:
    """文件的 SHA-256"""
    try:
        with open(filepath, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()[:16]
    except Exception:
        return "unknown"


def _hash_module(module_name: str) -> str:
    """模块源文件的 SHA-256"""
    try:
        mod = importlib.import_module(module_name)
        if hasattr(mod, '__file__') and mod.__file__:
            return _hash_file(mod.__file__)
    except Exception:
        pass
    return "unknown"


@dataclass
class RunManifest:
    """运行溯源清单"""
    run_id: str
    timestamp_utc: str
    git_commit: str
    config_hash: str
    topology_hash: str
    decoder_hash: str
    solver_hash: str
    calibrator_hash: str
    comparator_hash: str
    git_branch: str = "unknown"
    git_dirty: bool | None = None
    git_status_short: str = "unknown"
    git_status_count: int | None = None
    git_status_truncated: bool = False
    module_hashes: dict = field(default_factory=dict)
    terminal_physical: bool = False
    random_seed: int = 42
    fft_config: dict = field(default_factory=dict)
    dc_config: dict = field(default_factory=dict)
    mc_config: dict = field(default_factory=dict)
    system_info: dict = field(default_factory=dict)


def generate_manifest(
    repo_dir: str = None,
    random_seed: int = 42,
    fft_n: int = 4096,
    fft_k: int = 127,
    fft_fs: float = 10e6,
    amp_dbfs: float = -0.5,
    dnl_iter: int = 15,
    mc_seeds: int = 100,
    mc_sigma_pct: float = 0.5,
    avg_pairs: int = 128,
    cal_noise_lsb: float = 0.5,
) -> RunManifest:
    """生成运行溯源清单"""
    if repo_dir is None:
        repo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    now = datetime.now(timezone.utc)
    run_id = now.strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:8]

    # Module hashes
    module_hashes = {}
    for mod_name in [
        "python_cal.config",
        "python_cal.topology.cdac_topology",
        "python_cal.topology.capacitor",
        "python_cal.topology.switch_state",
        "python_cal.topology.switching_policy",
        "python_cal.physical.charge_solver",
        "python_cal.physical.charge_state",
        "python_cal.physical.differential_cdac",
        "python_cal.decode.sar_decoder",
        "python_cal.comparator.dynamic_comparator",
        "python_cal.comparator.comparator_result",
        "python_cal.async_control.handshake",
        "python_cal.async_control.timing",
        "python_cal.async_control.events",
        "python_cal.async_control.sar_fsm",
        "python_cal.calibration.shen_calibrator",
        "python_cal.calibration.calibration_switching",
        "python_cal.calibration.calibration_controller",
        "python_cal.calibration.calibration_registers",
        "python_cal.conversion.async_sar_adc",
    ]:
        module_hashes[mod_name] = _hash_module(mod_name)

    git_state = _get_git_state(repo_dir)
    return RunManifest(
        run_id=run_id,
        timestamp_utc=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        git_commit=_get_git_commit(repo_dir),
        git_branch=git_state["branch"],
        git_dirty=git_state["dirty"],
        git_status_short=git_state["status_short"],
        git_status_count=git_state["status_count"],
        git_status_truncated=git_state["status_truncated"],
        config_hash=module_hashes.get("python_cal.config", "unknown"),
        topology_hash=module_hashes.get("python_cal.topology.cdac_topology", "unknown"),
        decoder_hash=module_hashes.get("python_cal.decode.sar_decoder", "unknown"),
        solver_hash=module_hashes.get("python_cal.physical.charge_solver", "unknown"),
        calibrator_hash=module_hashes.get("python_cal.calibration.shen_calibrator", "unknown"),
        comparator_hash=module_hashes.get("python_cal.comparator.dynamic_comparator", "unknown"),
        module_hashes=module_hashes,
        terminal_physical=False,
        random_seed=random_seed,
        fft_config={
            "n": fft_n,
            "k": fft_k,
            "fs_hz": fft_fs,
            "amplitude_dbfs": amp_dbfs,
        },
        dc_config={
            "binary_search_iter": dnl_iter,
            "method": "binary_search_per_transition",
            "n_transitions": 4095,
        },
        mc_config={
            "n_seeds": mc_seeds,
            "sigma_pct": mc_sigma_pct,
            "avg_pairs": avg_pairs,
            "cal_noise_lsb": cal_noise_lsb,
        },
        system_info={
            "python_version": sys.version,
            "platform": sys.platform,
            "numpy_version": _hash_module("numpy"),
        },
    )


def save_manifest(manifest: RunManifest, out_dir: str) -> str:
    """保存 run_manifest.json，返回文件路径"""
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"run_manifest_{manifest.run_id}.json")

    d = asdict(manifest)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(d, f, indent=2, ensure_ascii=False)

    return path


def save_manifest_compact(manifest: RunManifest, out_dir: str) -> str:
    """保存 run_manifest.json（单行紧凑格式），返回文件路径"""
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "run_manifest.json")

    d = asdict(manifest)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False)

    return path
