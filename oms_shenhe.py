#!/usr/bin/python
# -*- coding:utf-8 -*-
import requests
import json
from pathlib import Path
import logging
from typing import List , Dict , Optional

# 基础路径设置
BASE_DIR = Path ( "/Users/admin/PycharmProjects/wbs/test_case" )
LOG_DIR = BASE_DIR / "variable" / "log"
LOG_FILE = LOG_DIR / "api_client.log"
HEADER_JSON = BASE_DIR / "paylo_js" / "header.json"

# 确保目录存在
LOG_DIR.mkdir ( parents=True , exist_ok=True )

# 日志配置
logging.basicConfig (
	filename=LOG_FILE ,
	level=logging.INFO ,
	format='%(asctime)s - %(name)s - %(levelname)s - %(message)s' ,
	encoding='utf-8'
)
logger = logging.getLogger ( __name__ )


def read_json_file ( file_path: Path ) -> dict :
	"""读取JSON文件内容"""
	try :
		with open ( file_path , 'r' , encoding='utf-8' ) as f :
			return json.load ( f )
	except Exception as e :
		logger.error ( f"读取JSON文件失败: {file_path}, 错误: {str ( e )}" )
		raise


def read_txt_file ( file_path: Path ) -> List[str] :
	"""读取txt文件内容并返回列表"""
	try :
		with open ( file_path , 'r' , encoding='utf-8' ) as f :
			return [line.strip () for line in f if line.strip ()]
	except Exception as e :
		logger.error ( f"读取文件失败: {file_path}, 错误: {str ( e )}" )
		raise


def send_request ( url: str , headers: Dict , payload: str , timeout: int = 10 ) -> Optional[requests.Response] :
	"""发送HTTP请求并返回响应对象"""
	try :
		logger.info ( f"尝试请求URL: {url}" )
		response = requests.post (
			url ,
			headers=headers ,
			data=payload ,
			timeout=timeout
		)
		response.raise_for_status ()  # 检查HTTP错误状态码
		return response
	except requests.exceptions.RequestException as e :
		logger.warning ( f"请求失败: {url}, 错误: {str ( e )}" )
		return None


def print_response_details ( response: requests.Response ) -> None :
	"""打印响应详情"""
	print ( "\n====== 响应详情 ======" )
	print ( f"URL: {response.url}" )
	print ( f"状态码: {response.status_code}" )
	
	try :
		print ( "响应体:" )
		print ( json.dumps ( response.json () , indent=2 , ensure_ascii=False ) )
	except ValueError :
		print ( "原始响应:" )
		print ( response.text )


def main () :
	try :
		# 读取订单ID
		order_ids = read_txt_file ( BASE_DIR / "variable/erp/order_ids.txt" )
		logger.info ( f"读取到订单ID: {order_ids}" )
		
		if not order_ids :
			logger.error ( "未读取到有效订单ID" )
			return
		
		# 读取请求头JSON文件
		headers = read_json_file ( HEADER_JSON )
		logger.info ( f"从JSON加载请求头: {headers.keys ()}" )
		
		# 添加固定请求头
		headers.update ( {
			'User-Agent' : 'Apifox/1.0.0 (https://apifox.com)' ,
			'Accept' : '*/*' ,
			'Connection' : 'keep-alive'
		} )
		
		# 构建请求体
		payload = json.dumps ( {"fulfillmentOrderIdList" : order_ids} )
		logger.info ( f"请求体: {payload}" )
		
		# 定义主备URL
		primary_url = "http://wbs-test.wbscorp.com:8080/oms/oms/order/reissue/parts/audit"
		backup_url = "http://wbs-test.wbscorp.com:8081/oms/oms/order/reissue/parts/audit"
		
		# 尝试主URL
		response = send_request ( primary_url , headers , payload )
		
		# 主URL失败时尝试备用URL
		if response is None :
			logger.warning ( "主URL请求失败，尝试备用URL..." )
			response = send_request ( backup_url , headers , payload )
			
			if response is None :
				logger.error ( "所有URL尝试均失败" )
				print ( "\n!!! 所有服务器请求均失败" )
				return
		
		# 记录响应
		logger.info ( f"最终响应状态码: {response.status_code}" )
		try :
			logger.info ( "响应体:\n" + json.dumps ( response.json () , indent=2 , ensure_ascii=False ) )
		except json.JSONDecodeError :
			logger.info ( f"原始响应: {response.text}" )
		
		# 控制台输出
		print ( "\n====== 请求详情 ======" )
		print ( f"最终使用URL: {response.url}" )
		print ( f"Headers: {json.dumps ( headers , indent=2 )}" )
		print ( f"Payload: {payload}" )
		
		print_response_details ( response )
	
	except Exception as e :
		logger.exception ( "程序执行异常" )
		print ( f"\n!!! 发生错误: {str ( e )}" )


if __name__ == "__main__" :
	main ()
