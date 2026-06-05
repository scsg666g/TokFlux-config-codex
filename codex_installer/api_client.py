# -*- coding: utf-8 -*-
from dataclasses import dataclass
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from .config import API_TEST_TIMEOUT, API_TEST_USER_AGENT


@dataclass(frozen=True)
class ApiTestResult:
    ok: bool
    message: str
    detail: str | None = None


def normalize_base_url(base_url):
    return base_url.rstrip("/") + "/"


def build_models_url(base_url):
    return urljoin(normalize_base_url(base_url), "models")


def test_openai_connection(base_url, api_key):
    if not base_url:
        return ApiTestResult(False, "连接失败：API 请求地址不能为空")

    if not api_key:
        return ApiTestResult(False, "连接失败：key 不能为空")

    request = Request(
        build_models_url(base_url),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "User-Agent": API_TEST_USER_AGENT,
        },
        method="GET",
    )

    try:
        with urlopen(request, timeout=API_TEST_TIMEOUT) as response:
            body = response.read().decode("utf-8", errors="replace").strip()
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace").strip()
        return ApiTestResult(
            False,
            f"连接失败：HTTP {exc.code}",
            trim_detail(detail),
        )
    except URLError as exc:
        return ApiTestResult(False, f"连接失败：{exc.reason}")
    except TimeoutError:
        return ApiTestResult(False, "连接失败：请求超时")
    except OSError as exc:
        return ApiTestResult(False, f"连接失败：{exc}")

    if not body:
        return ApiTestResult(False, "连接失败：接口没有返回内容")

    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return ApiTestResult(True, "连接成功：接口已返回内容", trim_detail(body))

    return ApiTestResult(True, "连接成功")


def trim_detail(text, limit=500):
    if not text:
        return None

    if len(text) <= limit:
        return text

    return text[:limit] + "..."
