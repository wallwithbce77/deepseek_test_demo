from __future__ import annotations
import pytest
from core import config as settings
from core.client import DeepseekClient
from core.fake_client import FakeClient
from core.metrics import RunContext, format_lines, write_artifacts
from tests.stub_server import StubServer

RUN_CTX = RunContext.new()


def pytest_configure(config):
    config.addinivalue_line("markers", "live: 需要真实 API Key 的用例，离线模式自动跳过")


@pytest.fixture(scope="session")
def api_client():
    if settings.USE_FAKE:
        client = FakeClient(error_rate=settings.FAKE_ERROR_RATE, seed=settings.FAKE_SEED)
    else:
        client = DeepseekClient()
    yield client
    client.close()


@pytest.fixture(scope="session")
def run_ctx() -> RunContext:
    return RUN_CTX


@pytest.fixture#启动服务器
def stub_server():
    server = StubServer().start()
    yield server
    server.stop()


def pytest_sessionfinish(session, exitstatus):
    summary = RUN_CTX.summary()
    if not summary["cases"] and not summary["extraction"]:
        return
    out_dir = write_artifacts(summary)
    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    lines = format_lines(summary) + [f"明细目录：{out_dir}"]
    if reporter:
        reporter.write_sep("=", "质量汇总")
        for line in lines:
            reporter.write_line(line)
    else:
        print("\n".join(lines))
