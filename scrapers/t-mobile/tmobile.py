#!/usr/bin/python -tt

# T-Mobile online account management scraper
# (c) 2008 Matthew J Ernisse <mernisse@ub3rgeek.net>
# (c) 2010 John Morrissey <jwm@horde.net>
#
# Redistribution and use in source and binary forms, 
# with or without modification, are permitted provided 
# that the following conditions are met:
#
#    * Redistributions of source code must retain the 
#      above copyright notice, this list of conditions 
#      and the following disclaimer.
#    * Redistributions in binary form must reproduce 
#      the above copyright notice, this list of conditions 
#      and the following disclaimer in the documentation 
#      and/or other materials provided with the distribution.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS 
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT 
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS 
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE 
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, 
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, 
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS 
# OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND 
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR 
# TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE 
# USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# 10 digit T-Mobile US telephone number.
PHONE_NUMBER = ''
# my.t-mobile.com password for the above mobile number.
PASSWORD = ''

# This e-mail address will be appended to the User-Agent header, so
# the site can contact you about your scraping if they so desire.
OWNER = ''

PROXY = ''

DEBUG = False


import getopt
import logging
import os
import re
import sys
import urllib2

import BeautifulSoup
import ClientForm
import mechanize

def usage():
	print 'T-Mobile online account management scraper'
	print 'Usage: ' + os.path.basename(sys.argv[0]) + ' [-D|--skip-detail] [-h|--help] [-l|--list] [-s|--summary] DATE'
	print ''
	print '    -D, --skip-detail  omit detail when retrieving full bill'
	print '    -h, --help         display this help and exit'
	print '    -l, --list         list available bill dates'
	print '    -s, --summary      display account summary'

try:
	options, when = getopt.gnu_getopt(sys.argv[1:], 'Dhls',
		['skip-detail', 'help', 'list', 'summary'])
except getopt.GetoptError, e:
	print os.path.basename(sys.argv[0]) + ': ' + str(e)
	usage()
	sys.exit(1)

LIST_ALL = False
SKIP_DETAIL = False
SUMMARY = False
for option in options:
	if option[0] == '-D' or option[0] == '--skip-detail':
		SKIP_DETAIL = True
	elif option[0] == '-h' or option[0] == '--help':
		usage()
		sys.exit(1)
	elif option[0] == '-l' or option[0] == '--list':
		LIST_ALL = True
	elif option[0] == '-s' or option[0] == '--summary':
		SUMMARY = True

if not PHONE_NUMBER or not PASSWORD or not OWNER:
	sys.exit('Please edit %s and follow the directions in the comments.' %
		sys.argv[0])

if LIST_ALL and len(when) > 0:
	usage()
	sys.exit(1)
if SUMMARY and (LIST_ALL or SKIP_DETAIL or len(when) > 0):
	usage()
	sys.exit(1)

if not SUMMARY and not LIST_ALL:
	if len(when) != 1:
		usage()
		sys.exit(1)
	when = when[0]

br = mechanize.Browser()
br.set_handle_robots(False)
br.set_handle_refresh(True, 10, True)
br.set_handle_redirect(True)
br.addheaders = [
	('User-agent',
		'Mozilla/5.0 (X11; U; Linux i686; en-US; rv 1.0) %s' % OWNER),
]
if PROXY:
	br.set_proxies({
		'http': PROXY,
		'https': PROXY,
	})

if DEBUG:
	br.set_debug_http(True)
	br.set_debug_responses(True)
	br.set_debug_redirects(True)
	logger = logging.getLogger('mechanize')
	logger.addHandler(logging.StreamHandler(sys.stdout))
	logger.setLevel(logging.DEBUG)

try:
	br.open('https://my.t-mobile.com/login/MyTmobileLogin.aspx')
except urllib2.HTTPError, e:
	sys.exit("%d: %s" % (e.code, e.msg))
if not br.viewing_html():
	sys.exit('Unable to retrieve HTML for login page, has my.t-mobile.com changed?')

# Build the form. This is normally done by JavaScript on the site.
form = list(br.forms())[0]
et = ClientForm.HiddenControl('hidden', '__EVENTTARGET',
	{'value': 'Login1$btnLogin'})
