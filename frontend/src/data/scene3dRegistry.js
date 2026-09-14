const defaultCamera = Object.freeze({ position: [15, 10, 17], target: [0, 2.7, 0], minDistance: 7, maxDistance: 42 })
const defaultTransform = Object.freeze({ scale: 1, position: [0, 0, 0], rotation: [0, 0, 0] })
const scene = (config) => Object.freeze({
  engine: 'three-webgl', asset_status: 'missing_3d_asset', model_url: null,
  camera: defaultCamera, transform: defaultTransform, lod: { mode: 'single_asset', level: 0 }, ...config,
})

export const SCENE_3D_REGISTRY = Object.freeze({
  industrial_dryer: scene({
    id: 'industrial_dryer', code: 'DR—03', label: '连续回转干燥系统', eyebrow: 'THERMAL DRYING',
    title: '连续回转干燥设备现场', description: '回转干燥筒、进料、热风、风机、尾气、出料、平台和工艺管线组成的真实空间结构。', accent: '#e7a45d',
    asset_status: 'installed', model_url: '/models/industrial_dryer.glb', asset_format: 'glb',
    asset_license: '3D Warehouse General Model License · Combined Work', asset_author: 'Alibre Design', asset_version: 4,
    asset_source: 'https://3dwarehouse.sketchup.com/model/ec181059cdc3036a5970eada872fb5c/Industrial-Rotary-Dryer',
    camera: { position: [31, 18, 31], target: [0, 3.6, 0], minDistance: 8, maxDistance: 68 },
    lod: { mode: 'component_visibility', detail_node: 'maintenance_platform', hide_beyond: 120 },
    semantic_nodes: [
      { id: 'dryer_drum', mesh_name: 'dryer_drum', label: '回转干燥筒', module: '干燥主机', description: '湿料在筒体翻动中与热风换热，托轮、齿圈和驱动电机共同维持连续运行。', palette: { base: '#737b7d', metalness: .78, roughness: .42, highlight: '#ff8a2a' }, fields: ['drum_speed', 'product_temperature'], dynamics: { rotate: 'drum_speed', heat: 'product_temperature' } },
      { id: 'feed_hopper', mesh_name: 'feed_hopper', label: '湿料进料系统', module: '进料段', description: '进料罩与密封组件将湿料稳定送入回转筒，减少热风泄漏和物料外逸。', palette: { base: '#536b70', metalness: .58, roughness: .5, highlight: '#ffb13b' }, fields: ['wet_feed_rate'], dynamics: { activity: 'wet_feed_rate' } },
      { id: 'air_heater', mesh_name: 'air_heater', label: '热风入口与调节', module: '热风系统', description: '源 CAD 中的空气过滤器和风门总成，负责入口空气组织与流量调节。', palette: { base: '#574f46', metalness: .45, roughness: .62, highlight: '#ff5a36' }, fields: ['hot_air_temperature', 'inlet_air_temperature', 'outlet_air_temperature'], dynamics: { heat: 'hot_air_temperature' } },
      { id: 'supply_fan', mesh_name: 'supply_fan', label: '热风风机', module: '热风系统', description: '离心风机建立干燥空气流量与压力，向筒体持续输送工艺风。', palette: { base: '#2d6275', metalness: .64, roughness: .46, highlight: '#29c7ff' }, fields: ['drying_air_flow'], dynamics: { rotate: 'drying_air_flow' } },
      { id: 'exhaust_outlet', mesh_name: 'exhaust_outlet', label: '尾气分离与排出', module: '尾气系统', description: '双旋风分离器、引风机与烟囱对含尘尾气进行分离和排放。', palette: { base: '#455b64', metalness: .68, roughness: .48, highlight: '#35d0c1' }, fields: ['exhaust_temperature', 'exhaust_humidity'], dynamics: { heat: 'exhaust_temperature' } },
      { id: 'product_outlet', mesh_name: 'product_outlet', label: '产品出料系统', module: '出料段', description: '出料罩和密封件接收干燥产品，其温度和含水率是主要质量指标。', palette: { base: '#6b6155', metalness: .5, roughness: .58, highlight: '#f4c542' }, fields: ['product_moisture', 'product_temperature'], dynamics: { state: 'product_moisture' } },
      { id: 'process_piping', mesh_name: 'process_piping', label: '工艺连接管线', module: '连接系统', description: '直管、弯头、变径和分流件连接风机、筒体与尾气处理设备。', palette: { base: '#50636a', metalness: .74, roughness: .4, highlight: '#44aaff' }, fields: ['drying_air_flow', 'exhaust_temperature'], dynamics: { flow: 'drying_air_flow' } },
      { id: 'maintenance_platform', mesh_name: 'maintenance_platform', label: '维护平台与支撑', module: '设备结构', description: '主钢架、旋风支架、基础和立柱承担设备荷载并提供检修空间。', palette: { base: '#3d4b50', metalness: .42, roughness: .68, highlight: '#ffd447' }, fields: [] },
    ],
    flows: [['feed_hopper', 'dryer_drum'], ['supply_fan', 'air_heater'], ['air_heater', 'dryer_drum'], ['dryer_drum', 'exhaust_outlet'], ['dryer_drum', 'product_outlet']],
  }),
  blast_furnace: scene({
    id: 'blast_furnace', code: 'BF—01', label: '高炉炼铁系统', eyebrow: 'IRONMAKING PROCESS', title: '高炉炼铁设备现场',
    description: '高炉本体、炉顶装料、热风炉、煤气除尘、出铁场和运输轨道组成的完整炼铁现场。', accent: '#ef8150',
    asset_status: 'installed', model_url: '/models/blast_furnace.glb', asset_format: 'glb',
    asset_license: 'ProcessPilot original reference-based asset', asset_author: 'ProcessPilot', asset_version: 1,
    asset_source: 'https://3dwarehouse.sketchup.com/model/0481c007-bad9-4ed1-a3a8-a478bc9e83fd/Blast-Furnace',
    camera: { position: [35, 24, 36], target: [1.5, 10, 1], minDistance: 9, maxDistance: 95 },
    semantic_nodes: [
      { id: 'furnace_body', mesh_name: 'furnace_body', label: '高炉本体', module: '炉体', description: '炉腹、炉腰、炉身和炉喉形成连续反应空间，环向加劲与检修平台表达真实炉壳结构。', palette: { base: '#76564a', metalness: .66, roughness: .46, highlight: '#ff7548' }, fields: ['total_pressure_drop', 'upper_pressure_drop', 'lower_pressure_drop'] },
      { id: 'burden_system', mesh_name: 'burden_system', label: '炉顶装料', module: '炉顶系统', description: '料车斜桥、受料斗、布料器和四路炉顶煤气导出管共同组成炉顶工艺系统。', palette: { base: '#59666b', metalness: .72, roughness: .42, highlight: '#ffd24c' }, fields: ['top_gas_pressure', 'top_gas_co2', 'top_gas_h2'] },
      { id: 'hot_blast', mesh_name: 'hot_blast', label: '热风与富氧', module: '鼓风系统', description: '三座热风炉经热风总管、围管和十二支风口向炉缸稳定供给高温富氧鼓风。', palette: { base: '#526b72', metalness: .68, roughness: .4, highlight: '#ff8b38' }, fields: ['blast_flow_rate', 'hot_blast_pressure', 'hot_blast_temperature', 'oxygen_flow_rate'] },
      { id: 'hearth', mesh_name: 'hearth', label: '炉缸与出铁场', module: '出铁系统', description: '炉缸、出铁沟、出铁场厂房、煤气重力除尘器和铁水运输轨道构成下部生产区域。', palette: { base: '#3f494d', metalness: .58, roughness: .55, highlight: '#ff4e2a' }, fields: ['hot_metal_silicon_content'] },
    ], flows: [['burden_system', 'furnace_body'], ['hot_blast', 'furnace_body'], ['furnace_body', 'hearth']],
  }),
  thermal_power_boiler_long_tail: scene({
    id: 'thermal_power_boiler_long_tail', code: 'TB—31', label: '热电锅炉长尾系统', eyebrow: 'THERMAL POWER BOILER', title: '热电锅炉设备现场',
    description: '当前场景已识别为热电锅炉长尾系统，但真实锅炉 GLB 模型资产尚未安装。', accent: '#ff9b64', required_asset: 'thermal_power_boiler.glb',
    semantic_nodes: [
      { id: 'fan_group', mesh_name: 'fan_group', label: '送引风机组', module: '风机系统', fields: ['secondary_fan_outlet_flow', 'primary_fan_outlet_flow'] },
      { id: 'boiler_furnace', mesh_name: 'boiler_furnace', label: '锅炉炉膛', module: '燃烧系统', fields: ['upper_furnace_temperature_right', 'upper_furnace_pressure_a', 'upper_furnace_pressure_b'] },
      { id: 'steam_drum', mesh_name: 'steam_drum', label: '汽包与蒸汽出口', module: '汽水系统', fields: ['container_outlet_vapour_pressure', 'pot_pressure_left'] },
      { id: 'economizer', mesh_name: 'economizer', label: '省煤器', module: '尾部烟道', fields: ['economizer_outlet_flue_gas_temperature_left'] },
      { id: 'air_preheater', mesh_name: 'air_preheater', label: '空预器与烟道', module: '尾部烟道', fields: ['primary_air_preheater_outlet_temperature'] },
    ], flows: [['fan_group', 'boiler_furnace'], ['boiler_furnace', 'steam_drum'], ['boiler_furnace', 'economizer'], ['economizer', 'air_preheater']],
  }),
  debutanizer_column: scene({
    id: 'debutanizer_column', code: 'DC—04', label: '脱丁烷精馏装置', eyebrow: 'REFINERY SEPARATION', title: '脱丁烷精馏设备现场',
    description: '精馏塔本体、塔顶冷凝、回流、塔底再沸和进料管廊组成的连续脱丁烷装置。', accent: '#61a8d8',
    asset_status: 'installed', model_url: '/models/debutanizer_column.glb', asset_format: 'glb',
    asset_license: 'ProcessPilot original reference-based asset', asset_author: 'ProcessPilot', asset_version: 1,
    asset_source: 'https://sketchfab.com/3d-models/cellier-blumenthal-distillation-column-623d365bf31b4d139d7cc5a8cdc37f7d',
    camera: { position: [31, 21, 33], target: [0, 11, 0], minDistance: 8, maxDistance: 85 },
    semantic_nodes: [
      { id: 'column_shell', mesh_name: 'column_shell', label: '精馏塔本体', module: '分离段', description: '立式塔壳、椭圆封头、塔盘环、仪表嘴、分层平台和通高爬梯共同表达精馏分离主体。', palette: { base: '#8d9da2', metalness: .84, roughness: .28, highlight: '#5fc7ff' }, fields: ['tray6_temperature', 'top_temperature', 'top_pressure'] },
      { id: 'condenser', mesh_name: 'condenser', label: '塔顶冷凝器', module: '塔顶系统', description: '卧式管壳冷凝器通过塔顶蒸气管线回收轻组分，并将凝液送往回流罐。', palette: { base: '#3f768e', metalness: .7, roughness: .38, highlight: '#48cfff' }, fields: ['top_temperature', 'top_pressure'] },
      { id: 'reflux_drum', mesh_name: 'reflux_drum', label: '回流罐与泵组', module: '回流系统', description: '卧式回流罐、双泵和回流返回管线稳定塔顶液相循环。', palette: { base: '#66777d', metalness: .74, roughness: .36, highlight: '#43b9ff' }, fields: ['reflux_flow'] },
      { id: 'reboiler', mesh_name: 'reboiler', label: '塔底再沸器', module: '塔底系统', description: '卧式釜式再沸器通过塔底液相入口、蒸气返回和加热介质管线向塔内提供上升蒸气。', palette: { base: '#986044', metalness: .63, roughness: .43, highlight: '#ff8b42' }, fields: ['bottom_temperature_a', 'bottom_temperature_b', 'bottom_butane_content'] },
      { id: 'feed_line', mesh_name: 'feed_line', label: '进料与公用管廊', module: '进料段', description: '钢结构管廊、主进料管、公用工程总管和现场阀组将上游物流接入中部塔盘。', palette: { base: '#435b66', metalness: .64, roughness: .46, highlight: '#76d8ff' }, fields: ['next_process_flow'] },
    ], flows: [['feed_line', 'column_shell'], ['column_shell', 'condenser'], ['condenser', 'reflux_drum'], ['column_shell', 'reboiler']],
  }),
  steel_industry_energy: scene({
    id: 'steel_industry_energy', code: 'SE—09', label: '钢铁企业能源系统', eyebrow: 'ENERGY DISTRIBUTION', title: '钢铁能源设备现场',
    description: '当前数据属于钢铁能源场景，但尚未配置适用的真实三维设备资产。', accent: '#5faee5', required_asset: 'steel_industry_energy.glb', semantic_nodes: [], flows: [],
  }),
  vapor_pressure_soft_sensor: scene({
    id: 'vapor_pressure_soft_sensor', code: 'VP—30', label: '蒸气压力软测量', eyebrow: 'SOFT SENSOR ARRAY', title: '蒸气压力软测量现场',
    description: '当前数据属于蒸气压力软测量场景，但尚未配置适用的真实三维设备资产。', accent: '#70c7c1', required_asset: 'vapor_pressure_soft_sensor.glb', semantic_nodes: [], flows: [],
  }),
})

