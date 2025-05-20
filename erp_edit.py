#!/usr/bin/python
# -*- coding:utf-8 -*-
import json
import requests
from pathlib import Path
from typing import List, Dict, Any, Union
import importlib.util


def load_ids_from_file(file_path: Path) -> str:
    """从文本文件读取平台订单ID并返回字符串（逗号分隔）"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            # 读取所有非空行并去除空白字符
            lines = [line.strip() for line in f if line.strip()]
            # 将列表转换为逗号分隔的字符串
            return ','.join(lines)
    except IOError as e:
        raise ValueError(f"文件读取失败: {str(e)}")


def load_zf_code_from_file(file_path: Path) -> Dict[str, str]:
    """从zf_code.txt文件读取数据并解析为字典"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                raise ValueError("zf_code.txt文件内容为空")

            parts = content.split('|')
            if len(parts) < 3:
                raise ValueError("zf_code.txt文件格式不正确，需要至少3个字段")

            return {
                'id': parts[0],
                'code': parts[1],
                'platform': parts[2]
            }
    except IOError as e:
        raise ValueError(f"文件读取失败: {str(e)}")


def load_payload_from_py(py_path: Path) -> Dict[str, Any]:
    """从Python文件加载payload数据"""
    try:
        # 动态导入Python模块
        spec = importlib.util.spec_from_file_location("payload_module", py_path)
        payload_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(payload_module)

        # 获取模块中的payload_data变量
        if hasattr(payload_module, 'payload_data'):
            # 确保associatedCode初始值为字符串类型
            payload = payload_module.payload_data
            if isinstance(payload.get('baseInfo', {}).get('associatedCode', []), list):
                payload['baseInfo']['associatedCode'] = ""
            return payload
        else:
            raise ValueError("Python文件中未找到payload_data变量")
    except Exception as e:
        raise ValueError(f"加载payload Python文件失败: {str(e)}")


def load_headers_from_json(json_path: Path) -> Dict[str, str]:
    """从JSON文件加载headers数据"""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            headers = json.load(f)
            if not isinstance(headers, dict):
                raise ValueError("headers文件内容必须是JSON对象格式")
            return headers
    except Exception as e:
        raise ValueError(f"加载headers JSON文件失败: {str(e)}")


def send_request(url: str, headers: Dict[str, str], payload: Dict[str, Any]) -> None:
    """发送HTTP请求并处理响应"""
    try:
        print(f"\n尝试请求URL: {url}")
        response = requests.post(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
            headers=headers,
            timeout=30
        )
        response.raise_for_status()

        print("\n请求成功")
        print(f"响应状态码: {response.status_code}")
        print(f"响应内容: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"\n请求失败: {str(e)}")
        if hasattr(e, 'response') and e.response:
            print(f"错误响应内容: {e.response.text}")
        raise


def main():
    try:
        # 1. 从文件加载数据
        order_ids_path = Path("/Users/admin/PycharmProjects/wbs/test_case/variable/erp/order_ids.txt")
        zf_code_path = Path("/Users/admin/PycharmProjects/wbs/test_case/variable/erp/zf_code.txt")
        payload_py_path = Path("/Users/admin/PycharmProjects/wbs/test_case/paylo_js/edit_json.py")
        headers_json_path = Path("/Users/admin/PycharmProjects/wbs/test_case/paylo_js/header.json")

        # 加载基础数据
        order_ids_str = load_ids_from_file(order_ids_path)  # 现在返回的是字符串
        zf_code_data = load_zf_code_from_file(zf_code_path)

        # 2. 加载payload和headers
        payload_data = load_payload_from_py(payload_py_path)
        headers = load_headers_from_json(headers_json_path)

        # 3. 更新payload中的动态字段
        payload_data["baseInfo"]["id"] = zf_code_data['id']
        payload_data["baseInfo"]["code"] = zf_code_data['code']
        payload_data["baseInfo"]["platform"] = zf_code_data['platform']
        payload_data["baseInfo"]["associatedCode"] = order_ids_str  # 直接使用字符串

        # 4. 设置主URL和备用URL
        main_url = "http://wbs-test.wbscorp.com:8080/tms/directDeliveryOrder/update"
        backup_url = "http://wbs-test.wbscorp.com:8081/tms/directDeliveryOrder/update"

        # 5. 打印请求信息
        print("\n====== 请求参数详情 ======")
        print(f"URL: {main_url} (主), {backup_url} (备)")
        print("Headers:")
        print(json.dumps(headers, indent=2, ensure_ascii=False))
        print("Payload:")
        print(json.dumps(payload_data, indent=2, ensure_ascii=False))
        print("=" * 30 + "\n")

        # 6. 尝试发送请求（先主URL，失败后尝试备用URL）
        try:
            send_request(main_url, headers, payload_data)
        except requests.exceptions.RequestException:
            print("\n主URL请求失败，尝试备用URL...")
            send_request(backup_url, headers, payload_data)

    except ValueError as e:
        print(f"\n配置错误: {str(e)}")
    except Exception as e:
        print(f"\n程序异常: {str(e)}")


if __name__ == "__main__":
    main()