form.controls.append(et)
ea = ClientForm.HiddenControl('hidden', '__EVENTARGUMENT', {'value': ''})
form.controls.append(ea)

try:
	br.select_form('Form1')
except mechanize.FormNotFoundError:
	sys.exit('Unable to locate login form, has my.t-mobile.com changed?')

br['Login1:txtMSISDN'] = PHONE_NUMBER
br['Login1:txtPassword'] = PASSWORD

try:
	r = br.submit()
except urllib2.HTTPError, e:
	sys.exit('%d: %s' % (e.code, e.msg))

if SUMMARY:
	try:
		r = br.open('https://my.t-mobile.com/PartnerServices.aspx?service=eBill&link=MonthlyUsage')
		r = br.open('https://ebill.t-mobile.com/myTMobile/getUnbilledUsages.do?FromJSONCall=true&msisdn0=%s' % PHONE_NUMBER)
		r = br.open('https://ebill.t-mobile.com/myTMobile/pages/modunbilledusage/unbilledUsageOverview.jsp')
	except urllib2.HTTPError, e:
		sys.exit('%d: %s' % (e.code, e.msg))
	if not br.viewing_html():
		sys.exit('Unable to retrieve HTML for usage summary page, has my.t-mobile.com changed?')

	soup = BeautifulSoup.BeautifulSoup(r.get_data())
	summary = soup.find('table', attrs={'id': 'tblMinuteUsageSummary'})

	services = summary.findAll(attrs={'class': re.compile(r'(^|\s+)ubmu_service(\s+|$)')})
	for service in services:
		row = service.findParent('tr')
		used = row.find(attrs={'class': re.compile(r'(^|\s+)ubmu_used(\s+|$)')})
		included = row.find(attrs={'class': re.compile(r'(^|\s+)ubmu_included(\s+|$)')})
		print '%s: %s / %s' % (
			service.findChild(text=True), used.findChild(text=True),
			included.findChild(text=True),
		)

try:
	r = br.open('https://my.t-mobile.com/PartnerServices.aspx?service=eBill&link=DetailsUsage&unavid=viewbill')
except urllib2.HTTPError, e:
	sys.exit("%d: %s" % (e.code, e.msg))
if not br.viewing_html():
	sys.exit('Unable to retrieve HTML for bill selection page, has my.t-mobile.com changed?')

soup = BeautifulSoup.BeautifulSoup(r.get_data())
bill_links = {}

billdate_re = re.compile(r'.*Bill\s+date:\s*\w{3} (\w{3} \d{2}) \d{2}:\d{2}:\d{2} \w{3} (\d{4}).*',
	flags=re.I + re.S)
for bill in soup.findAll(text=re.compile(r'Bill\s+date:')):
	date = billdate_re.sub(r'\1 \2', bill)

	while bill.parent:
		bill = bill.parent

		if 'selectedbill' in bill.get('class', '').split():
			# The currently selected bill is displayed on the current page.
			url = None
			break

		view = bill.find(text=re.compile('View\s+Bill'))
		if not view:
			if bill.name == 'li':
				# If we go up further, we risk catching the bill URL for
				# a different month.
				raise Exception('Unable to locate bill cycle selection URL for %s.' % date)
			continue
		url = view.findParent('a')['href']

	bill_links[date] = url

if LIST_ALL:
	for date in bill_links:
		print date
	sys.exit(0)

try:
	if bill_links[when]:
		r = br.open('https://ebill.t-mobile.com/myTMobile/%s' % bill_links[when])
	r = br.open('https://ebill.t-mobile.com/myTMobile/onPrintBill.do')
except urllib2.HTTPError, e:
	sys.exit("%d: %s" % (e.code, e.msg))
if not br.viewing_html():
	sys.exit('Unable to retrieve HTML for printable bill, has my.t-mobile.com changed?')

if SKIP_DETAIL:
	soup = BeautifulSoup.BeautifulSoup(r.get_data())
	soup.find(id='LocalAirtimeDetailData').extract()
	soup.find(id='MessagingChargesDetailData').extract()
	soup.find(id='DataServiceChargesDetailData').extract()
	print soup
else:
	print r.get_data()
