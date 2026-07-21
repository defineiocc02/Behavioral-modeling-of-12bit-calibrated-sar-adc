from pathlib import Path

from virtuoso_bridge.spectre.runner import SpectreSimulator, spectre_mode_args


HERE = Path(__file__).resolve().parent
OUT = HERE / "spectre_closed_loop"


def main() -> int:
    sim = SpectreSimulator.from_env(
        spectre_args=spectre_mode_args("spectre"),
        work_dir=OUT,
        output_format="psfascii",
    )
    result = sim.run_simulation(
        HERE / "tb_DEC_CAL_PHY_closed_loop.scs",
        {
            "include_files": [
                HERE / "DEC_CAL_PHY.va",
                HERE / "SWITCH_CAL.va",
                HERE / "CAL_CMP_TB.va",
            ]
        },
    )
    print(f"status={result.status.value}")
    print(f"ok={result.ok}")
    if result.errors:
        print("errors:")
        for item in result.errors:
            print(item)
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
