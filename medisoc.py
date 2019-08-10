#!/usr/bin/python
# -*- coding: utf-8 -*-

__author__ = "Georg Wallisch"
__contact__ = "gw@phpco.de"
__copyright__ = "Copyright © 2019 by Georg Wallisch"
__credits__ = ["Georg Wallisch"]
__date__ = "2019/08/09"
__deprecated__ = False
__email__ =  "gw@phpco.de"
__license__ = "open source software"
__maintainer__ = "Georg Wallisch"
__status__ = "alpha"
__version__ = "0.2"

import requests
import re
from datetime import datetime
from datetime import timedelta  
import logging
from lxml import etree
import HTMLParser
import logging

#reload(sys)
#sys.setdefaultencoding("utf-8")

class MedisocAccount:
	"""Query Medisoc Host
	"""
	
	def __init__(self, userid, password, host="www.medisoc.de", protocol = 'https', logger = None):
		if logger is None:
			console = logging.StreamHandler()
			self._log = logging.getLogger('MedisocAccount')
			self._log.addHandler(console)
		else:
			self._log = logger 
			
		self._log.info("Constructing new MedisocAccount object")
		self.userid = userid
		self.password = password
		self.host = host
		self.protocol = protocol
		self.session = requests.session()
		self.customers = None
		self.customers_header = None
	
	def login(self):
		hosturl = self.get_hosturl('/login/')
		self._log.info("Logging in..")
		self._log.debug("querying {}".format(hosturl))
		payload = {'kundennummer': self.userid, 'passwort': self.password} 
		r = self.session.post(hosturl, data=payload)
		if r:
			self._log.info("Login successful.")
			return r
		else:
			self._log.error("Login failed.")
			return None
			
	def get_hosturl(self, uri):
		return "{}://{}{}".format(self.protocol, self.host, uri)
		
	def get_xhrpage(self, uri, referrer = None):			
		hosturl = self.get_hosturl(uri)
		self._log.debug("Getting XHR Page {}".format(hosturl))
		
		if referrer is None:
			referrer = hosturl
			
		headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:68.0) Gecko/20100101 Firefox/68.0',
           'X-Requested-With': 'XMLHttpRequest',
           'Host': self.host,
           'Referer': referrer}
		
		r = self.session.get(hosturl, headers=headers)
		if r:
			return r
		else:
			self._log.error("Page does not exist!")
			return None
	
	def post_xhr(self, uri, payload, referrer = None):			
		hosturl = self.get_hosturl(uri)
		self._log.debug("Posting XHR Request {}".format(hosturl))
		
		if referrer is None:
			referrer = hosturl
			
		headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:68.0) Gecko/20100101 Firefox/68.0',
           'X-Requested-With': 'XMLHttpRequest',
           'Host': self.host,
           'Referer': referrer}
		
		r = self.session.post(hosturl, headers=headers, data=payload)
		if r:
			return r
		else:
			self._log.error("Post Request not successful!")
			return None

			
	def get_customers(self):
		t = TableParser()
		next_uri = '/startseite/massbestellung/'
		i = 0
		while(next_uri is not None):
			i += 1
			self._log.info("Reading Page {}".format(i))
			p = PaginationParser()
			r = self.get_xhrpage(next_uri)
			if r:
				t.header_firstline = True
				t.feed(r.text)
				p.feed(r.text)
			next_uri = p.next_uri
		self.customers = t.content
		self.customers_header = t.header
	
	def get_customer_history(self, pnr, include_current_orders = True):
		self._log.info("Getting Customer product history for PNR {}".format(pnr))
		t = TableParser()
		
		next_uri = "/patient/altmass/?pnr={}".format(pnr)
		i = 0
		while(next_uri is not None):
			i += 1
			self._log.info("Reading Page {}".format(i))
			p = PaginationParser()
			r = self.get_xhrpage(next_uri,'/startseite/massbestellung/')
			
			if r:
				t.header_firstline = True
				t.feed(r.text)
				p.feed(r.text)
			next_uri = p.next_uri
			
		if include_current_orders:
			self._log.info("Getting current orders of Customer PNR {}".format(pnr))
			next_uri = "/patient/altmass/?pnr={}&show=offen".format(pnr)
			i = 0
			while(next_uri is not None):
				i += 1
				self._log.info("Reading Page {}".format(i))
				p = PaginationParser()
				r = self.get_xhrpage(next_uri,'/startseite/massbestellung/')
				
				if r:
					t.header_firstline = True
					t.feed(r.text)
					p.feed(r.text)
				next_uri = p.next_uri
						
		return t.content
	
	def get_customer_data(self, pnr):
		self._log.info("Getting Customer data for PNR {}".format(pnr))

		r = self.get_xhrpage("/patient/?pnr={}".format(pnr))
		f = FormParser()
		f.feed(r.text)
		d = {'attrs':f.form_attrs, 'data':f.form_data}
		return d
		
	def set_customer_data(self, pnr, data):
		self._log.info("Setting Customer data for PNR {}".format(pnr))
		r = self.post_xhr("/patient/?pnr={}&save=true".format(pnr), data, "/patient/?pnr={}".format(pnr))
		return r
		
	def set_customer_inactive(self, pnr, info=None):
		c = self.get_customer_data(pnr)
		data = c['data']
		if 'active' in data:
			data.pop('active')
		if info is not None:
			if 'patienteninfo' in data and data['patienteninfo'] != "":
				data['patienteninfo'] += "\n" + info
			else:
				data['patienteninfo'] = info
		r = self.set_customer_data(pnr, data)
		return r	 
		
