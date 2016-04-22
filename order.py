#!/usr/bin/env python
# -*- coding: utf_8 -*-
# @Author: stupig

import time
import requests
import re
from PIL import Image
import pytesseract
import signal

index_url = "http://my.seu.edu.cn"
order_url = "http://yuyue.seu.edu.cn"
login_vcode_path = ""

def down_validate_code(req, img_path):
	with open('validateimage', 'wb') as validate_file:
		img_stream = req.get(img_path, stream=True)
		for chunk in img_stream.iter_content(chunk_size=1024):
			if chunk:
				validate_file.write(chunk)
				validate_file.flush()
		validate_file.close()

def login(req, code, user, passwd):
	form_data = {
	"Login.Token1": user,
	"Login.Token2": passwd,
	"captcha": code,
	"goto": "http://my.seu.edu.cn/loginSuccess.portal",
	"gotoOnFail": "http://my.seu.edu.cn/loginFailure.portal"
	}
	res = req.post(index_url + "/userPasswordValidate.portal", data=form_data)

	# print '[*] Return code is ' + res.text

	return res.text

def get_validate_code(req, validate_code_path):
	vcode = ''
	while True:
		if re.match('\w{4}', vcode) is None:
			down_validate_code(req, validate_code_path)

			image = Image.open('validateimage')
			vcode = pytesseract.image_to_string(image)
			vcode = vcode[:4]
		else:
			print '[*] validate code is ' + vcode
			break
	return vcode

def get_order_date():
	year = time.strftime('%Y')
	month = time.strftime('%m')
	day = time.strftime('%d')
	order_day = int(day) + 2
	date = year + '-' + month + '-' + str(order_day)

	return date

def get_time_list(req, time_list_path, order_item, order_day):
	form_data = {
	"itemId": order_item,
	"dayInfo": order_day,
	"pageNumber": '1'
	}
	res = req.post(time_list_path, data=form_data)

	# print '[*] Return code is ' + res.text
	pat = re.compile("orderSite\(\'(.*)\'\)")
	return pat.findall(res.text)

def insert_order(req, to_order_path, validateimage_path, to_order_time, PHONE, order_item, userId):
	vcode = get_validate_code(req, validateimage_path)
	print '[*] validate code again is ' + vcode
	form_data = {
	"orderVO.useTime": to_order_time,
	"orderVO.itemId": order_item,
	"orderVO.useMode": "2",
	"useUserIds": userId,
	"orderVO.phone": PHONE,
	"orderVO.remark": "",
	"validateCode": vcode
	}
	res = req.post(to_order_path, data=form_data)

	print '[*] log status ' + res.text

	if res.text=="success":
		return True
	return False

def to_make_order(req, to_order_path, validateimage_path, order_day, time_list, PHONE, order_item, userId):
	for time in time_list:
		to_order_time = order_day
		if time.startswith('18'):
			to_order_time = to_order_time + " " + time
		elif time.startswith('19'):
			to_order_time = to_order_time + " " + time
		elif time.startswith('20'):
			to_order_time = to_order_time + " " + time
		if len(to_order_time) > len(order_day):
			print "[*] " + to_order_time + " is available"

			# to order here
			if insert_order(req, to_order_path, validateimage_path, to_order_time, PHONE, order_item, userId):
				return True
	return False

def to_sleep(secs):
	hour = time.strftime("%H")
	minute = time.strftime("%M")
	if int(hour) == 8:
		if int(minute) > 10:
			sleep(secs)
	elif int(hour) == 7:
		if int(minute) < 56:
			sleep(120)
	else:
		print '[*] sleep for ' + str(secs) + ' seconds'
		time.sleep(secs)

to_exit = False

def signal_handler(signal, frame):
	print '[*] Ctrl + C is pressed'
	global to_exit
	to_exit = True

if __name__ == '__main__':
	print "[-] thread start..."
	signal.signal(signal.SIGINT, signal_handler)

	## parameter block
	USERNAME = 'USERNAME'
	PASSWORD = 'PASSWORD'
	PHONE = "PHONE_NUMBER"
	order_item = "10"		# the project you wanna order, 10 for badminton; 8 for basketball, 12 for fitness
	userId = "YOURPARTNERID"		# user ID in system, if you wanna order fitness, userId should be NULL

	while not to_exit:
		print '[-] open session'

		try:

			req = requests.session()

			is_login = False
			# continue to login before login successfully
			while not is_login:

				# get validate code used to login
				validate_code_path = index_url + '/captchaGenerate.portal'
				vcode = get_validate_code(req, validate_code_path)

				res = login(req, vcode, USERNAME, PASSWORD)
				if re.search('Successed', res):
					print '[-] login successed'
					is_login = True
				else:
					print '[-] login failed'

			# now we are happy to order the badminton
			order_day = get_order_date()
			print '[-] now time: ' + order_day + " " + time.strftime("%H:%M:%S")

			time_list_path = order_url + "/eduplus/order/order/getOrderInfo.do?sclId=1"
			time_list = get_time_list(req, time_list_path, order_item, order_day)
			if not time_list:
				print '[-] list is empty'
				to_sleep(3300)			# 55 minutes
			else:
				order_path = order_url + "/eduplus/order/order/order/insertOredr.do?sclId=1"
				validateimage_path = order_url + "/eduplus/control/validateimage"
				order_success = to_make_order(req, order_path, validateimage_path, order_day, time_list, PHONE, order_item, userId)

				if order_success:
					print '[-] order successful'
					time.sleep(21600)	# six hour
				else:
					print '[-] order failed'
					to_sleep(3300)		# 55 minutes

			print '[-] close session'
			req.close()

			print ''

		except requests.exceptions.ConnectionError:
			print '[-] connection error: max retries exceeded with URL'

	print '[-] thread end...'
