from __future__ import annotations

from pathlib import Path

import pandas as pd

from standard_agent.demo import generate_demo


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "training_data" / "factory_onboarding"


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)

    steel = generate_demo("steel_reheating_furnace", rows=120).add_prefix("新厂A_DCS_")
    steel.to_csv(OUTPUT / "新厂A_钢厂加热炉字段验收.csv", index=False, encoding="utf-8-sig")

    boiler = generate_demo("thermal_power_boiler", rows=120).add_prefix("新厂B_PLC_")
    mixed = pd.concat([steel.add_prefix("STEEL_"), boiler.add_prefix("BOILER_")], axis=1)
    mixed.to_csv(OUTPUT / "新厂B_锅炉与加热炉混合字段验收.csv", index=False, encoding="utf-8-sig")

    irrelevant = pd.DataFrame(
        {
            "会议室预约状态": [1, 0, 1],
            "打印机墨粉余量": [90, 82, 74],
            "值班员电子签名": ["甲", "乙", "丙"],
        }
    )
    irrelevant.to_csv(OUTPUT / "无关字段拒识验收.csv", index=False, encoding="utf-8-sig")

    (OUTPUT / "README.md").write_text(
        """# 新厂字段包接入验收数据

本目录为可重复生成的合成验收数据，不宣称为真实工厂数据。

- `新厂A_钢厂加热炉字段验收.csv`：验证新厂前缀和 DCS 包装后的单场景覆盖率。
- `新厂B_锅炉与加热炉混合字段验收.csv`：验证混合场景报警、字段簇分组与报告导出。
- `无关字段拒识验收.csv`：验证非工业过程字段不被错误接收。

在 Web 工作台导入后，可下载“覆盖率”和“场景分组”报告。
""",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
