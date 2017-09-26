from bittrex import Bittrex
import os, threading, time
from datetime import datetime, timedelta
import pandas as pd
import pandas.io.sql as psql
import sqlalchemy

# This info should probably be stored in a json file
# db_location = 'local' # db location
db_location = 'foo' # db location
if (db_location == 'local'): # connects to local db or remote one on heroku
	user = "cryptovan"
	password="cryptoftw#421"
	db="davinci_development"
	host = 'localhost'
	port = 5432
else:
	user="aqhgnocrccmwgg"
	password="fa198151f144ec06d5e2a58411db39dc55a0345cf642a2a11ebe81b464967e14"
	db="dab80rgl8696qb"
	host="ec2-54-225-88-191.compute-1.amazonaws.com"
	port="5432"

def new_markets(daysback=120):
	"""
	Prints out the new markets (coin pairs) added in the last X days, where X is @daysback
	"""
	bittrex = Bittrex(None, None)
	now = datetime.now()
	# markets
	markets = bittrex.get_market_volumes()
	markets = markets['result']
	for i in range(len(markets)):
		marketname = markets[i]['MarketName']
		if(marketname.split('-')[0]=='BTC'):
			created = markets[i]['Created']
			try: # some dates don't have microseconds
				datetime_object = datetime.strptime(created, '%Y-%m-%dT%H:%M:%S')
			except:
				datetime_object = datetime.strptime(created, '%Y-%m-%dT%H:%M:%S.%f')
			date_N_days_ago = datetime.now() - timedelta(days=daysback)
			# output new currency pairs
			if (datetime_object >= date_N_days_ago):
				print(i,marketname,created)

def get_markets():
	"""
	returns a list of available markets [BTC only]
	"""
	marketsList = []
	bittrex = Bittrex(None, None)
	markets = bittrex.get_market_summaries()
	markets = markets['result']
	for i in range(len(markets)):
		market_name = markets[i]['MarketName'] 
		if (market_name.split('-')[0] == 'BTC'): # isolate only BTC markets
			marketsList.append(markets[i]['MarketName'])
	return marketsList
	
def schedulerThreaded():
	"""
	TODO: not in use, need to replace sleep timer with threaded version
	"""
	s = sched.scheduler(time.time, time.sleep)
	for i in range(3):
		data = get_market_volume()
		s.enter(i*60, 1, write_to_log, argument=(str(data),))
	s.run()

def get_market_data(market, labels):
	"""
	return dictionary with market data. Ie.:
	{'Marnbket': 'BTC-1ST', 'TimeStamp': '2017-09-25T17:44:19.207', 
	'High': 8.241e-05, 'Low': 7.901e-05, 'Volume': 676784.12504852, 
	'BaseVolume': 54.20717213, 'Bid': 8e-05, 'Ask': 8.075e-05, 
	'Last': 8e-05, 'OpenBuyOrders': 297, 'OpenSellOrders': 6113, 'PrevDay': 7.97e-05}
	this is the main call done from the scheduler to bittrex
	"""
	bittrex = Bittrex(None, None)
	market_summary = bittrex.get_marketsummary(market)
	summary = market_summary['result']
	data = {}
	data['Marnbket'] = market
	for key in labels:
		data[key] = summary[0][key]
	return data

def print_tables():
	"""
	prints out list of all tables stored in the db
	"""
	con, meta = db_connect()
	n_tables = len(meta.tables)
	for table in meta.tables:
		print(table)
	print("Currently {} tables stored on the db ...".format(n_tables))

def print_all_rows(tail_limit=10):
	print("Printing all rows for all tables")
	con, meta = db_connect()
	for table in meta.tables:
		# print(table)
		table_name = meta.tables[table].name
		print(table_name)
		df = pd.read_sql_table(table_name, con)
		print(df.tail(tail_limit))					

def clear_db():
	"""
	Deletes all the tables on the db
	"""
	con, meta = db_connect()
	print('Deleting all tables ...')
	# for table in meta.tables:
		# con.execute(table.delete())
	for tbl in (meta.tables):
		# con.execute(meta.tables[tbl].delete())
		meta.tables[tbl].drop()
		# print(type(meta.tables[tbl]))
		# print(tbl)

def scheduler(t=60, vol_alert=1.05, vol_tail=3, vol_in_btc=2):
	
	"""
	executes a query to collect real-time bittrex data and sore it into postgres db tables
	GENERAL:
	@t = 60 is the time interval between queries (in seconds)
	"""
	
	print("Monitoring Started ...")

	# scheduler vars
	markets_limit = 999 # limit the market search to markets_limit, for debugging purposes only	
	dataLabels = ['TimeStamp','High','Low','Volume','BaseVolume','Bid','Ask','Last','OpenBuyOrders','OpenSellOrders','PrevDay']

	con, meta = db_connect() # connect to db
	marketsList = get_markets() # collet all markets

	try: 
		while True:
		# nn = 0 # debug only
		# while (nn<3): # debug only
			print("Querying {} markets".format(min(markets_limit,len(marketsList))))
			for market in marketsList[:markets_limit]: #traverse the markets 
				table_name = market
				try:
					marketData = get_market_data(market,dataLabels) # returns a dictionary with data for each label
					new_row = pd.DataFrame([marketData]) # create df with new row 
					# print(new_row)
					new_row.to_sql(table_name, con, if_exists='append') # append data on the table with current df
					# nn = nn + 1 # debug only
				except IOError: # in case the api connection to bittrex drops, will pass to the next cycle
					pass	
			time.sleep(t)
		print('Done.')
	except KeyboardInterrupt:
		print('interrupted!')

def db_connect():
	"""
	returns a connection and a metadata object
	we connect with the help of the PostgreSQL URL: postgresql://federer:grandestslam@localhost:5432/tennis
	connection variables are specified in the global section to be accessible from all methods
	"""
		
	url = 'postgresql://{}:{}@{}:{}/{}'
	url = url.format(user, password, host, port, db) # fetch these variable from globals

	# The return value of create_engine() is our connection object
	
	# CHECK THIS FOR SSL CONNECTION 
	con = sqlalchemy.create_engine(url, client_encoding='utf8') # normal connection withouth SSL
	# con = sqlalchemy.create_engine(url, connect_args={'sslmode':'require'}, client_encoding='utf8') # this is for heroku
	#################################

	# We then bind the connection to MetaData()
	meta = sqlalchemy.MetaData(bind=con, reflect=True)

	return con, meta

if __name__ == '__main__':

	# clear_db() # clear db
	scheduler() # start the scheduler
	# print_tables() # test print all tables
	# print_all_rows()

	# TODO: could be interesting to plot buy orders vs sell orders vs % change in price over the time period
