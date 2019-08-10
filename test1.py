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

import ConfigParser
import argparse
import medisoc
import sys
import os
import io
import logging
from datetime import datetime
from datetime import date
from datetime import timedelta

#reload(sys)
#sys.setdefaultencoding("utf-8")

_log = logging.getLogger('medisoc')

def main():
	
	try:
		argp = argparse.ArgumentParser(description=__doc__)
		argp.add_argument('--configfile', default=os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),'medisoc.cfg')),
				  help='Config file to use instead of standard medisoc.cfg')
		argp.add_argument('--list-without-order', action="store_true",
				  help='List all customers without any order within a defined time range')
		argp.add_argument('--list-active', action="store_true",
				  help='List all active customers')
		argp.add_argument('--set-inactive', action="store_true",
				  help='Set all selected customers inactive')
		argp.add_argument('--within-years', type=int, default=2,
				  help='amount of years (default: 2 years')
		argp.add_argument('-v', '--verbose', action='count', default=0,
					  help='increase output verbosity (use up to 3 times)')
		args = argp.parse_args()
		
		if args.verbose > 2:
			logging.basicConfig(level=logging.DEBUG)
		elif args.verbose > 1:
			logging.basicConfig(level=logging.INFO)
		elif args.verbose > 0:
			logging.basicConfig(level=logging.WARNING)
			
			
		print(u"\n\n*** Medisoc Test 1 ***\n\nBenutze Configfile: {}\n\n".format(args.configfile))
				
		with open(args.configfile) as f:
			opax_config = f.read()
		config = ConfigParser.RawConfigParser()
		config.readfp(io.BytesIO(opax_config))
		
		kdnr   = config.get('medisoc','Kundennummer')
		passwd = config.get('medisoc','Passwort')
			
	except ConfigParser.NoSectionError:
		print("Konfigurationsabschnitt fehlt!\n")
	except ConfigParser.ParsingError:
		print("Fehlerhafte Konfigurationsdatei!\n")
		raise
	except ConfigParser.Error:
		print("Allgemeiner Konfigurationsfehler!\n")
		raise

	try:
		ms = medisoc.MedisocAccount(userid=kdnr, password=passwd,logger=logging)
		r = ms.login()
		if r:
			ms.get_customers()
			print(u"Es wurden {} Kunden gefunden".format(len(ms.customers)))
			
			if args.list_active:
				for c in ms.customers:
					print(u"{:>4} {}, {} ({})".format(c[0], c[1], c[2], c[3])) 
			elif args.list_without_order:
				print(u"Suche Kunden ohne Bestellung innerhalb von {} Jahren..".format(args.within_years))
				if args.set_inactive:
					print(u"\n*** Setze diese jetzt auf inaktiv! ***\n")
				heute = date.today()
				dt = timedelta(days = args.within_years * 365)
				cnt = 0
				for c in ms.customers:
					h = ms.get_customer_history(c[0])
					last_date = None #date(2000,1,1)
					for line in h:
						cur_date = datetime.strptime(line[0], '%d.%m.%Y').date()
						if last_date is None:
							last_date = cur_date
						elif cur_date > last_date:
							last_date = cur_date
					if last_date is None:
							if args.verbose > 0:						
								print(u"Kunde {}: {} {}: Keine Bestellung bisher".format(c[0], c[1], c[2]))
							cnt += 1
							if args.set_inactive:
								ms.set_customer_inactive(c[0],u"Am {} auf inaktiv gesetzt, da bisher keine Bestellung.".format(heute.strftime('%d.%m.%Y')))							
					elif heute - last_date > dt:
							if args.verbose > 0:						
								print(u"Kunde {}: {} {}: Letzte Bestellung {}".format(c[0], c[1], c[2], last_date.strftime('%d.%m.%Y')))
							cnt += 1
							if args.set_inactive:
								ms.set_customer_inactive(c[0],u"Am {} auf inaktiv gesetzt, da letzte Bestellung vor über {} Jahren ({}).".format(heute.strftime('%d.%m.%Y'), args.within_years, last_date.strftime('%d.%m.%Y')))					
						
				print(u"Es gibt {} Kunden ohne Bestellung innerhalb von {} Jahren.".format(cnt, args.within_years))
								
#			for i in range(3):
#				c = ms.customers[i]
#				c_form = ms.get_customer_data(c[0])
#				c_data = c_form['data']
#				print(u"--------------- {}".format(c_form['attrs']['action']))
#				for e in c_data:
#					print(u"{}: {}".format(e, c_data[e]))
#				if i < 2:	
#					rr = ms.set_customer_inactive(c[0],"Zum Testen deaktiviert")
#					print rr
		else:
			print(u"Nix wars!")
			
#			
#			
#			for c in ms.customers:
#				h = ms.get_customer_history(c[0])
#				last_date = date(2000,1,1)
#				for line in h:
#					cur_date = datetime.strptime(line[0], '%d.%m.%Y').date()
#					if cur_date > last_date:
#						last_date = cur_date
#				if heute - last_date > dt:
#					print(u"Kunde {}: {} {}: ZU ALT!!, Letzte Bestellung {}".format(c[0], c[1], c[2], last_date))
#				else:
#					print(u"Kunde {}: {} {}: OK, Letzte Bestellung {}".format(c[0], c[1], c[2], last_date))
							

			
			
	except KeyboardInterrupt:
		print("\nAbbruch durch Benutzer Ctrl+C")
	except RuntimeError as e:
		print("RuntimeError: ",e)
	except Exception as e:
		    exc_type, exc_obj, exc_tb = sys.exc_info()
		    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
		    print("Unexpected error: {}".format(e))
		    print(exc_type, fname, exc_tb.tb_lineno)
		#print( sys.exc_info()[0])
	finally:
		print("Finally ended")
		
if __name__ == "__main__":
	main()