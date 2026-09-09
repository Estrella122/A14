"""Human-readable, synthetic routing seeds. Split before adding train-only wrappers."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
IDS = {
'asset':'csv_asset_manager', 'simulation':'industrial_simulation_generator',
'scenario':'dataset_scenario_profiler', 'standard':'semantic_field_unit_standardizer',
'time':'time_axis_alignment_resampler', 'clean':'missing_anomaly_cleaner',
'state':'steady_transient_state_detector', 'snr':'signal_noise_ratio_estimator',
'segment':'high_snr_dynamic_segment_extractor', 'quality':'segment_quality_scorer_ranker',
'lag':'time_delay_estimator_compensator', 'collinear':'collinearity_detector_reducer',
'dataset':'modeling_dataset_assembler', 'order':'arx_structure_order_selector',
'model':'system_identification_trainer', 'benchmark':'multi_model_benchmark',
'diagnostic':'model_diagnostics_evaluator', 'optimize':'closed_loop_preprocessing_optimizer',
'interpret':'engineering_result_interpreter', 'visual':'engineering_visualization_builder',
'report':'expert_report_writer', 'export':'final_artifact_exporter',
'experiment':'experiment_tracker_comparator', 'audit':'evidence_audit_reproducer', 'none':'__none__'}
# These are authored examples, not production logs and not labels copied from the old router.
TRAIN = {
'asset':'登记上传的CSV文件|校验这个数据文件能否读取|把新数据集加入资产库|查看原始CSV的文件名|检查CSV编码和分隔符|上传一份工业数据文件|读取刚上传的数据表|管理我的数据资产|记录数据来源和文件大小|检查文件是否为空|CSV资产在哪里|验证导入文件的格式|这份文件有没有登记|查看已上传文件列表|import the csv file|register dataset asset',
'simulation':'生成一份仿真数据|创建带噪声的加热炉测试数据|合成精馏塔时序样本|模拟带阶跃输入的炉温数据|生成含异常点的测试集|构造工业仿真CSV|给我造一批模拟数据|产生反应器的测试数据|仿真数据生成器在哪里|用模拟器生成动态样本|生成带稳态和过渡段的数据|合成有缺失值的工业数据|创建加热炉模拟数据集|生成随机扰动样本|generate synthetic time series|simulate industrial test data',
'scenario':'识别当前数据的工业场景|这批记录来自加热炉还是精馏塔|判断属于哪种生产装置|分析数据场景画像|根据数据推断设备类型|当前CSV属于哪个工艺|识别工厂业务场景|这是什么类型的工业过程|做数据场景分类|查看装置工况画像|数据更像锅炉还是反应器|识别工业过程类别|确定数据所属场景|判断这份数据的设备类别|identify industrial scenario|profile the equipment type',
'standard':'统一字段名称和单位|将温度从华氏度转为摄氏度|把压力单位换算为MPa|识别输入输出变量角色|解释字段映射依据|匹配标准字段字典|把流量列映射成标准名|检查量纲是否一致|字段别名如何统一|将timestamp映射为时间列|修正温度字段的单位|压力字段没有匹配成功|变量角色MV和CV怎么对应|进行语义字段标准化|normalize field units|map column names to standard fields',
 'time':'按10秒重新采样|把时间轴对齐|检查时间戳间隔|统一数据采样周期|解释采样频率的设置|检查时间戳重复|重采样到一分钟|检查不同传感器时钟偏移|如何避免采样混叠|时间序列频率不一致|对齐多路数据的时间戳|采样周期应该设多大|按30秒规整时间索引|解释奈奎斯特采样频率|resample every ten seconds|align timestamps',
'clean':'清洗缺失值和异常点|补齐传感器数据空缺|修复数据里的空值|检测离群点|把毛刺和坏点处理掉|对缺失值做线性插值|剔除超出物理边界的异常值|查看缺失率|处理数据断点|为什么空值这么多|异常值该怎么修复|清理不合理的负温度|检查数据中的坏点|缺失机制怎么判断|clean missing values and outliers|interpolate missing readings',
'state':'区分稳态和过渡态|识别工况变化区间|找出平稳运行的时间段|判断系统是否进入稳态|检测动态响应窗口|标记设备工况切换|识别有效动态工况|找出从稳态转入动态的时刻|工况状态识别|哪些区间没有动态变化|检测输入阶跃激励|持续激励充分吗|查看稳态与非稳态区间|判断这段数据是否平稳|detect steady and transient states|classify operating regimes',
'snr':'估计这段信号的信噪比|计算各变量SNR|测量噪声水平|信噪比为何偏低|评估传感器噪声强度|看看哪个变量噪声大|给出窗口信噪比置信等级|单独计算信噪比|信号被噪声淹没了吗|测一下输入信号的SNR|噪声占信号的比例是多少|评估信噪比是否达标|解释SNR的估计方法|估算信号和噪声功率比|estimate signal to noise ratio|measure sensor noise level',
'segment':'提取高信噪比动态段|筛选适合建模的动态数据|取出1号塔的优质动态窗口|挑出响应明显的动态片段|截取高质量动态数据|导出前先提取有效动态段|提取加热炉高信噪比动态数据|选择低噪声的动态窗口|筛选能用于辨识的有效片段|抽取动态变化清楚的时段|将有效动态数据提取出来|挑选高信噪比响应段|找出适合建模的动态样本|优选动态数据区间|extract high SNR dynamic segments|select informative dynamic windows',
'quality':'给动态段打分排序|比较各窗口的数据质量分数|按质量排列候选段|哪个片段评分最高|评估动态段完整性|对候选窗口进行综合评分|为什么这个动态段排名靠后|给优质段排序|按响应和完整性评价窗口|查看片段异常率得分|候选段的质量评分依据|为已选动态窗口评估质量|按平滑度排列窗口|评估严格动态段质量门槛|rank segment quality scores|score candidate windows',
'lag':'估计输入输出时滞|补偿气流到炉温的延迟|时滞为何是负数|分析变量响应滞后|用互相关估计纯滞后|把输入输出按时滞对齐|计算延迟采样点数量|检查时滞补偿结果|纯滞后有多大|流量变化多久后温度响应|估算系统时间延迟|检查补偿偏移方向|解释时滞估计结果|寻找互相关峰值对应时滞|estimate input output delay|compensate time lag',
'collinear':'检查输入变量共线性|计算各变量VIF|删除冗余输入|剔除高度相关的特征|多重共线性怎么处理|降维并保留独立变量|哪些输入信息重复|相关性太高该删哪列|解释VIF阈值|共线性消减结果如何|检查条件数与共线风险|筛掉重复信息的变量|保留哪些独立输入|处理严重多重共线|reduce multicollinearity|drop redundant input variables',
'dataset':'组装建模数据集|按时间切分训练集和测试集|检查训练测试数据泄漏|拼接优选动态窗口|冻结独立验证集|建立可复现的数据切分|生成建模用的数据表|避免把未来信息放进训练集|按工况分组划分样本|划分训练验证测试数据|整合用于辨识的样本|按时间先后分训练和验证|检查时间穿越泄漏|把选定窗口合并为建模数据|assemble modeling dataset|split training validation test chronologically',
'order':'选择ARX输入输出阶次|比较不同模型阶数|确定na和nb|用AIC挑选模型结构|BIC如何用于选阶|设置ARX纯延迟阶数|确定输入输出滞后阶数|挑选合适的ARX结构|模型阶次设为二阶|搜索最合适的模型阶数|结构选择要考虑哪些参数|ARX阶次为什么这么高|选择输入延迟nk|用信息准则确定阶数|select ARX model order|choose na nb and nk',
'model':'训练系统辨识模型|拟合一个ARX模型|用数据辨识动态系统|建立多输入单输出模型|开始系统辨识训练|重新拟合动力学模型|训练一个新的预测模型|根据建模数据估计模型参数|执行系统辨识|建立输入输出动态关系|学习工业过程模型参数|对当前数据做模型拟合|训练MISO动态模型|建立过程预测模型|train system identification model|fit an ARX predictor',
'benchmark':'比较多个候选模型|在相同测试集上做模型基准对比|哪种候选模型更好|公平比较不同模型结构|对照ARX和其他模型性能|查看多模型对比结果|给候选模型做一致的评价|运行模型基准测试|评比不同模型的泛化性能|比较两种辨识算法|各候选结构在同一数据上的效果|挑选表现更好的候选模型|模型之间的基准指标对照|对多个预测器做统一评测|benchmark candidate models|compare different model structures',
'diagnostic':'评估模型R2和RMSE|残差是否为白噪声|检查模型稳定性|模型预测误差有多大|计算MAE指标|检查残差自相关|诊断模型是否过拟合|验证模型泛化能力|看模型极点是否在单位圆内|模型是否可靠|评价预测误差分布|检查残差和输入互相关|给出模型诊断结果|分析模型R²为何偏低|evaluate model residuals|diagnose prediction error',
'optimize':'进行闭环预处理寻优|选择最佳轮次|为什么这一轮最优|调整top_k和max_lag优化模型效果|比较各轮寻优结果|闭环寻优何时停止|设置目标函数权重|优化动态筛选和时滞参数|查看寻优收敛情况|分析局部最优问题|寻找最佳预处理策略|评估各轮候选综合得分|继续闭环优化迭代|以模型效果反馈调整预处理|optimize preprocessing in closed loop|choose the best optimization round',
'interpret':'用工艺语言解释当前结果|这批数据最大的问题是什么|给出工程风险和建议|解释算法指标的实际意义|当前结论对生产有什么启示|说明自动分析的结论边界|模型能否直接上线投运|评估投运安全边界|结果还有什么薄弱环节|解释当前结果的工程含义|给工艺工程师说明主要问题|指出影响上线的证据缺口|总结结果中的主要风险|分析安全联锁要求|interpret engineering results|explain deployment limitations',
'visual':'画出温度趋势图|生成模型残差可视化|展示伯德图|绘制奈奎斯特图|把寻优过程画成曲线|展示输入输出对比图|生成工程可视化图表|查看频率响应图|绘制误差分布直方图|画出采样曲线|展示系统阶跃响应图|生成动态窗口示意图|将分析结果做成图|展示时间序列趋势|plot engineering charts|visualize frequency response',
'report':'撰写专家分析报告|生成本次评审报告|编写包含方法证据和结论的文档|整理工业建模总结报告|形成技术评审文档|写一份交付报告|把分析过程写成报告|生成Markdown专家报告|报告应该包含哪些章节|汇总方法与结果的报告|撰写项目总结文档|起草评审结论报告|输出完整分析报告内容|整理专家评审材料|write an expert report|draft technical analysis report',
'export':'下载已有报告|导出模型指标JSON|获取建模CSV下载链接|打包当前产物|把动态段CSV下载下来|导出本轮最终文件|给我现有报告的下载入口|下载最佳建模数据|导出寻优记录|获取已生成的文件|下载原始CSV文件|提供交付物下载链接|导出已有模型结果|把现有产物打包导出|download existing artifacts|export metrics as JSON',
'experiment':'比较历史运行的参数|查看实验版本历史|对比昨天和今天的运行结果|追踪模型漂移|历史实验哪一次最好|对照两个run的指标|记录模型版本变化|查看实验追踪记录|比对前后版本的参数差异|监测模型实时漂移|追踪在线更新记录|查看历史任务的表现|对比不同运行批次|比较实验版本的指标变化|compare historical experiment runs|track model version changes',
'audit':'审计输入参数和证据链|根据随机种子复现实验|检查结果能否追溯|固化原始输入和运行日志|复核审计证据|追溯每一步的数据来源|验证产物哈希|还原历史运行的证据链|检查实验可复现性|导出前核对证据来源|记录执行事件的审计链|验证输入和产物一致性|查阅证据审计日志|按原参数复现分析证据|audit evidence provenance|reproduce execution evidence',
'none':'你好|在吗|谢谢你|帮我订机票|明天会下雨吗|随便弄一下|处理一下|继续吧|帮我做一下|这个呢|我想吃什么|删除所有文件|发送邮件给客户|打开支付宝|hi there|what is the weather'}
VALIDATION = {
'asset':'校验刚上传的csv格式|查看数据资产登记信息|导入数据文件前检查编码',
'simulation':'合成一份锅炉仿真样本|生成带阶跃的模拟序列|创建用于测试的人工时序数据',
'scenario':'判断CSV对应哪类工业设备|做这批数据的场景画像|当前记录属于什么工艺场景',
'standard':'检查温度列与标准字段对应关系|统一测量量纲|把气体流量字段做语义匹配',
 'time':'把所有采样点按20秒对齐|检查时间戳是否连续|采样频率过低是否导致混叠',
'clean':'清理这列里的异常毛刺|用插值修补采集空档|为什么传感器有空缺数据',
'state':'识别由平稳转入过渡的时段|区分这个工况的稳动态状态|标记工况切换点',
'snr':'求各输入的信号噪声功率比|估计传感器的噪声大小|窗口SNR达到多少',
'segment':'抽取噪声低而响应强的动态片段|筛选高信噪比样本段|挑出用于建模的动态数据',
'quality':'按片段完整性和响应评分|候选窗口质量怎么排名|找出动态段评分最高的一段',
'lag':'测量控制量到输出的纯延迟|解释这个时滞补偿偏移|输入输出延迟有几步',
'collinear':'筛掉有冗余信息的输入列|查看多重共线性诊断|VIF很高时该留哪个变量',
'dataset':'构建时间顺序的训练测试分区|将动态窗口合并成辨识数据|检查数据划分有没有未来信息',
'order':'ARX的na应该如何确定|按照BIC比较阶次|选择合适的输出滞后阶数',
'model':'建立这个过程的动态预测器|用当前训练样本拟合模型|对现有数据执行系统辨识',
'benchmark':'候选模型能在同一批样本比较吗|进行多模型基准评测|对照不同辨识模型的表现',
'diagnostic':'检查拟合后的残差分布|测试R²和MAE表现怎样|判断模型极点稳定性',
'optimize':'哪个寻优轮次综合得分最好|基于模型效果调整预处理策略|查看闭环优化的终止条件',
'interpret':'说明这些结论的工艺意义|目前主要工程风险是什么|投运前还缺什么安全证据',
'visual':'绘制预测误差分布图|把当前频响显示成图表|生成输入输出趋势对照图',
'report':'编写本次系统辨识技术报告|整理方法和证据形成评审文档|起草项目分析总结',
'export':'给我现有模型指标文件的下载地址|导出已经生成的报告|下载已保存的建模数据CSV',
'experiment':'比较两次历史实验的误差|查询模型版本演变|跟踪概念漂移的情况',
'audit':'核对运行记录的证据来源|依据原始参数复现证据|检查交付物哈希是否一致',
'none':'晚上好|请帮我买股票|往后接着做'}
TEST = {
'asset':'CSV导入之前确认编码及列分隔符是否有效|这份上传文件的资产登记在哪里查|校验空白的数据文件|查一下已登记数据集的来源',
'simulation':'为反应器造一份含阶跃和毛刺的模拟时序|给我合成带传感器断点的试验数据|产生人工加热炉测试样本|生成工业模拟CSV序列',
'scenario':'从这些测点推断数据属于锅炉还是精馏装置|辨别当前工业数据的场景类别|给这份时序做设备场景画像|判断采集记录出自哪类生产过程',
'standard':'气体流量列名称和标准字典对不上|将这列压力由kPa换算到MPa|统一现场点表中的变量角色|测温字段的量纲映射错在哪里',
 'time':'多个传感器时间戳有偏移，按五秒统一时间轴|重新采样成60秒间隔|解释混叠与采样周期的关系|校对时间索引中重复的时刻',
'clean':'温度测点里有一串空白和突刺，修补一下|对超物理范围的数值做异常清洗|缺测记录用线性插值补全|排查数据中离群的坏点',
'state':'标出生产曲线由稳态进入过渡态的位置|哪些时间窗处于平稳运行工况|识别设备状态切换的区段|判断过程的激励是否充分',
'snr':'只测量信号功率相对噪声功率的比例|输入通道的噪声水平有多高|为每个窗口估算SNR|这个传感器的信噪比可信吗',
'segment':'把3号炉响应明显又低噪声的动态时段挑出来|抽取可用于辨识的高信噪比片段|筛出当前数据里的有效动态窗口|高信噪比动态数据提取',
'quality':'依据完整性和异常比例给这些候选窗口排名|列出动态段的综合质量分|为每个选定片段评估质量等级|哪一个候选段在评分榜首',
'lag':'输入阶跃之后输出晚了多久才变化，估计时滞|将流量与温度的纯滞后做补偿|检查输入输出延迟采样点|互相关峰值对应的滞后时间是多少',
'collinear':'几路输入重复表达同一个信息，消减冗余|根据VIF筛除共线变量|给出需要保留和删除的高度相关输入|多重共线的条件数为什么这么大',
'dataset':'把选定时间窗拼起来并冻结建模样本|按先后时间划出独立训练集和测试集|验证数据分区是否混入未来信息|组装可复现的辨识数据表',
'order':'用信息准则决定ARX模型阶数|设定输入阶次nb与输出阶次na|选择延迟项nk和候选结构|比较AIC以确定合适阶次',
'model':'根据这批样本拟合多输入动态系统|重新训练过程的ARX预测器|用现有数据估计辨识模型参数|执行多输入单输出系统建模',
'benchmark':'给几个候选预测器做公平的基准评测|用完全一样的验证数据比较模型结构|对照多种辨识算法的性能|哪一个候选模型测试效果更好',
'diagnostic':'检验残差序列有没有自相关|当前预测器的MAE和均方根误差如何|验证模型极点是否落在单位圆以内|诊断拟合结果的泛化可靠性',
'optimize':'让预处理策略随辨识效果反馈迭代寻优|比较各轮综合目标函数得分|闭环搜索为什么还没收敛|找出最优轮次的top_k参数',
'interpret':'把当前算法结论翻译成现场工艺建议|这套结果离投运还差哪些安全条件|本批次有哪些最需要解决的工程问题|给出分析结论适用的边界',
'visual':'将系统频率特性画成伯德图|展示炉温随时间变化的趋势曲线|画预测残差的直方分布|把闭环寻优每轮得分可视化',
'report':'将本轮证据整理成专家评审稿|撰写介绍方法和局限的分析报告|编写工业建模技术总结文档|起草可交付的专家报告正文',
'export':'把已经做好的报告下载给我|提供本轮模型JSON的下载入口|下载现成的动态片段CSV文件|打包导出已生成的交付物',
'experiment':'查历史任务两个版本之间的指标差异|对照前后运行的参数改动|跟踪上线后的模型漂移变化|比较不同批次实验的效果记录',
'audit':'通过原始输入和参数追溯结果证据|核验执行事件与产物的一致性|查每份交付数据的哈希证据|按照保存的随机种子复现实验记录',
'none':'今天上海的天气如何|麻烦继续那个|周末给我推荐一家餐厅|你好呀谢谢'}

def main():
    seen = set()
    for split, seeds in [('train',TRAIN),('validation',VALIDATION),('test',TEST)]:
        rows=[]
        for alias, phrases in seeds.items():
            for index, text in enumerate(phrases.split('|')):
                assert text not in seen, text
                seen.add(text)
                group=f'{split}-{alias}-{index:02}'
                variants=[text] if split!='train' else [text, '请帮我'+text, '我需要'+text]
                for v, message in enumerate(variants):
                    rows.append({'id':f'{group}-{v}','group':group,'text':message,'labels':[] if alias=='none' else [IDS[alias]],'source':'assistant_authored_synthetic','split':split})
        dest=ROOT/'data'/f'{split}.jsonl'
        dest.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows),encoding='utf8')
        print(split,len(rows),hashlib.sha256(dest.read_bytes()).hexdigest())
if __name__=='__main__':main()
