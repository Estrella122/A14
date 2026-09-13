const scene = (config) => Object.freeze({ engine: 'dom-css3d', lod: 'semantic-equipment', ...config })

export const SCENE_3D_REGISTRY = Object.freeze({
  debutanizer_column: scene({
    id: 'debutanizer_column', code: 'DC—04', label: '脱丁烷精馏装置', eyebrow: 'REFINERY SEPARATION',
    title: '脱丁烷精馏过程结构', description: '塔顶冷凝回流、塔板分离与塔底再沸的物料和能量通路。', accent: '#61a8d8', ambient: 'rgba(73,151,205,.2)',
    nodes: [
      { id: 'feed', label: '进料管线', shape: 'pipe', x: 18, y: 52, fields: ['next_process_flow'], module: '进料段' },
      { id: 'column', label: '精馏塔板区', shape: 'column', x: 47, y: 43, fields: ['tray6_temperature', 'top_temperature', 'top_pressure'], module: '分离段' },
      { id: 'condenser', label: '塔顶冷凝器', shape: 'exchanger', x: 76, y: 23, fields: ['top_temperature', 'top_pressure'], module: '塔顶系统' },
      { id: 'reflux', label: '回流罐', shape: 'vessel', x: 82, y: 43, fields: ['reflux_flow'], module: '回流系统' },
      { id: 'reboiler', label: '塔底再沸器', shape: 'exchanger', x: 71, y: 73, fields: ['bottom_temperature_a', 'bottom_temperature_b', 'bottom_butane_content'], module: '塔底系统' },
    ], flows: [['feed', 'column'], ['column', 'condenser'], ['condenser', 'reflux'], ['reflux', 'column'], ['column', 'reboiler']],
  }),
  thermal_power_boiler_long_tail: scene({
    id: 'thermal_power_boiler_long_tail', code: 'TB—31', label: '热电锅炉长尾系统', eyebrow: 'THERMAL POWER BOILER',
    title: '热电锅炉风烟与汽水系统', description: '从送引风、炉膛燃烧到省煤器和蒸汽出口的多测点运行结构。', accent: '#ff9b64', ambient: 'rgba(255,126,72,.2)',
    nodes: [
      { id: 'fans', label: '送风与引风机组', shape: 'fan', x: 17, y: 62, fields: ['secondary_fan_outlet_flow', 'primary_fan_outlet_flow'], module: '风机系统' },
      { id: 'furnace', label: '锅炉炉膛', shape: 'boiler', x: 45, y: 45, fields: ['upper_furnace_temperature_right', 'upper_furnace_pressure_a', 'upper_furnace_pressure_b'], module: '燃烧系统' },
      { id: 'drum', label: '汽包与蒸汽出口', shape: 'drum', x: 59, y: 18, fields: ['container_outlet_vapour_pressure', 'pot_pressure_left'], module: '汽水系统' },
      { id: 'economizer', label: '省煤器', shape: 'exchanger', x: 76, y: 48, fields: ['economizer_outlet_flue_gas_temperature_left', 'economizer_outlet_flue_gas_temperature_right'], module: '尾部烟道' },
      { id: 'stack', label: '空预器与烟道', shape: 'stack', x: 88, y: 24, fields: ['primary_air_preheater_outlet_temperature'], module: '尾部烟道' },
    ], flows: [['fans', 'furnace'], ['furnace', 'drum'], ['furnace', 'economizer'], ['economizer', 'stack']],
  }),
  industrial_dryer: scene({
    id: 'industrial_dryer', code: 'DR—03', label: '连续回转干燥系统', eyebrow: 'THERMAL DRYING',
    title: '连续热风干燥过程结构', description: '湿料给入、热风换热、回转输送与产品水分的耦合关系。', accent: '#d9ad67', ambient: 'rgba(210,157,75,.2)',
    nodes: [
      { id: 'hopper', label: '湿料进料斗', shape: 'hopper', x: 14, y: 37, fields: ['wet_feed_rate'], module: '进料段' },
      { id: 'heater', label: '空气加热器', shape: 'heater', x: 22, y: 72, fields: ['hot_air_temperature', 'drying_air_flow'], module: '热风系统' },
      { id: 'drum', label: '回转干燥筒', shape: 'dryer', x: 52, y: 50, fields: ['product_temperature'], module: '干燥主机' },
      { id: 'exhaust', label: '尾气出口', shape: 'stack', x: 78, y: 25, fields: ['exhaust_humidity'], module: '尾气系统' },
      { id: 'product', label: '产品出料', shape: 'conveyor', x: 85, y: 68, fields: ['product_moisture', 'product_temperature'], module: '出料段' },
    ], flows: [['hopper', 'drum'], ['heater', 'drum'], ['drum', 'exhaust'], ['drum', 'product']],
  }),
  blast_furnace: scene({
    id: 'blast_furnace', code: 'BF—01', label: '高炉炼铁系统', eyebrow: 'IRONMAKING PROCESS',
    title: '高炉炼铁过程结构', description: '装料、鼓风、炉内反应、煤气与铁水质量的工艺通路。', accent: '#ef8150', ambient: 'rgba(239,103,57,.22)',
    nodes: [
      { id: 'burden', label: '炉顶装料', shape: 'hopper', x: 46, y: 13, fields: ['top_gas_pressure', 'top_gas_co2', 'top_gas_h2'], module: '炉顶系统' },
      { id: 'furnace', label: '高炉本体', shape: 'blast-furnace', x: 49, y: 48, fields: ['total_pressure_drop', 'upper_pressure_drop', 'lower_pressure_drop'], module: '炉体' },
      { id: 'blast', label: '热风与富氧', shape: 'fan', x: 17, y: 62, fields: ['blast_flow_rate', 'hot_blast_pressure', 'hot_blast_temperature', 'oxygen_flow_rate'], module: '鼓风系统' },
      { id: 'hearth', label: '炉缸与出铁口', shape: 'vessel', x: 70, y: 74, fields: ['hot_metal_silicon_content'], module: '出铁系统' },
    ], flows: [['burden', 'furnace'], ['blast', 'furnace'], ['furnace', 'hearth']],
  }),
  steel_industry_energy: scene({
    id: 'steel_industry_energy', code: 'SE—09', label: '钢铁企业能源系统', eyebrow: 'ENERGY DISTRIBUTION',
    title: '钢铁能源与负荷网络', description: '有功能耗、无功电量、功率因数与生产负荷的运行视图。', accent: '#5faee5', ambient: 'rgba(69,153,214,.2)',
    nodes: [
      { id: 'grid', label: '厂区进线', shape: 'substation', x: 16, y: 45, fields: ['energy_usage'], module: '供配电' },
      { id: 'reactive', label: '无功补偿', shape: 'vessel', x: 42, y: 68, fields: ['lagging_reactive_energy', 'leading_reactive_energy'], module: '无功补偿' },
      { id: 'loads', label: '生产负荷', shape: 'factory', x: 63, y: 43, fields: ['load_type', 'lagging_power_factor', 'leading_power_factor'], module: '生产用能' },
      { id: 'emission', label: '碳排算', shape: 'stack', x: 86, y: 30, fields: ['co2_emission'], module: '能碳管理' },
    ], flows: [['grid', 'reactive'], ['grid', 'loads'], ['loads', 'emission']],
  }),
  vapor_pressure_soft_sensor: scene({
    id: 'vapor_pressure_soft_sensor', code: 'VP—30', label: '蒸气压力软测量', eyebrow: 'SOFT SENSOR ARRAY',
    title: '多温区蒸气压力软测量', description: '多点温度阵列与蒸气压力估计的数据采集结构。', accent: '#70c7c1', ambient: 'rgba(63,184,175,.18)',
    nodes: [
      { id: 'temperature-array', label: '多点温度阵列', shape: 'sensor-array', x: 30, y: 48, fields: Array.from({ length: 27 }, (_, i) => `temperature_${String(i + 1).padStart(2, '0')}`), module: '温度采集' },
      { id: 'soft-sensor', label: '软测量计算单元', shape: 'processor', x: 62, y: 47, fields: ['hours_elapsed'], module: '软测量' },
      { id: 'pressure-output', label: '蒸气压力输出', shape: 'gauge', x: 84, y: 47, fields: ['vapor_pressure'], module: '输出端' },
    ], flows: [['temperature-array', 'soft-sensor'], ['soft-sensor', 'pressure-output']],
  }),
})

export const UNKNOWN_SCENE_3D = scene({
  id: 'unknown_scene', code: 'SC—?', label: '未知数据场景', eyebrow: 'SCENE UNRESOLVED', title: '尚未确认工业场景',
  description: '当前数据没有可用的场景模型；完成场景识别后将自动加载对应设备结构。', accent: '#7e93a8', ambient: 'rgba(111,137,161,.16)', nodes: [], flows: [],
})

export function getScene3DDescriptor(sceneId) {
  return SCENE_3D_REGISTRY[sceneId] || UNKNOWN_SCENE_3D
}

export function buildScene3DState(sceneState) {
  const requestedId = sceneState?.data_scene?.id
  const descriptor = getScene3DDescriptor(requestedId)
  return { descriptor, isKnown: descriptor !== UNKNOWN_SCENE_3D, requestedId: requestedId || null }
}