class TableParser(HTMLParser.HTMLParser):
	def __init__(self):
		HTMLParser.HTMLParser.__init__(self)
		self.in_td = False
		self.in_table = False
		self.in_tr = False
		self.header_firstline = True
		self.header = []
		self.content = []
		self.row = []
     
	def handle_starttag(self, tag, attrs):
		if tag == 'table':
			self.in_table = True
		elif tag == 'tr':
			self.in_tr = True
		elif tag == 'td':
			self.in_td = True

	def handle_data(self, data):
		d = data.strip(" \n\r\t")
		if self.in_td:
			if self.header_firstline:
				self.header.append(d)
			else:
				self.row.append(d)
			
	def handle_endtag(self, tag):
		if tag == 'table':
			self.in_table = False
		elif tag == 'tr':
			self.in_tr = False			
			if self.header_firstline:
				self.header_firstline = False
			else:
				self.content.append(self.row)
				self.row = []
		elif tag == 'td':
			self.in_td = False
			
class PaginationParser(HTMLParser.HTMLParser):
	def __init__(self):
		HTMLParser.HTMLParser.__init__(self)
		self.div_next = False
		self.next_uri = None
		#<div class="pagination-next">
		#<a href="/startseite/massbestellung/?&amp;page=2&amp;show=&amp;suche=">Vor</a>
		#</div>
     
	def handle_starttag(self, tag, attrs):
		
		if self.div_next:
			if tag == 'a':
				for attr in attrs:
					if attr[0] == 'href':
						if 'page=1&' not in attr[1]:
							self.next_uri = attr[1]
		else:
			if tag == 'div':
				for attr in attrs:
					if attr[0] == 'class' and attr[1] == 'pagination-next':						
						self.div_next = True
					
	def handle_endtag(self, tag):
		if self.div_next and tag == 'div':
			self.div_next = False	

class FormParser(HTMLParser.HTMLParser):
	def __init__(self):
		HTMLParser.HTMLParser.__init__(self)
		self.in_form = False
		self.in_textarea = False
		self.in_select = False
		self.form_attrs = None
		self.form_data = {}
		self.textarea_attrs = None
		self.select_attrs = None

	
	def parse_attrs(self, attrs):
		data = {}
		for attr in attrs:
			data[attr[0]] = attr[1]
		return data
		     
	def handle_starttag(self, tag, attrs):
		
		data = self.parse_attrs(attrs)
		if self.in_form:
			if tag == 'textarea':
				self.in_textarea = True
				self.textarea_attrs = data
			elif tag == 'select':
				self.in_select = True
				self.select_attrs = data
			elif tag == 'option':
				if 'selected' in data:
					if 'name' in data and 'value' in data:
						self.form_data[data['name']] = data['value']				
			elif tag == 'input':
				if data['type'] == 'text':
					if 'name' in data and 'value' in data:
						self.form_data[data['name']] = data['value']
				elif data['type'] == 'checkbox':
					if 'checked' in data:
						if 'name' in data and 'value' in data:
							self.form_data[data['name']] = data['value']
					else:
						if 'name' in data:
							self.form_data[data['name']] = ''					
		else:
			if tag == 'form':
				self.in_form = True
				self.form_attrs = data	
					
	def handle_data(self, data):
		d = data.strip(" \n\r\t")
		if self.in_textarea:
			self.form_data[self.textarea_attrs['name']] = d
				
					
	def handle_endtag(self, tag):
		if tag == 'form':
			self.in_form = False
		elif tag == 'textarea':
			self.in_textarea = False
		elif tag == 'select':
			self.in_select = False		
