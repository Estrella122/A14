# A14 真实三维场景迁移报告

## 结论

`/digital-twin` 已从 DOM/CSS 几何示意切换为 Three.js WebGL + GLB 运行时，并将工业干燥器场景替换为真实工程 CAD。当前生产 GLB 由 3D Warehouse 的 **Industrial Rotary Dryer**（Alibre Design）转换而来，包含回转筒、托轮、齿圈、驱动、进出料罩、双旋风分离器、风机、烟囱、管道、钢结构和基础。源模型在线信息为 53,631 polygons、103 materials；Collada 中实际导入 5,931 个网格和 121 个材质。

## 旧实现审计

旧版 `SceneModel3D.vue` 使用 DOM 元素、CSS transform 和 `shape-*`/`equipment-body` 样式拼装设备外观；`scene3dRegistry.js` 的引擎为 `dom-css3d`，没有 GLB/GLTF 资产、GLTFLoader、真实网格拾取或模型生命周期管理。因此视觉上是抽象积木，不能表达真实机械结构。

## 当前运行链

1. `DigitalTwinView.vue` 从统一 SceneState 读取 `data_scene.id`，项目场景仍独立显示。
2. `scene3dRegistry.js` 根据数据场景选择模型资产和语义节点。
3. `SceneModel3D.vue` 动态加载 GLTFLoader、DRACOLoader、MeshoptDecoder 和 OrbitControls。
4. GLB 加载后按 `mesh_name` 建立字段到设备网格的映射；点击列表或模型会聚焦对应设备。
5. 当前流水线快照的标准字段驱动温度、风量、转速等视觉状态，并在设备检查卡显示真实值。
6. 模型按 URL + `asset_version` 缓存；场景切换和组件销毁时释放克隆的 geometry、material、texture 和 WebGL context。

## 真实 CAD 迁移与许可

- 来源：[Industrial Rotary Dryer — 3D Warehouse](https://3dwarehouse.sketchup.com/model/ec181059cdc3036a5970eada872fb5c/Industrial-Rotary-Dryer)
- 作者：Alibre Design
- 许可：[3D Warehouse General Model License](https://3dwarehouse.sketchup.com/tos)
- 使用方式：模型被纳入 ProcessPilot Combined Work，并增加语义结构、数据绑定、交互、UI、运行时和压缩处理。
- 原始 DAE/ZIP 不进入仓库；仓库只保存转换后的应用资产和可复现转换脚本。

转换脚本保留 Collada 装配变换，将 5,931 个源网格按设备语义归并为 8 个运行时根节点，并执行坐标归一、材质规范化和 Draco 压缩。GLB 当前约 705 KB。`air_heater` 对应源 CAD 中真实存在的空气入口过滤器与风门；源 CAD 没有独立燃烧器壳体，页面不伪造该部件。

## 语义节点

| 运行时节点 | CAD 部件示例 | 数据字段示例 |
| --- | --- | --- |
| `dryer_drum` | SHELL、托轮、轴承、齿圈、电机、齿轮罩 | `drum_speed`, `product_temperature` |
| `feed_hopper` | 进料罩、进料密封 | `wet_feed_rate` |
| `air_heater` | 空气过滤器、风门 | `hot_air_temperature` |
| `supply_fan` | BCS-222 风机、风机基础、出口 | `drying_air_flow` |
| `exhaust_outlet` | 双旋风、LS-2021 风机、烟囱 | `exhaust_temperature`, `exhaust_humidity` |
| `product_outlet` | 出料罩、出料密封 | `product_moisture`, `product_temperature` |
| `process_piping` | 直管、弯头、变径、分流、支架 | `drying_air_flow`, `exhaust_temperature` |
| `maintenance_platform` | 主钢架、旋风支架、基础、立柱 | 无强制数据字段 |

## 交互、性能和失败状态

- 支持左键旋转、滚轮缩放、右键平移、复位相机、模型拾取和设备列表聚焦。
- 初始相机根据核心设备真实边界自动取景，避免资产更换后被固定坐标裁切。
- 远距 LOD 只处理维护结构，不隐藏核心工艺设备。
- 没有模型的场景明确返回 `missing_3d_asset`，仅在用户点击后显示标明“非真实 3D 模型”的简化示意，不静默伪装为真实模型。
- 模型请求带 `asset_version` 缓存键，替换 GLB 后不会继续显示旧浏览器缓存。

## 真实浏览器验收

在 `127.0.0.1:5176/digital-twin`、Django `127.0.0.1:8000` 下完成：

- 工业干燥器 GLB 成功加载，页面状态为“GLB 已加载”。
- 项目预设为高炉、数据场景为工业干燥器时仍显示非阻塞场景不一致提示，三维资产按数据场景选择。
- 八个语义设备按钮均可聚焦；“回转干燥筒”显示当前快照 `product_temperature = 82.39 degC` 和“实时数据已绑定”。
- OrbitControls 旋转、缩放、平移及相机复位均可用。
- 浏览器控制台：0 errors，0 warnings。
- 未安装资产场景：显示 `missing_3d_asset`，不会回退成未标注的假模型。

## 验证结果

- ESLint 与项目静态检查：通过，41 个 JavaScript/Vue 文件。
- 前端测试：27/27 通过。
- Vite production build：通过。
- Three.js 主包约 524.5 KB（gzip 131.25 KB），通过路由分包只在三维页面使用；构建仍报告单个未压缩 chunk 超过 500 KB 的提示，不影响运行。

## 修改文件

- `frontend/src/components/SceneModel3D.vue`
- `frontend/src/data/scene3dRegistry.js`
- `frontend/src/views/DigitalTwinView.vue`
- `frontend/public/models/industrial_dryer.glb`
- `frontend/public/models/README.md`
- `frontend/public/draco/*`
- `frontend/scripts/importIndustrialDryerCad.py`
- `frontend/scripts/importIndustrialDryerCad.sh`
- `frontend/tests/scene3dRegistry.test.mjs`
- `frontend/package.json`
- `frontend/package-lock.json`

## 剩余边界

当前只有工业干燥器具备可核验来源的真实 GLB。高炉、锅炉、脱丁烷塔、钢铁能源和蒸气压力场景仍明确标记缺少资产，需要分别取得合法模型后按同一 Registry 接口安装。本次没有用程序化几何冒充这些场景。

## 点击特写与初始视角补充修复

- 从原 CAD 建筑基础的几何分布恢复真实地面法向，在 GLB 导出前自动对齐竖直轴，解决初始视角中地面竖起、设备倾斜和构图裁切。
- 初始相机以回转筒、进出料与送风设备为核心自动取景，超长烟囱和连接管线不再把主设备压缩成小图。
- 点击任一设备后执行 620 ms 平滑近景动画，特写距离根据该节点边界计算，用户操作可立即中断动画。
- 说明卡移到画布右上角，无需向下滚动即可看到；展示设备用途、工艺关系、语义节点、当前测点值和数据绑定状态。
