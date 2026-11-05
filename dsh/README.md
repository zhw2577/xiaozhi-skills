# DSH Web 学生端适配

基于小智伴学 2.12.5，源提交 `c6d628d0602d16585be31abb17bfc4ea0c725b01`。
Fork：https://github.com/zhw2577/xiaozhi-skills 。上游作者、MIT 许可与学科资源保持不变。

## 构建

使用 Python 3.10+ 标准库，无需 npm install：

```text
python scripts/build-dsh.py --output <新的绝对输出目录，必须在源码目录外>
```

输出为 49 个完整学生技能的平铺目录、文件哈希清单、tar.gz 归档。DSH filesystem provider
只扫描技能根的直接子目录，所以不能直接把上游 student/ 多层目录整体放进去。
老师端 34 个技能和开发者工具不进入部署包。共享约定、reference、schema 随各技能保留。
唯一 JS 资源 schemas/validate.js 是上游开发期校验示例，已阅读并按哈希固定，仅复制而不执行；不安装其 Ajv 依赖。

## 适配范围

- 构建时添加 dsh-platform.md 以及关键运行约定，明确原生图片输入、按需加载、Office 衔接。
- 不依赖 agent-photo-question；原技能由部署过程移到备份，便于恢复。
- 不修改上游 source SKILL.md 的教学内容，生成包声明 DSH compatibility。
- 学习 DNA、IM 提醒只允许用户手动调用，其余 47 个保留模型调用。
- 目前 M/X/T 未接入；共享管理员实例没有学生身份与字段访问控制，不开启长期档案与主动提醒。
- 语音评测、合成、精确计时等未验证，使用上游规定的降级流程。
- 不安装 OCR、额外模型或系统依赖，不改 DSH 源码，不重建镜像。

## 安装与验证

先保存当前技能目录清单，备份同名技能以及 agent-photo-question。将归档内 skills 的直接子目录
安装到 `/var/lib/dsh/skills/`，目录权限 700、文件 600，保留原来其他技能。
由 DSH 官方 FileSystemSkillProvider 检查发现数量、唯一名称、调用策略、正文与资源可读性。
再核对清单文件哈希以及安装前后容器镜像、启动时间、Compose/profile 哈希保持一致。
不为加载 Skill 重启容器。验证不包含收费模型调用，真实题图效果由用户试用。

DSH 适配文件发布到 fork 的 `dsh-web-adapter` 分支，上游与 fork 的 main 不改。
构建清单记录 fork HEAD、工作副本是否有未提交修改，以及固定的上游源提交；
每个实际安装资源另有 SHA-256，用于核对本地部署包。
