#!/usr/bin/python
# -*- coding:utf-8 -*-
import requests
import json
from pathlib import Path
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_headers_from_json():
    """从JSON文件加载请求头"""
    headers_path = Path("/Users/admin/PycharmProjects/wbs/test_case/paylo_js/header.json")
    try:
        if not headers_path.exists():
            raise FileNotFoundError(f"请求头文件不存在: {headers_path}")

        with open(headers_path, 'r', encoding='utf-8') as f:
            headers = json.load(f)

        # 确保返回的是字典类型
        if not isinstance(headers, dict):
            raise ValueError("请求头文件内容必须是JSON对象格式")

        return headers

    except json.JSONDecodeError as e:
        raise ValueError(f"请求头JSON解析失败: {str(e)}")
    except Exception as e:
        raise ValueError(f"加载请求头失败: {str(e)}")

def print_request_details(method, url, headers, payload):
    """打印请求详细信息"""
    print("\n====== 请求参数详情 ======")
    print(f"URL: {url}")
    print(f"Method: {method}")
    print("Headers:")
    print(json.dumps(headers, indent=2, ensure_ascii=False))
    print("Payload:")
    print(json.dumps(json.loads(payload), indent=2, ensure_ascii=False))
    print("=" * 30 + "\n")

def extract_fields(response_data):
    """从响应体中提取目标字段"""
    results = []
    if 'data' in response_data:
        for item in response_data['data']:
            raw_date = item.get('customerExpectDeliveryDate', '')
            formatted_date = raw_date[:10] if raw_date else ''

            record = {
                'id': item.get('id', ''),
                'code': item.get('code', ''),
                'customerExpectDeliveryDate': formatted_date,
                'platform': item.get('platform', ''),
                'fulfillmentOrderCreatedTime': item.get('fulfillmentOrderCreatedTime', '')
            }
            results.append(record)
    return results

def save_data(records):
    """统一处理文件存储"""
    file_path = Path("/Users/admin/PycharmProjects/wbs/test_case/variable/erp/zf_code.txt")
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        lines = []
        for r in records:
            line = f"{r['id']}|{r['code']}|{r['platform']}|{r['customerExpectDeliveryDate']}|{r['fulfillmentOrderCreatedTime']}"
            lines.append(line)

        existing = set()
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                existing = set(f.read().splitlines())

        with open(file_path, 'w', encoding='utf-8') as f:
            for line in lines:
                if line not in existing:
                    f.write(line + '\n')

        print(f"成功保存{len(lines)}条记录到{file_path.resolve()}")
    except KeyError as e:
        print(f"字段缺失错误: 缺少关键字段 {str(e)}")
    except Exception as e:
        print(f"存储失败: {str(e)}")

def read_txt_file(file_path):
    """读取txt文件内容并返回字符串列表"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.read().strip().split('\n')
            logging.info(f"读取文件 {file_path}，共读取 {len(lines)} 行记录")
            return lines
    except Exception as e:
        logging.error(f"读取文件失败: {file_path}, 错误: {str(e)}")
        return []

# 读取所有需要的文件（示例路径，请根据实际情况修改）
order_ids_file_path = "/Users/admin/PycharmProjects/wbs/test_case/variable/erp/order_ids.txt"
order_ids = read_txt_file(order_ids_file_path)

# 验证读取结果
logging.info("验证读取结果:")
logging.info(f"order_ids: {order_ids}")

def main():
    try:
        # 从JSON文件加载请求头
        headers = load_headers_from_json()
        logging.info("从JSON加载的请求头: %s", headers)

        # 准备请求参数
        main_url = "http://wbs-test.wbscorp.com:8080/tms/directDeliveryOrder/list"
        backup_url = "http://wbs-test.wbscorp.com:8081/tms/directDeliveryOrder/list"
        payload = json.dumps({
            "currentPage": 1,
            "pageSize": 100,
            "associatedCodeList": order_ids
        })

        # 打印请求详情
        print_request_details("POST", main_url, headers, payload)

        # 尝试发送请求到主URL
        try:
            response = requests.post(main_url, headers=headers, data=payload, timeout=10)
            response.raise_for_status()
            used_url = main_url
        except requests.exceptions.RequestException as e:
            logging.warning(f"请求主URL失败：{str(e)}，尝试备用URL")
            # 尝试发送请求到备用URL
            try:
                response = requests.post(backup_url, headers=headers, data=payload, timeout=10)
                response.raise_for_status()
                used_url = backup_url
            except requests.exceptions.RequestException as e:
                logging.error(f"请求备用URL也失败：{str(e)}")
                raise

        # 记录使用的URL
        logging.info(f"\n====== 实际使用的URL ======")
        logging.info(used_url)

        # 后续逻辑（响应处理、数据提取和保存等）
        logging.info("\n====== 响应状态码 ======")
        logging.info(f"HTTP {response.status_code}")

        logging.info("\n====== 响应体内容 ======")
        response_data = response.json()
        logging.info(json.dumps(response_data, indent=2, ensure_ascii=False))

        # 处理响应数据
        extracted_data = extract_fields(response_data)
        logging.info("\n提取到的记录:")
        for d in extracted_data:
            logging.info(
                f"代码: {d.get('id', '')}, ID: {d.get('code', '')}, 平台: {d.get('platform', '')}, 发货日期: {d.get('customerExpectDeliveryDate', '')}, 建单日期: {d.get('fulfillmentOrderCreatedTime', '')}"
            )

        if extracted_data:
            save_data(extracted_data)
        else:
            logging.info("无有效数据需要保存")

    except json.JSONDecodeError:
        logging.error("错误：响应不是有效的JSON格式")
    except ValueError as e:
        logging.error(f"配置错误：{str(e)}")
    except Exception as e:
        logging.error(f"程序异常：{str(e)}")

if __name__ == "__main__":
    main()
