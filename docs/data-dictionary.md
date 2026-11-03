# 数据字典

每行代表一名客户，原数据无客户 ID。

| 阶段 | 字段 | 含义 |
| --- | --- | --- |
| 实验前 | recency | 距最近购买的月数 |
| 实验前 | history | 过去一年消费金额（美元） |
| 实验前 | history_segment | 历史消费档位 |
| 实验前 | mens | 是否买过男装 |
| 实验前 | womens | 是否买过女装 |
| 实验前 | zip_code | 邮编对应地区类型，原表郊区写作 Surburban |
| 实验前 | newbie | 是否为过去一年新增客户 |
| 实验前 | channel | 历史购买渠道，Phone、Web、Multichannel |
| 分配 | segment | Mens E-Mail、Womens E-Mail、No E-Mail |
| 两周结果 | visit | 是否访问网站 |
| 两周结果 | conversion | 是否购买 |
| 两周结果 | spend | 消费金额（美元），未消费记零 |

历史品类 purchase_group 由 mens 和 womens 派生。
