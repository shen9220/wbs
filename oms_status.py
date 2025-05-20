#!/usr/bin/python
# -*- coding:utf-8 -*-
import requests
import json
from pathlib import Path
from typing import Dict , List , Any , Union
from dataclasses import dataclass
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import importlib.util
import sys


@dataclass
class ApiConfig :
	"""API配置数据类"""
	primary_url: str
	fallback_url: str
	payload: Union[Dict[str , Any] , str , Path]
	headers: Union[Dict[str , str] , str , Path]
	timeout: int = 10


class ApiClient :
	"""高性能API客户端"""
	
	def __init__ ( self , config: ApiConfig ) :
		self.config = config
		self.session = requests.Session ()
		adapter = HTTPAdapter (
			max_retries=Retry ( total=3 , backoff_factor=1 , status_forcelist=[500 , 502 , 503 , 504] ) ,
			pool_connections=10 ,
			pool_maxsize=50
		)
		self.session.mount ( 'http://' , adapter )
		self.session.mount ( 'https://' , adapter )
	
	def _load_data ( self , source: Union[Dict , str , Path] ) -> Any :
		"""通用数据加载方法，支持JSON文件和Python模块"""
		if isinstance ( source , dict ) :
			return source
		
		path = Path ( source )
		if not path.exists () :
			raise FileNotFoundError ( f"文件不存在: {path}" )
		
		# 如果是Python文件(.py)
		if path.suffix == '.py' :
			try :
				# 动态导入Python模块
				module_name = f"module_{path.stem}"
				spec = importlib.util.spec_from_file_location ( module_name , path )
				module = importlib.util.module_from_spec ( spec )
				sys.modules[module_name] = module
				spec.loader.exec_module ( module )
				
				# 获取模块中的json_template变量
				if hasattr ( module , 'json_template' ) :
					# 从文件加载ID列表
					txt_path = Path ( "/Users/admin/PycharmProjects/wbs/test_case/variable/oms/sql_ids.txt" )
					try :
						with open ( txt_path , 'r' , encoding='utf-8' ) as f :
							ids = [line.strip () for line in f if line.strip ()]
							module.json_template["platformOrderIdList"] = ids
					except IOError as e :
						raise Exception ( f"无法加载ID文件: {str ( e )}" )
					
					return module.json_template
				else :
					raise AttributeError ( f"Python模块中未找到json_template变量: {path}" )
			except Exception as e :
				raise Exception ( f"加载Python文件失败: {str ( e )}" )
		# 如果是JSON文件
		else :
			try :
				with open ( path , 'r' , encoding='utf-8' ) as f :
					return json.load ( f )
			except Exception as e :
				raise Exception ( f"加载JSON文件失败: {str ( e )}" )
	
	def execute_request ( self ) -> Dict[str , Any] :
		"""执行API请求"""
		payload = self._load_data ( self.config.payload )
		headers = self._load_data ( self.config.headers )
		
		print ( "\n====== 请求参数 ======" )
		print ( f"URL: {self.config.primary_url}" )
		print ( f"Headers: {json.dumps ( headers , indent=2 , ensure_ascii=False )}" )
		print ( f"Payload: {json.dumps ( payload , indent=2 , ensure_ascii=False )}" )
		
		try :
			response = self.session.post (
				url=self.config.primary_url ,
				json=payload ,
				headers=headers ,
				timeout=self.config.timeout
			)
			if response.status_code == 502 :
				response = self.session.post (
					url=self.config.fallback_url ,
					json=payload ,
					headers=headers ,
					timeout=self.config.timeout
				)
			response.raise_for_status ()
			return response.json ()
		except requests.exceptions.RequestException as e :
			raise Exception ( f"API请求失败: {str ( e )}" )


def extract_fulfillment_ids ( data: Dict ) -> List[str] :
	"""从响应数据中提取所有fulfillmentOrderId"""
	ids = set ()
	for order in data.get ( "data" , [] ) :
		if "fulfillmentOrderId" in order :
			ids.add ( order["fulfillmentOrderId"] )
		for item in order.get ( "afterSaleItemList" , [] ) :
			for goods in item.get ( "reissueGoodsInfoList" , [] ) :
				if "fulfillmentOrderId" in goods :
					ids.add ( goods["fulfillmentOrderId"] )
	return list ( ids )


def save_to_file ( ids: List[str] , file_path: Union[str , Path] ) -> None :
	"""将ID列表保存到文件"""
	try :
		path = Path ( file_path )
		path.parent.mkdir ( parents=True , exist_ok=True )
		with open ( path , 'w' , encoding='utf-8' ) as f :
			f.write ( '\n'.join ( ids ) + '\n' )
		print ( f"\n成功保存{len ( ids )}个ID到: {path.resolve ()}" )
	except IOError as e :
		raise Exception ( f"文件保存失败: {str ( e )}" )


def main () :
	try :
		# 配置API参数
		api_config = ApiConfig (
			primary_url="http://wbs-test.wbscorp.com:8080/oms/oms/order/reissue/parts/page" ,
			fallback_url="http://wbs-test.wbscorp.com:8081/oms/oms/order/reissue/parts/page" ,
			payload=Path ( "/Users/admin/PycharmProjects/wbs/test_case/paylo_js/status_json.py" ) ,
			# 使用Python文件作为payload
			headers=Path ( "/Users/admin/PycharmProjects/wbs/test_case/paylo_js/header.json" ) ,
			timeout=15
		)
		
		# 执行API请求
		response_data = ApiClient ( api_config ).execute_request ()
		print ( "\n====== 响应数据 ======" )
		print ( json.dumps ( response_data , indent=2 , ensure_ascii=False ) )
		
		# 提取并保存ID
		fulfillment_ids = extract_fulfillment_ids ( response_data )
		print ( "\n提取到的唯一ID:" , fulfillment_ids )
		
		if fulfillment_ids :
			save_to_file ( fulfillment_ids ,
			               Path ( "/Users/admin/PycharmProjects/wbs/test_case/variable/erp/order_ids.txt" ) )
		else :
			print ( "警告: 未提取到有效ID" )
	
	except Exception as e :
		print ( f"\n发生错误: {str ( e )}" , file=sys.stderr )
		sys.exit ( 1 )


if __name__ == "__main__" :
	main ()
