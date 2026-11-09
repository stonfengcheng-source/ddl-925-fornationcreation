export type MetricType = 'ratio'|'number'|'count'|'distribution'|'days';
export interface MetricMetadata { name: string; description: string; type: MetricType; unit: string; direction: string; applicability: string; formula: string; unavailable: string }
const meta = (name:string, description:string, type:MetricType, unit:string, direction:string, formula:string, unavailable='当前缺少可靠的计算依据，不能据此判断。'):MetricMetadata => ({name,description,type,unit,direction,formula,applicability:'以本次处理记录和规则为范围；不代表专业内容正确。',unavailable});
export const METRIC_METADATA: Record<string,MetricMetadata> = {
  valid_sft_structure_rate:meta('问答结构有效率','指令和回答均非空的记录比例。','ratio','%', '越高越完整','有效指令与回答记录数 / 已解析记录数'),
  required_field_completeness_rate:meta('必要字段完整样本率','必要字段全部存在的样本比例。','ratio','%', '越高越完整','必要字段完整样本数 / 已检查样本数'),
  required_field_cell_presence_rate:meta('必要字段填充率','必要字段单元格中非空项的比例。','ratio','%', '越高越完整','非空必要字段数 / 必要字段总数'),
  parseable_sample_rate:meta('记录可解析率','可解析为对象的输入记录比例。','ratio','%', '越高越完整','可解析记录数 / 非空输入记录数'),
  necessary_label_coverage:meta('回答字段覆盖率','已解析记录中具有非空回答的比例；不等于分类标签。','ratio','%', '越高越完整','具有回答的记录数 / 已解析记录数'),
  schema_consistency_rate:meta('结构一致率','标识、指令和回答满足基本类型及非空条件的比例。','ratio','%', '越高越一致','结构有效记录数 / 已解析记录数'),
  answer_conflict_groups:meta('疑似答案冲突组占比','重复问题中存在多个答案变体的组比例，仅供复核。','ratio','%', '需人工判断','疑似冲突组数 / 重复问题组数','没有可比较的重复问题组；无法由此判断答案正确性。'),
  cross_modal_match_rate:meta('跨模态匹配率','图文或音视频配对内容的一致性。','ratio','%', '越高越一致','匹配配对数 / 配对总数','当前是纯文本数据，缺少图像或音频配对，无法评价跨模态一致性。'),
  reviewer_agreement_rate:meta('复核者一致率','独立复核者对同一内容的一致程度。','ratio','%', '越高越一致','一致的复核结果数 / 双人复核总数','缺少独立双人复核记录；不能据此评价复核一致性。'),
  category_coverage:meta('主题覆盖率','规则估计主题覆盖配置类别的情况，非人工标注。','ratio','%', '仅作分布参考','已观察主题数 / 配置主题数','缺少主题规则，无法估计主题覆盖。'),
  category_distribution:meta('主题估计分布','基于关键词规则估计的主题数量，并非人工标签。','distribution','条', '仅作分布参考','各估计主题的样本数'),
  normalized_category_entropy:meta('主题分布归一化熵','描述规则估计主题的分散程度，不是综合质量分。','number','', '仅作分布参考','主题分布熵 / 已观察主题数的对数'),
  long_tail_category_coverage:meta('长尾主题覆盖','规则估计中低于阈值的主题和数量。','distribution','', '仅作分布参考','统计占比不高于阈值的主题'),
  near_duplicate_ratio:meta('近重复候选比例','被标记为近重复、需要人工复核的记录比例。','ratio','%', '需人工判断','近重复候选记录数 / 已解析记录数'),
  reference_distribution_difference:meta('参考分布差异','当前分布与外部参考分布的差异，越小越接近。','number','', '越小越接近参考','各类别占比差的绝对值之和 / 2','缺少可靠的参考分布；可补充可信分布后重算，当前不能得出无偏结论。'),
  source_distribution:meta('来源分布','本批记录按来源统计的数量。','distribution','条', '仅作来源参考','各来源记录数'),
  published_at_coverage:meta('发布时间覆盖率','带有可解析发布时间的记录比例。','ratio','%', '越高依据越充分','有效发布时间记录数 / 已解析记录数'),
  data_age_days:meta('数据年龄范围','仅根据已知发布时间计算处理时的数据年龄。','days','天', '结合使用场景判断','处理时间减去发布时间','缺少有效发布时间；可补充可信时间后重算，不能推断数据年龄。'),
  confirmed_expired_ratio:meta('确认过期比例','基于明确有效期证据确认过期的记录比例。','ratio','%', '越低越好','确认过期记录数 / 具备有效期证据的记录数','缺少可核实的有效期；发布时间久不等于已过期。'),
  older_than_threshold_ratio:meta('超过时间阈值比例','发布时间早于配置阈值的记录比例，不代表已过期。','ratio','%', '结合使用场景判断','超过阈值记录数 / 有效发布时间记录数','缺少有效发布时间；不能判断是否超过时间阈值。'),
  time_anomalies:meta('时间异常统计','无效日期及未来日期的数量。','distribution','条', '需核查','分别统计无效日期与未来日期'),
  version_conflict_count:meta('版本冲突数','相同样本标识对应不同原始内容的数量。','count','条', '需核查','统计标识冲突样本数'),
};
export const DIMENSION_PRIMARY: Record<string,string> = {completeness:'valid_sft_structure_rate',consistency:'schema_consistency_rate',diversity:'category_coverage',unbiasedness:'reference_distribution_difference',timeliness:'published_at_coverage'};
