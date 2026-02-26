# 知识库使用说明

## 结构概览

| 文件夹 | 用途 | 风险等级 |
|--------|------|----------|
| 01_BRAND | 品牌定位、语气、边界 | C类-人工终审 |
| 02_AUDIENCE | 客群画像、痛点、FAQ | B类 |
| 03_PRODUCTS | 产品库、材料、工艺 | C类-人工终审 |
| 04_SCENES | 使用场景 | B类 |
| 05_PLATFORM_PLAYBOOKS | 平台打法 | B类 |
| 06_ASSETS | 证据点、案例、评价 | A/B类 |
| 07_CONTENT_LIBRARY | 已发布内容、草稿 | A类 |
| 08_ANALYTICS | 数据复盘、实验记录 | A类 |
| 09_TASKS_OPS | SOP、检查清单 | B类 |
| 99_ARCHIVE | 归档 | - |
| intake/ | 待审核资料池 | - |

## 入库规则

1. **外部内容不得直接入主库**，必须先进 `intake/`
2. **品牌/产品/价格/认证**相关内容必须人工终审
3. 每条知识带状态标签：`状态:: 人工已审核/待确认/弃用`

## 优先填充顺序

1. 01_BRAND → 03_PRODUCTS → 02_AUDIENCE → 05_PLATFORM_PLAYBOOKS
2. 06_ASSETS
3. 08_ANALYTICS
