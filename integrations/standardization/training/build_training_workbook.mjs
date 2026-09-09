import fs from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const root = fileURLToPath(new URL("../", import.meta.url));
const payload = JSON.parse(await fs.readFile(`${root}training_data/workbook_payload.json`, "utf8"));
const metrics = JSON.parse(await fs.readFile(`${root}models/training_metrics.json`, "utf8"));
const outputDir = `${root}outputs/A14_task2`;
const previewDir = `${outputDir}/qa_previews`;
await fs.mkdir(previewDir, { recursive: true });

const workbook = Workbook.create();
const summary = workbook.worksheets.add("概览");
const samples = workbook.worksheets.add("字段训练样本");
const intents = workbook.worksheets.add("场景意图样本");
const dictionary = workbook.worksheets.add("多场景数据字典");
const labels = workbook.worksheets.add("标签说明");

const colors = { header: "#21617A", section: "#DCECF1", ink: "#17232B", muted: "#5F6F77", green: "#E5F2EA", amber: "#FFF1D6" };
for (const sheet of [summary, samples, intents, dictionary, labels]) sheet.showGridLines = false;

summary.getRange("A1:F1").merge();
summary.getRange("A1").values = [["A14 多场景字段需求判定 Agent 训练数据包"]];
summary.getRange("A1:F1").format = { fill: colors.header, font: { bold: true, color: "#FFFFFF", size: 18 }, rowHeight: 34, verticalAlignment: "center" };
summary.getRange("A3:B8").values = [
  ["指标", "结果"],
  ["工业场景", payload.manifest.scenarios.length],
  ["标准字段类别", metrics.model.labels],
  ["字段语义样本", payload.manifest.field_samples],
  ["场景意图样本", payload.manifest.intent_samples],
  ["模型特征数量", metrics.model.features],
];
summary.getRange("D3:F8").values = [
  ["测试指标", "结果", "门槛"],
  ["Top-1 准确率", metrics.test.top1_accuracy, 0.90],
  ["Top-3 准确率", metrics.test.top3_accuracy, 0.98],
  ["相关字段接收召回", metrics.test.relevant_accept_recall, 0.85],
  ["无关字段误接收率", metrics.test.irrelevant_false_accept_rate, 0.05],
  ["拒绝阈值", metrics.model.accept_threshold, null],
];
summary.getRange("A3:B3").format = { fill: colors.section, font: { bold: true, color: colors.ink } };
summary.getRange("D3:F3").format = { fill: colors.section, font: { bold: true, color: colors.ink } };
summary.getRange("E4:F8").format.numberFormat = "0.0%";
summary.getRange("A10:F10").merge(); summary.getRange("A10").values = [["场景模板"]]; summary.getRange("A10:F10").format = { fill: colors.section, font: { bold: true, color: colors.ink } };
const scenarioRows = payload.manifest.scenarios.map(item => [item.scenario_id, item.scenario_name, item.industry, item.process_unit, item.field_count, item.required_count]);
summary.getRangeByIndexes(10, 0, scenarioRows.length + 1, 6).values = [["场景ID", "场景名称", "行业", "装置", "字段数", "必需字段"], ...scenarioRows];
summary.getRange("A11:F11").format = { fill: colors.header, font: { bold: true, color: "#FFFFFF" } };
summary.getRange("A18:F19").merge(); summary.getRange("A18").values = [["注意：当前指标来自合成种子数据，仅用于验证训练链路。真实部署必须加入多厂区人工审核标签并重新评估。"]]; summary.getRange("A18:F19").format = { fill: colors.amber, font: { color: "#7A5200" }, wrapText: true, verticalAlignment: "center" };
summary.getRange("A1:F20").format.font = { name: "Arial", color: colors.ink };
summary.getRange("A1:F1").format.font = { name: "Arial", bold: true, color: "#FFFFFF", size: 18 };
summary.getRange("A11:F11").format.font = { name: "Arial", bold: true, color: "#FFFFFF", size: 11 };
summary.getRange("A1:F20").format.columnWidth = 20;
summary.getRange("D1:D20").format.columnWidth = 27;

