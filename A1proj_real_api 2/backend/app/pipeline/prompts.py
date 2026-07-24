"""LLM 三元组抽取 Prompt 模板。"""
from __future__ import annotations

TRIPLE_EXTRACTION_PROMPT = """从以下数控机床维修文档中提取知识三元组。严格按格式输出，每行一个三元组，不要输出任何其他内容。

【文档】
{document_text}

【输出格式】
头实体类型|头实体名称|关系|尾实体类型|尾实体名称

实体类型只能是: device, component, fault, fault_cause, solution

关系示例（可自由扩展）:
- has_part: 设备包含部件
- causes: 原因导致故障
- solved_by: 故障用方案修复
- triggers: 部件触发故障
- located_in: 部件位于设备
- related_to: 一般关联

提取规则:
1. 头尾实体名称必须从文档原文中提取，不要编造
2. 优先提取报警代码、故障现象、具体部件名、参数值
3. 无把握时不强行提取，宁可少提取"""

TRIPLE_EXTRACTION_PROMPT_COMPACT = """从以下文档提取知识三元组（每行一个，格式固定）:

头实体类型|头实体名称|关系|尾实体类型|尾实体名称

实体类型: device, component, fault, fault_cause, solution
关系: has_part, causes, solved_by, triggers, located_in, related_to

文档:
{document_text}

三元组:"""
