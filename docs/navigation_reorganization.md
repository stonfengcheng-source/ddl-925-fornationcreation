# 导航与兼容

正式入口为 `/app/data-governance/:section?` 和 `/app/model-experiments`，资源入口为 `/app/resources`。旧 `/app/preproject-data/:section?` 和 `/app/module4` 会重定向，并保留查询参数与片段。治理阶段包括数据选择、配置、任务、质量、复核和版本交付。版本页携带版本 ID 前往训练实验。

数据资产使用原数据库资产表。由治理导入的资产具有相同来源 ID，资产页可直接进入治理或查看该来源的版本；未关联文件的旧资产需要重新登记，不能伪装成已经迁移。
