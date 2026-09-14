# 本地真实数据库存

使用 rg --files --hidden --no-ignore 搜索，排除 .git/.venv/node_modules/__pycache__；扫描 datasets、training、演示数据、runtime、reports、docs、integrations 及来源/manifest/历史候选文档。检索命中 3734 个数据或来源相关路径，包含大量历史运行衍生产物，不是 3734 份独立实测数据。

完整路径清单：datasets/real_validation/local_file_inventory.txt。历史 30 个来源逐项核对实际文件是否存在与 SHA256，8 个代表数据文件本轮运行 precheck；新增烟草 subset 有独立原文件记录。

| 来源 | 文件状态 | 可信分类 | SHA256 |
| --- | --- | --- | --- |
| Fixed Mendeley derived 720h | ACQUIRED_FILE | DERIVED_REAL | 337389aab42fa898d018d432dd5383fd2b48c4780890b9e3a9cb61d00dbfdaa2 |
| Fortuna 文本镜像 | ACQUIRED_FILE | BENCHMARK_REAL | e963abcd668e2bc3282815ffd21f73b4b4ccd89d34600feaecc6d5a42aad3438 |
| Coimbra 大学原始 MAT 包 | ACQUIRED_FILE | BENCHMARK_REAL | f8cd1e3c2f58f0e87ce2c78e90764efabffa3ce1231e8e1fc97367e2e8636fc0 |
| DC-dataset CSV 镜像 | ACQUIRED_FILE | BENCHMARK_REAL | ea9f660ad4f99a82f14249d7db9d376582f9b4572295c7b85d6872e12e9b274c |
| LostRunes DB DATA-B | ACQUIRED_FILE | UNKNOWN | f3ae03e28f29f2b0b29fe932a5833603c5bdbae48af6ba85c0369be0a920c60b |
| 本地 360 行 raw sample | ACQUIRED_FILE | UNKNOWN | 3679519020df3acf090047019a11c37b0e9f4fefb7747016660a68a7d2d9e629 |
| Danny-Taehyun-Kim hybrid demo | SOURCE_REFERENCE_ONLY | SYNTHETIC | None |
| LPG composition paper | SOURCE_REFERENCE_ONLY | UNKNOWN | None |
| Column flooding paper | SOURCE_REFERENCE_ONLY | UNKNOWN | None |
| Fortuna 其他复用仓库 | SOURCE_REFERENCE_ONLY | UNKNOWN | None |
| DAISY 96-016 industrial dryer | ACQUIRED_FILE | PUBLIC_REAL_PROCESS | 0000546d78f737a8a33bf91ae62235fa8848a730b660ef1a25a4fda12d3b064f |
| Coffee microwave/oven temperature experiment | ACQUIRED_FILE | PUBLIC_EXPERIMENT | 60f8e07c8987ad1f37aa40458dcca9dac5bb4a62d0c247797aac6bd98f53d30b |
| Filter media drying moisture | SOURCE_REFERENCE_ONLY | UNKNOWN | None |
| Solar multipurpose dryer | SOURCE_REFERENCE_ONLY | UNKNOWN | None |
| Solar biomass fish dryer | SOURCE_REFERENCE_ONLY | UNKNOWN | None |
| Industrial laundry exhaust | SOURCE_REFERENCE_ONLY | UNKNOWN | None |
| LARCO tumble dryers | SOURCE_REFERENCE_ONLY | UNKNOWN | None |
| WUR EHD dryer model | SOURCE_REFERENCE_ONLY | UNKNOWN | None |
| Rotary potash dryer paper | SOURCE_REFERENCE_ONLY | UNKNOWN | None |
| Batch rotary NARX paper | SOURCE_REFERENCE_ONLY | UNKNOWN | None |
| Rotary nickel CO paper | SOURCE_REFERENCE_ONLY | UNKNOWN | None |
| 本地 867 行合成验收集 | ACQUIRED_FILE | SYNTHETIC | 798660db9fa687d87c064c31dbeeb8bac98c68d529ae24d74cf6bd426d86cad1 |
| 本地 360 行 dryer raw sample | ACQUIRED_FILE | SYNTHETIC | 7e1274d4c3aae044ec80d982e0ca154345294fcab063f6bed0ef4472894dad80 |
| StevenShaw98 Fortuna CSV | ACQUIRED_FILE | BENCHMARK_REAL | 15897d2b086cf5e9ffcdb9e879bffcc6e6f9c96d4688f30503f8091893a5de7f |
| Basque refinery pentanes classification | SOURCE_REFERENCE_ONLY | UNKNOWN | None |
| UTP CRU debutanizer thesis | SOURCE_REFERENCE_ONLY | UNKNOWN | None |
| Tobacco Primary Processing data2 | SOURCE_REFERENCE_ONLY | UNKNOWN | None |
| Solar dryer with thermal storage | SOURCE_REFERENCE_ONLY | UNKNOWN | None |
| Kiln beech-chip residence time | SOURCE_REFERENCE_ONLY | UNKNOWN | None |
| Cassava dryer IoT design files | SOURCE_REFERENCE_ONLY | UNKNOWN | None |
| KLD-2 tobacco processed subset / transformer-lstm | ACQUIRED_FILE | DERIVED_REAL | 997e73bbf88854af528739019a62f93262e9a52c9dfc1ca34e453244dde4ee43 |

没有重新下载已有 Fortuna、LostRunes、DAISY、coffee 或镜像。重新读取 DAISY 原说明、Fortuna archive 目录、既有 SOURCE/转换元数据及固定高炉 manifest。runtime 内各次标准化 CSV/模型 artifact 是来源的衍生缓存，不当作新真实数据。没有原文件的条目全部 SOURCE_REFERENCE_ONLY。
