ai_test_pro_p1/
├── core/
│   ├── config.py          # 环境变量、门禁阈值、离线开关
│   ├── client.py          # HTTP 客户端：重试、超时、结构化返回
│   ├── fake_client.py     # 离线桩：按标注合成回答，用于 CI/演示
│   ├── dataset.py         # 多文件数据集加载与 id 去重
│   ├── validators.py      # 归一化 + 字段级打分 + 断言规则
│   └── metrics.py         # 指标聚合、门禁、metrics.json 落盘
├── data/
│   ├── cases_functional.json     # 12 条
│   ├── cases_instruction.json    # 12 条
│   ├── cases_grounding.json      # 10 条
│   ├── cases_safety.json         # 8 条
│   ├── cases_boundary.json       # 8 条
│   └── extraction_samples.json   # 14 条
├── tests/
│   ├── conftest.py               # fixture、运行上下文、产物落盘
│   ├── stub_server.py            # 本地 HTTP 桩（真实 socket）
│   ├── test_dataset_quality.py   # 离线：数据集自检
│   ├── test_validators_unit.py   # 离线：纯函数单测
│   ├── test_chat_cases.py        # 在线：50 条数据驱动
│   ├── test_extraction_accuracy.py # 在线：字段准确率 + 门禁
│   ├── test_stability.py         # 在线：8 次采样
│   ├── test_negative.py          # 离线桩 + 真实负向
│   └── test_contract.py          # 真实契约
├── docs/defects.md        # 4 条缺陷记录
├── .env.example
├── pytest.ini
└── requirements.txt