# 优学院脚本集合（DGUT版本）

> ⚠️ **免责声明**：本项目仅供学习交流使用，请勿用于商业用途或任何违规行为。本项目仅供学习研究使用，请勿用于违反学术诚信的行为。使用本项目产生的任何后果由使用者自行承担，与开发者无关。使用本脚本所产生的一切后果由使用者自行承担，作者不承担任何责任。

## 项目简介

本项目是针对东莞理工学院（DGUT）优学院平台的脚本集合，包含自动签到、刷课、题目下载和AI答题等功能。所有脚本均经过适配改造，以兼容DGUT的优学院系统。

## 功能特性

### 1. 自动签到脚本 (QIANDAO.py)
- ✅ 自动登录DGUT应用平台
- ✅ 自动签到功能
- ✅ 作业检查与提醒
- ✅ 邮件通知功能
- ✅ 支持手动token输入和Selenium自动登录

### 2. 刷课脚本 (刷课.js)
- ✅ 自动播放课程视频
- ✅ 自动跳过视频进度
- ✅ 支持批量课程处理
- ✅ 可配置播放速度
- ✅ 自动完成课程学习要求

### 3. 题目下载脚本 (jiaoben.js)
- ✅ 批量下载优学院课程题目
- ✅ 支持多种题型导出
- ✅ 保存为结构化格式
- ✅ 便于离线复习和整理

### 4. 网页答案读取脚本 (scrip（dgut专门版）.py)
- ✅ 直接从考试页面获取前端答案
- ✅ 支持单选题、多选题、判断题、填空题
- ✅ 自动答题功能
- ✅ 基于DrissionPage框架实现

### 5. AI答题服务 (ai_answer_service_local.py)
- ✅ 本地AI模型支持
- ✅ FastAPI服务架构
- ✅ 支持多种题型识别
- ✅ 兼容繁体中文题型
- ✅ 可配置模型参数

## 依赖库安装

### 基础依赖
```bash
pip install requests configparser apscheduler
```

### 签到脚本额外依赖
```bash
pip install selenium
```

### 网页答案脚本依赖
```bash
pip install DrissionPage
```

### AI答题服务依赖
```bash
pip install fastapi uvicorn torch transformers
```

### 完整安装命令
```bash
pip install requests configparser apscheduler selenium DrissionPage fastapi uvicorn torch transformers
```

## 使用说明

### 1. 自动签到脚本
1. 运行 `QIANDAO.py`
2. 首次运行会自动创建配置文件 `config.ini`
3. 按提示输入账号信息（格式：dgut+学号）
4. 配置地理位置信息（松山湖校区默认：纬度 22.927, 经度 113.881）
5. 可选配置邮件通知功能

### 2. 网页答案读取脚本
1. 确保已安装浏览器驱动
2. 运行 `scrip（dgut专门版）.py`
3. 在浏览器中打开DGUT优学院答题页面
4. 按脚本提示进行操作

### 3. AI答题服务
1. 修改 `ai_answer_service_local.py` 中的模型路径配置
2. 运行脚本启动服务（默认端口5000）
3. 服务地址：`http://localhost:5000`
4. API文档：`http://localhost:5000/docs`

## 配置说明

### 浏览器配置
- 支持Chrome和Edge浏览器
- 可通过配置文件或命令行参数指定浏览器路径
- 浏览器版本要求：Chrome 90+ 或 Edge 90+

### AI模型配置
- 支持Qwen系列模型
- 推荐模型：Qwen2.5-1.5B-Instruct
- 支持GPU加速（如可用）
- 可调整生成参数（temperature、top_p等）

## 注意事项

1. **首次使用**：建议先测试单个功能，确保环境配置正确
2. **账号安全**：请妥善保管个人账号信息，不要分享配置文件
3. **网络环境**：确保网络连接稳定，特别是使用AI答题服务时
4. **浏览器驱动**：请下载与浏览器版本匹配的驱动程序
5. **模型文件**：AI模型文件较大，首次使用需要下载时间

## 📌 原项目参考

### 🔗 重要项目链接
- **网页答案脚本**：[Black-Cyan/Ulearning](https://github.com/Black-Cyan/Ulearning) ⭐
- **题目下载脚本**：[twj0/ulearning-course-export](https://github.com/twj0/ulearning-course-export?tab=readme-ov-file) ⭐
- **AI答题脚本**：[spiritofmoon/online-course-ai-assistant](https://github.com/spiritofmoon/online-course-ai-assistant) ⭐

### 其他参考
- 签到脚本：原项目已不可考

---

**⚠️ 重要声明**：
1. **刷课脚本**：仅用于辅助学习，请合理使用，避免过度依赖
2. **题目下载脚本**：仅供个人学习使用，请勿用于商业用途或传播
3. 所有脚本的使用应遵守学校相关规定和学术诚信要求

## 版本信息

- 签到脚本：DGUT适配版
- 答题脚本：v1.3.2-dgut
- AI服务：本地模型版

## 许可证

本项目基于Apache License 2.0开源协议。

## 贡献

欢迎提交Issue和Pull Request来改进本项目。

---

**重要提醒**：请遵守学校相关规定，合理使用学习工具，维护良好的学习环境。