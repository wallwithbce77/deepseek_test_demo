# DeepSeek API 自动化测试框架 (模块化 & 数据驱动)

这是一个基于 Python + Pytest + Requests 搭建的大模型 API 自动化测试框架。项目采用**分层架构设计**与**数据驱动 (DDT)** 思想，用于验证 DeepSeek 对话接口的连通性、业务逻辑、响应性能及大模型幻觉防御能力。

## 🛠️ 技术栈
- **开发语言**：Python 3.10+
- **测试框架**：pytest
- **网络请求**：requests (含 HTTPAdapter 重试机制)
- **环境隔离**：python-dotenv
- **报告生成**：pytest-html

## 📁 项目结构
```text
ai_test_pro/
├── config.py             # 全局配置中心 (读取环境变量、模型名称、超时时间等)
├── client.py             # 客户端封装类 (全局 Session 复用、Retry 重试机制)
├── conftest.py           # 全局 Fixture (注入 Client 实例，保障资源安全释放)
├── validators.py         # 校验规则引擎 (基于策略模式/字典映射的动态断言)
├── test_data.json        # 测试用例数据源 (JSON 格式，实现数据与逻辑分离)
├── test_ai_api.py        # 核心测试执行入口
├── pytest.ini            # Pytest 运行配置
├── requirements.txt      # 项目依赖清单
└── README.md             # 项目说明文档