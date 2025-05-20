#!/usr/bin/python
# -*- coding: utf-8 -*-
import requests
import json
import importlib.util
from pathlib import Path
import sys


class ApiConfig:
    def __init__(self, primary_url, fallback_base_url=None, payload=None, headers=None, timeout=30):
        self.primary_url = primary_url
        # 修改备用URL的初始化方式，只存储基础部分，端口号在需要时动态添加
        self.fallback_base_url = fallback_base_url
        self.payload = payload
        self.headers = headers
        self.timeout = timeout

    # 添加一个方法来获取完整的备用URL
    def get_fallback_url(self, base_port=8080):
        # 默认备用端口号为主端口号+1，但这里我们直接指定为8081（如果需要动态计算，可以移除base_port参数并使用primary_url解析）
        fallback_port = 8081  # 或者通过解析primary_url获取端口并+1，但这里为了简化直接指定
        fallback_url = f"{self.fallback_base_url}:{fallback_port}" if self.fallback_base_url else None
        return fallback_url


class ApiClient:
    def __init__(self, config):
        self.config = config

    def execute_request(self):
        try:
            # 动态导入payload文件并获取payload数据
            payload_module = self._import_payload_file(self.config.payload)
            payload_data = payload_module.payload_data

            # 打印请求体
            print("\n====== 请求体 ======")
            print(json.dumps(payload_data, indent=2, ensure_ascii=False))

            # 获取headers数据
            headers = self._load_headers(self.config.headers)

            # 发送请求到主URL
            response = requests.post(
                self.config.primary_url,
                data=json.dumps(payload_data, ensure_ascii=False).encode('utf-8'),
                headers=headers,
                timeout=self.config.timeout
            )

            # 检查响应状态码，如果不是200则尝试备用URL（这里特别检查502错误，但也可以扩展为检查所有错误）
            if response.status_code != 200:
                if response.status_code == 502 or not self.config.fallback_base_url:  # 如果遇到502错误或没有备用URL，则直接抛出异常
                    response.raise_for_status()  # 这将抛出HTTPError异常
                else:
                    # 获取备用URL并发送请求
                    fallback_url = self.config.get_fallback_url()
                    print(f"\n主URL请求失败，状态码：{response.status_code}，正在尝试备用URL：{fallback_url}")
                    fallback_response = requests.post(
                        fallback_url,
                        data=json.dumps(payload_data, ensure_ascii=False).encode('utf-8'),
                        headers=headers,
                        timeout=self.config.timeout
                    )
                    fallback_response.raise_for_status()  # 如果备用请求也失败，则抛出异常
                    return fallback_response.json()  # 如果备用请求成功，则返回响应数据
            else:
                return response.json()  # 如果主请求成功，则返回响应数据

        except requests.exceptions.RequestException as e:
            # 这里不再需要检查备用URL是否存在，因为在上面的逻辑中已经处理过了
            raise Exception(f"请求失败: {str(e)}")


    def _import_payload_file(self, file_path):
        """动态导入Python文件作为payload"""
        try:
            spec = importlib.util.spec_from_file_location("payload_module", file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
        except Exception as e:
            raise Exception(f"导入payload文件失败: {str(e)}")

    def _load_headers(self, file_path):
        """从JSON文件加载headers"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            raise Exception(f"加载headers文件失败: {str(e)}")


def main():
    try:
        # 配置API参数，注意这里我们只需要提供基础备用URL（不带端口号）
        api_config = ApiConfig(
            primary_url="http://wbs-test.wbscorp.com:8080/tms/directDeliveryOrder/update",
            fallback_base_url="http://wbs-test.wbscorp.com/tms/directDeliveryOrder/update",  # 基础备用URL
            payload=Path("/Users/admin/PycharmProjects/wbs/test_case/paylo_js/submit_json.py"),
            headers=Path("/Users/admin/PycharmProjects/wbs/test_case/paylo_js/header.json"),
            timeout=15
        )

        # 执行API请求
        response_data = ApiClient(api_config).execute_request()

        # 打印响应数据
        print("\n====== 响应数据 ======")
        print(json.dumps(response_data, indent=2, ensure_ascii=False))

    except Exception as e:
        print(f"\n发生错误: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
