#!/usr/bin/python
# -*- coding: utf-8 -*-
import requests
import json
from pathlib import Path
from typing import Dict , Any , Optional , Union
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class ApiClient :
	"""高性能API客户端封装"""
	
	def __init__ ( self , base_url: str = "" , default_timeout: int = 10 ) :
		"""
		初始化客户端
		:param base_url: API基础地址
		:param default_timeout: 默认超时时间(秒)
		"""
		self.session = requests.Session ()
		self.base_url = base_url.rstrip ( '/' )
		self.default_timeout = default_timeout
		
		# 配置重试策略
		retry_strategy = Retry (
			total=3 ,
			backoff_factor=1 ,
			status_forcelist=[500 , 502 , 503 , 504]
		)
		
		# 配置连接池
		adapter = HTTPAdapter (
			max_retries=retry_strategy ,
			pool_connections=10 ,
			pool_maxsize=50 ,
			pool_block=False
		)
		self.session.mount ( 'http://' , adapter )
		self.session.mount ( 'https://' , adapter )
	
	def request (
			self ,
			method: str ,
			endpoint: str ,
			payload: Optional[Union[Dict , str]] = None ,
			headers: Optional[Dict[str , str]] = None ,
			**kwargs
	) -> Dict[str , Any] :
		"""
		发送API请求
		:param method: HTTP方法(GET/POST/PUT/DELETE)
		:param endpoint: API端点
		:param payload: 请求体数据
		:param headers: 请求头
		:param kwargs: 其他requests参数
		:return: 响应数据字典
		"""
		url = f"{self.base_url}/{endpoint.lstrip ( '/' )}"
		headers = headers or {}
		
		# 自动设置Content-Type
		if 'Content-Type' not in headers and isinstance ( payload , dict ) :
			headers['Content-Type'] = 'application/json'
		
		# 记录请求日志
		self._log_request ( method , url , payload , headers )
		
		try :
			response = self.session.request (
				method=method ,
				url=url ,
				json=payload if isinstance ( payload , dict ) else None ,
				data=payload if isinstance ( payload , str ) else None ,
				headers=headers ,
				timeout=kwargs.pop ( 'timeout' , self.default_timeout ) ,
				**kwargs
			)
			response.raise_for_status ()
			
			return self._process_response ( response )
		
		except requests.exceptions.RequestException as e :
			error_msg = f"API请求失败: {str ( e )}"
			self._log_error ( error_msg , response=e.response if hasattr ( e , 'response' ) else None )
			raise ApiRequestError ( error_msg ) from e
	
	def _process_response ( self , response: requests.Response ) -> Dict[str , Any] :
		"""统一处理响应"""
		try :
			resp_data = response.json ()
		except ValueError :
			resp_data = {"raw_response" : response.text}
		
		self._log_response ( response.status_code , resp_data )
		return resp_data
	
	def _log_request (
			self ,
			method: str ,
			url: str ,
			payload: Optional[Union[Dict , str]] ,
			headers: Dict[str , str]
	) :
		"""记录请求日志"""
		log_msg = [
			f"\n{'=' * 50}" ,
			f"⬆️ 请求发送: {method} {url}" ,
			"\n====== 请求头 ======" ,
			json.dumps ( headers , indent=2 , ensure_ascii=False )
		]
		
		if payload :
			log_msg.extend ( [
				"\n====== 请求体 ======" ,
				json.dumps ( payload , indent=2 , ensure_ascii=False )
				if isinstance ( payload , dict ) else payload
			] )
		
		print ( '\n'.join ( log_msg ) )
	
	def _log_response ( self , status_code: int , response_data: Dict ) :
		"""记录响应日志"""
		print (
			"\n====== 响应状态 ======" ,
			f"HTTP {status_code}" ,
			"\n====== 响应体 ======" ,
			json.dumps ( response_data , indent=2 , ensure_ascii=False ) ,
			f"\n{'=' * 50}\n" ,
			sep='\n'
		)
	
	def _log_error ( self , error_msg: str , response: Optional[requests.Response] = None ) :
		"""记录错误日志"""
		log_lines = [
			"\n⚠️ 请求异常:" ,
			error_msg
		]
		
		if response is not None :
			log_lines.extend ( [
				f"状态码: {response.status_code}" ,
				"响应体:" ,
				response.text[:500]  # 限制错误日志长度
			] )
		
		print ( '\n'.join ( log_lines ) )
	
	def post (
			self ,
			endpoint: str ,
			payload: Union[Dict , str] ,
			headers: Optional[Dict[str , str]] = None ,
			**kwargs
	) -> Dict[str , Any] :
		"""发送POST请求"""
		return self.request ( 'POST' , endpoint , payload , headers , **kwargs )


class ApiRequestError ( Exception ) :
	"""自定义API异常"""
	pass


def read_json_file ( file_path: Union[str , Path] ) -> Dict[str , Any] :
	"""
	从JSON文件读取数据
	:param file_path: JSON文件路径
	:return: 解析后的字典数据
	:raises: ValueError 如果文件不存在或JSON解析失败
	"""
	path = Path ( file_path )
	if not path.exists () :
		raise ValueError ( f"文件不存在: {file_path}" )
	
	try :
		with path.open ( 'r' , encoding='utf-8' ) as f :
			return json.load ( f )
	except json.JSONDecodeError as e :
		raise ValueError ( f"JSON解析失败: {file_path}, 错误: {str ( e )}" )
	except Exception as e :
		raise ValueError ( f"读取文件失败: {file_path}, 错误: {str ( e )}" )


def main () :
	try :
		# 1. 初始化客户端
		client = ApiClient ( base_url="http://wbs-test.wbscorp.com:8080" )
		
		# 2. 准备请求数据和头信息
		payload_path = Path ( "/Users/admin/PycharmProjects/wbs/test_case/paylo_js/bufa.json" )
		headers_path = Path ( "/Users/admin/PycharmProjects/wbs/test_case/paylo_js/header.json" )
		
		# 读取JSON文件
		payload = read_json_file ( payload_path )
		headers = read_json_file ( headers_path )
		
		# 3. 发送请求
		endpoint = "/oms/oms/order/reissue/parts/create"
		try :
			response = client.post (
				endpoint=endpoint ,
				payload=payload ,
				headers=headers ,
				timeout=15  # 可覆盖默认超时
			)
			print ( "✅ 请求成功！" )
			print ( json.dumps ( response , indent=2 , ensure_ascii=False ) )
			return response
		
		except ApiRequestError as e :
			print ( f"❌ 请求失败: {str ( e )}" )
			return None
	
	except ValueError as e :
		print ( f"❌ 配置文件错误: {str ( e )}" )
		return None
	except Exception as e :
		print ( f"❌ 程序执行出错: {str ( e )}" )
		return None


if __name__ == "__main__" :
	main ()
