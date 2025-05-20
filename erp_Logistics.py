#!/usr/bin/python
# -*- coding:utf-8 -*-
import requests
import json
from pathlib import Path


def load_headers_from_json ( file_path: str ) -> dict :
	"""从JSON文件加载headers"""
	try :
		with open ( file_path , 'r' , encoding='utf-8' ) as f :
			headers = json.load ( f )
			if not isinstance ( headers , dict ) :
				raise ValueError ( "Headers文件内容必须是字典格式" )
			return headers
	except Exception as e :
		raise ValueError ( f"加载headers失败: {str ( e )}" )


def print_request_details ( method , url , headers , payload ) :
	"""打印请求详细信息"""
	print ( "\n====== 请求参数详情 ======" )
	print ( f"Method: {method}" )
	print ( f"URL: {url}" )
	print ( "Headers:" )
	print ( json.dumps ( headers , indent=2 , ensure_ascii=False ) )
	print ( "Payload:" )
	print ( json.dumps ( json.loads ( payload ) , indent=2 , ensure_ascii=False ) )
	print ( "=" * 30 + "\n" )


def extract_fields ( response_data , index=5 ) :
	"""从响应体中提取目标字段"""
	try :
		if isinstance ( response_data , str ) :
			response_data = json.loads ( response_data )
		
		if not isinstance ( response_data , dict ) :
			raise ValueError ( "响应数据不是有效的字典格式" )
		
		results = []
		if 'data' in response_data :
			data_items = response_data['data']
			if not isinstance ( data_items , list ) :
				raise ValueError ( "'data'字段不是列表格式" )
			
			for item in data_items :
				if not isinstance ( item , dict ) :
					continue
				
				record = {
					'item' : str ( item.get ( 'item' , '' ) ) ,
					'name' : str ( item.get ( 'name' , '' ) ) ,
				}
				results.append ( record )
			return results[index - 1] if (0 < index <= len ( results )) else None
	except Exception as e :
		print ( f"解析响应数据出错: {str ( e )}" )
		return None


def save_data ( record , file_path="/Users/admin/PycharmProjects/wbs/test_case/variable/erp/zf_logistics.txt" ) :
	"""保存单条数据到文件"""
	try :
		path = Path ( file_path )
		path.parent.mkdir ( parents=True , exist_ok=True )
		
		if record :
			line = f"{record['item']}|{record['name']}"
			with open ( path , 'w' , encoding='utf-8' ) as f :
				f.write ( line + '\n' )
			print ( f"成功保存记录到 {path.resolve ()}" )
			return True
		else :
			print ( "警告：未提取到指定索引的数据" )
			return False
	except Exception as e :
		print ( f"存储失败: {str ( e )}" )
		return False


def print_file_content ( file_path="/Users/admin/PycharmProjects/wbs/test_case/variable/erp/zf_logistics.txt" ) :
	try :
		with open ( file_path , 'r' , encoding='utf-8' ) as f :
			content = f.read ().strip ()
			print ( f"文件内容: {content}" )
			print ( f"类型验证: {type ( content )}" )
			return content
	except FileNotFoundError :
		print ( f"错误：文件 {file_path} 不存在" )
	except Exception as e :
		print ( f"读取文件失败: {str ( e )}" )


def make_request ( url , headers , payload ) :
	"""执行请求并处理响应"""
	try :
		print_request_details ( "POST" , url , headers , payload )
		response = requests.post ( url , headers=headers , data=payload , timeout=10 )
		response.raise_for_status ()
		
		print ( "\n====== 响应状态码 ======" )
		print ( f"HTTP {response.status_code}" )
		
		print ( "\n====== 响应体内容 ======" )
		response_data = response.json ()
		print ( json.dumps ( response_data , indent=2 , ensure_ascii=False ) )
		return response_data
	except requests.exceptions.RequestException as e :
		print ( f"请求失败: {str ( e )}" )
		return None


if __name__ == "__main__" :
	# 主URL和备用URL
	main_url = "http://wbs-test.wbscorp.com:8080/master/dictionary/dictItemListQuery"
	backup_url = "http://wbs-test.wbscorp.com:8081/master/dictionary/dictItemListQuery"
	
	# 从JSON文件加载headers
	headers_path = "/Users/admin/PycharmProjects/wbs/test_case/paylo_js/header.json"
	try :
		headers = load_headers_from_json ( headers_path )
	except Exception as e :
		print ( f"加载headers失败，使用默认headers: {str ( e )}" )
		headers = {
			'Content-Type' : 'application/json' ,
			'Accept' : '*/*' ,
			'User-Agent' : 'Apifox/1.0.0 (https://apifox.com)'
		}
	
	payload = json.dumps ( {
		"dictionaryType" : "DIRECT_DELIVERY_LOGISTIC"
	} )
	
	# 先尝试主URL
	response_data = make_request ( main_url , headers , payload )
	
	# 如果主URL失败，尝试备用URL
	if response_data is None :
		print ( "\n主URL请求失败，尝试备用URL..." )
		response_data = make_request ( backup_url , headers , payload )
	
	# 处理响应数据
	if response_data :
		# 提取数据并保存
		record = extract_fields ( response_data , index=6 )
		if record :
			save_data ( record )
			# 打印文件内容
			print_file_content ()
		else :
			print ( "警告：未提取到有效数据" )
	else :
		print ( "所有URL请求均失败" )