export const UNKNOWN_SCENE_3D = scene({
  id: 'unknown_scene', code: 'SC—?', label: '未知数据场景', eyebrow: 'SCENE UNRESOLVED', title: '尚未确认工业场景',
  description: '当前数据场景尚未确认，不能选择真实三维设备模型。', accent: '#7e93a8', required_asset: null, semantic_nodes: [], flows: [],
})

export function getScene3DDescriptor(sceneId) {
  return SCENE_3D_REGISTRY[sceneId] || UNKNOWN_SCENE_3D
}

export function buildScene3DState(sceneState) {
  // Before a CSV run exists there is no data-scene evidence yet. In that
  // state, preview the explicitly selected project scene instead of showing
  // an unrelated "unknown scene" canvas. A detected data scene always wins.
  const requestedId = sceneState?.data_scene?.id || sceneState?.project_scene?.id
  const descriptor = getScene3DDescriptor(requestedId)
  return {
    descriptor,
    isKnown: descriptor !== UNKNOWN_SCENE_3D,
    hasAsset: descriptor.asset_status === 'installed' && Boolean(descriptor.model_url),
    requestedId: requestedId || null,
    source: sceneState?.data_scene?.id ? 'data_scene' : sceneState?.project_scene?.id ? 'project_preview' : 'unresolved',
    status: descriptor.asset_status,
  }
}