function writeDataSheet(sheet, headers, rows, widths, tableName) {
  const values = [headers, ...rows];
  sheet.getRangeByIndexes(0, 0, values.length, headers.length).values = values;
  sheet.getRangeByIndexes(0, 0, 1, headers.length).format = { fill: colors.header, font: { bold: true, color: "#FFFFFF" }, rowHeight: 25, verticalAlignment: "center" };
  sheet.getRangeByIndexes(0, 0, values.length, headers.length).format.font = { name: "Arial", size: 10, color: colors.ink };
  sheet.getRangeByIndexes(0, 0, 1, headers.length).format.font = { name: "Arial", size: 10, bold: true, color: "#FFFFFF" };
  widths.forEach((width, index) => sheet.getRangeByIndexes(0, index, values.length, 1).format.columnWidth = width);
  sheet.freezePanes.freezeRows(1);
  sheet.tables.add(sheet.getRangeByIndexes(0, 0, values.length, headers.length), true, tableName);
}

writeDataSheet(samples,
  ["text", "scenario_id", "standard_name", "relevance", "role", "unit", "source", "split"],
  payload.field_rows.map(row => [row.text,row.scenario_id,row.standard_name,row.relevance,row.role,row.unit,row.source,row.split]),
  [28,24,28,14,16,14,18,13], "FieldTrainingTable");
writeDataSheet(intents,
  ["text", "scenario_id", "scenario_name", "split"],
  payload.intent_rows.map(row => [row.text,row.scenario_id,row.scenario_name,row.split]),
  [48,26,24,14], "ScenarioIntentTable");
writeDataSheet(dictionary,
  ["scenario_id","scenario_name","standard_name","display_name","description","role","data_type","unit","required","aliases","lower_bound","upper_bound"],
  payload.dictionary_rows.map(row => [row.scenario_id,row.scenario_name,row.standard_name,row.display_name,row.description,row.role,row.data_type,row.unit,row.required,row.aliases,row.lower_bound,row.upper_bound]),
  [24,22,28,20,42,16,14,14,12,48,14,14], "DictionaryTable");

labels.getRange("A1:D1").merge(); labels.getRange("A1").values = [["标签与使用规则"]]; labels.getRange("A1:D1").format = { fill: colors.header, font: { bold: true, color: "#FFFFFF", size: 16 }, rowHeight: 32 };
labels.getRange("A3:D8").values = [
  ["标签", "含义", "是否进入标准数据", "产生方式"],
  ["required", "场景必需字段", "是", "场景模板"],
  ["useful", "可选但具有工艺价值", "是", "场景模板"],
  ["uncertain", "模型候选或映射冲突", "否，需人工确认", "推理阈值/冲突规则"],
  ["irrelevant", "与场景无关或无法识别", "否", "负样本/拒绝阈值"],
  ["ready/review/reject", "整份文件可用性", "按状态决定", "必需覆盖率+风险规则"],
];
labels.getRange("A3:D3").format = { fill: colors.section, font: { bold: true, color: colors.ink } };
labels.getRange("A1:D8").format.columnWidth = 28;
labels.getRange("B1:B8").format.columnWidth = 44;
labels.getRange("A1:D8").format.wrapText = true;

const previews = [
  ["概览", "A1:F20"], ["字段训练样本", "A1:H24"], ["场景意图样本", "A1:D24"], ["多场景数据字典", "A1:L20"], ["标签说明", "A1:D8"]
];
for (const [sheetName, range] of previews) {
  const image = await workbook.render({ sheetName, range, scale: 1.3, format: "png" });
  await fs.writeFile(`${previewDir}/${sheetName}.png`, new Uint8Array(await image.arrayBuffer()));
}

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(`${outputDir}/A14_多场景字段Agent训练数据包.xlsx`);
console.log(`${outputDir}/A14_多场景字段Agent训练数据包.xlsx`);