export function resolveScene3DView(sceneState, preferredScope = 'auto') {
  const dataId = sceneState?.data_scene?.id || null
  const projectId = sceneState?.project_scene?.id || null
  const dataDescriptor = getScene3DDescriptor(dataId)
  const projectDescriptor = getScene3DDescriptor(projectId)
  const dataHasAsset = dataDescriptor.asset_status === 'installed' && Boolean(dataDescriptor.model_url)
  const projectHasAsset = projectDescriptor.asset_status === 'installed' && Boolean(projectDescriptor.model_url)

  let scope = preferredScope
  if (scope === 'auto') scope = dataId && dataHasAsset ? 'data' : projectId && projectHasAsset ? 'project' : dataId ? 'data' : 'project'
  if (scope === 'data' && !dataId) scope = 'project'
  if (scope === 'project' && !projectId) scope = 'data'

  const descriptor = scope === 'data' ? dataDescriptor : projectDescriptor
  return {
    scope,
    descriptor,
    dataHasAsset,
    projectHasAsset,
    usedProjectFallback: preferredScope === 'auto' && scope === 'project' && Boolean(dataId) && !dataHasAsset,
    sceneState: scope === 'data'
      ? sceneState
      : { ...sceneState, data_scene: { ...(sceneState?.data_scene || {}), id: null } },
  }
}

export function listMissingSceneAssets() {
  return Object.values(SCENE_3D_REGISTRY).filter((item) => item.asset_status !== 'installed').map((item) => ({ scene_id: item.id, required_asset: item.required_asset }))
}
