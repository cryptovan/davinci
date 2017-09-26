# from bittrex import Bittrex
import json, csv, os, threading, sched, time
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import seaborn as sns
import psycopg2 as pg
import pandas.io.sql as psql
import sqlalchemy

# global vars
volumes = []
prices = []

# graph type
plt.style.use('ggplot')

# set pandas display options
pd.set_option('display.height', 1000)
pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 1000)

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


def average(list,size):
	"""
	retruns the average of a list of numbers.
	If list is empty returns -1
	"""
	if len(list)>=size:
		average = sum(list)/size
	else:
		average = -1
	return average

def get_market_data(market, labels):
	"""
	return dictionary with market data. Ie.:
	{'Market': 'BTC-1ST', 'TimeStamp': '2017-09-25T17:44:19.207', 
	'High': 8.241e-05, 'Low': 7.901e-05, 'Volume': 676784.12504852, 
	'BaseVolume': 54.20717213, 'Bid': 8e-05, 'Ask': 8.075e-05, 
	'Last': 8e-05, 'OpenBuyOrders': 297, 'OpenSellOrders': 6113, 'PrevDay': 7.97e-05}
	this is the main call done from the scheduler to bittrex
	"""
	bittrex = Bittrex(None, None)
	market_summary = bittrex.get_marketsummary(market)
	summary = market_summary['result']
	data = {}
	data['Market'] = market
	for key in labels:
		data[key] = summary[0][key]
	return data

def markets_correlation():
	"""
	Generate a correlation plot between markets.
	"""
	
	x = 999 # limit of markets to test, for debugging purposes
	vol_threshold = 300000 # volume threshold beow which we discard the market [300.000]
	corr_threshold = 0.9
	
	con, meta = db_connect() # connect to db, download a list of all tables
	marketList = list(meta.tables.keys())
	
	main_df = pd.DataFrame() # empty df

	for market in marketList[:x]: #traverse the market list
		
		df = get_df_from_table(market,con) # get df from db table

		# group data based on timeframe [h:hour, m:minute]
		df=df.reset_index() # reste index for time-manipulation 
		df['TimeStamp'] = df['TimeStamp'].values.astype('<M8[m]') # recalculate timestamp
		# print(df.tail())
		
		volume_mean = df['Volume'].mean() # find volume mean, volume is used to filer out some markets
		# df = df.drop('Volume',axis=1) # drop the volume column
		
		df = df.drop_duplicates(subset='TimeStamp', keep='last') # remove duplicates
		# print(df.tail())

		df.set_index('TimeStamp', inplace=True) # set index back to timestamp
		df = df[['Last']] # drop all colums but the price
		df.rename(columns={'Last':market},inplace=True) # rename the colum with the pair name [make unique]

		if volume_mean >= vol_threshold: 
			if main_df.empty: # join df
				main_df = df
			else:
				main_df = main_df.join(df)
		else:
			main_df = main_df
		main_df.fillna(method='ffill', inplace=True) # fill NANs
		main_df.fillna(value=0, inplace=True) # fill reamining NANs with zero

	if not main_df.empty: # generate correlation table
		corr_df = main_df.corr().round(2)
		for row in corr_df.iterrows():
			index, data = row
			drop_row = True
			for item in data.tolist():
				if (item < 1 and item >= corr_threshold) or (item > -1 and item <= -corr_threshold):
					drop_row = False # there is a candidate value
			if drop_row == True:
				corr_df.drop(index, inplace=True)
				corr_df.drop(index, axis=1, inplace=True)
		# print(corr_df)
		plt.matshow(corr_df)
		sns.heatmap(corr_df, # display correlation table
				xticklabels=corr_df.columns.values,
				yticklabels=corr_df.columns.values)
		plt.subplots_adjust(bottom=0.2,top=0.9, left=0.14)
		plt.show()
	else:
		print('Dataframe is empty')

def print_tables():
	"""
	prints out list of all tables stored in the db
	"""
	con, meta = db_connect()
	n_tables = len(meta.tables)
	for table in meta.tables:
		print(table)
	print("Currently {} tables stored on the db ...".format(n_tables))

def print_all_rows(market_limit=3, tail_limit=10):
	print("Printing all rows for all tables")
	con, meta = db_connect()
	for table_name in meta.tables:
		# print(type(table))
		df = get_df_from_table(table_name, con)
		print(df.tail())
	print(">>>>> Found {} tables".format(len(meta.tables)))			

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
	ALERTS:
	@vol_alert=1.05 is the ratio above which a volume alert will be triggered
	@vol_tail = 3 is the number of time steps to look back when generating a delta-volume alert
	@vol_in_btc = 7 is the threshold above which the alert will be triggered
	"""
	
	print("Monitoring Started ...")

	# scheduler vars
	x = 3000 # limit the market search to x, for debugging purposes
	dataLabels = ['TimeStamp','High','Low','Volume','BaseVolume','Bid','Ask','Last','OpenBuyOrders','OpenSellOrders','PrevDay']

	con, meta = db_connect() # connect to db
	marketsList = get_markets() # collet all markets

	try: 
		while True:
		# nn = 0 # debug only
		# while (nn<3): # debug only
			for market in marketsList[:x]: #traverse the markets 
				table_name = market
				print("Querying {}".format(market))
				try:
					marketData = get_market_data(market,dataLabels) # returns a dictionary with data for each label
					new_row = pd.DataFrame([marketData]) # create df with new row 
					print(new_row)
					new_row.to_sql(table_name, con, if_exists='append') # append data on the table with current df
					# nn = nn + 1 # debug only
				except IOError: # in case the api connection to bittrex drops, will pass to the next cycle
					pass	
		time.sleep(t)
		print('Done.')
	except KeyboardInterrupt:
		print('interrupted!')

def scheduler_old(t=60,n=3,vol_in_btc=2):
	# t = 10 is the time interval between queries (in seconds)
	# n = 3 is the number of time steps to look back
	# vol_in_btc = 7 is the threshold above which the alert will be triggered
	volume_alert_ratio = 1.05
	x = 10000 # limit the market search to x, for debugging purposes

	marketsList = get_markets()
	dataLabels = ['TimeStamp','High','Low','Volume','BaseVolume','Bid','Ask','Last','OpenBuyOrders','OpenSellOrders','PrevDay']
	
	print("Monitoring Started ...")

	try: 
		while True:
		# nn = 0
		# while (nn<10):
			for market in marketsList[:x]: #traverse the markets 

				filename = market+'.csv'
				path = os.path.join('data', filename)
				try:
					marketData = get_market_data(market,dataLabels) # returns a dictionary with data for each label

					df = get_df_from_csv(path, dataLabels) # check if a .csv exists (or creates it) and return a df

					newdata = pd.DataFrame([marketData]) # append new data to df
					df = df.append(newdata)
					df.to_csv(path, index=False) # write out to csv

					"""
					# Alert on volume ratio
					volumes = df.tail(n)['Volume'].tolist()
					if len(volumes)>=n: 
						av = average(volumes[-n-1:-1],n)
						vol_ratio = volumes[-1:][0]/av
						# print('market: {} volumes: {}\taverage: {:.1f}\tvol_ratio: {:.1f}'.format(market, volumes, av, vol_ratio))
						if (((vol_ratio >= volume_alert_ratio) or (volume_alert_ratio <= (1-vol_ratio)))):
							vol_percentage = (vol_ratio-1)*100
							print(">>> Alert! {} Pair {} had a change of volume of {:.1f} percent in the last {:.2f} seconds".format(marketData['TimeStamp'], market, vol_percentage,t))
							
							# add alert data to log
							# new_data = {'TimeStamp':marketData[],'Market':market,'VolChange':vol_percentage,'TimeFrame':t}
							vol_datalabels = marketData.keys()
							vol_filename = 'log_volumes.csv'
							vol_path = os.path.join('data', vol_filename)
							
							vol_df = get_df_from_csv(vol_path, vol_datalabels) # check if a .csv exists (or creates it) and return a df				
							new_vol_data = pd.DataFrame([marketData]) # append new data to df
							vol_df = vol_df.append(new_vol_data)
							vol_df.to_csv(vol_path, index=False) # write out to csv
					
					# Alert on volume change in BTC
					if len(volumes)>=n: 
						vol_prev = volumes[-n-1:-1][0]
						vol_change_in_btc = (marketData['Volume']-vol_prev)*marketData['Last']
						# print(new_volume, vol_prev, new_last_price)
						# print(vol_change_in_btc)
						if (vol_change_in_btc >= vol_in_btc):
							print("### Alert! {} Pair {} had a pump of {:.1f} BTC in the last {:.2f} seconds".format(new_date, market, vol_change_in_btc,t))

							# add alert data to log
							new_data = {'TimeStamp':new_date,'Market':market,'BtcDelta':vol_change_in_btc,'TimeFrame':t}
							btc_datalabels = new_data.keys()
							btc_filename = 'log_delta_btc.csv'
							btc_path = os.path.join('data', btc_filename)
							
							btc_df = get_df_from_csv(btc_path, btc_datalabels) # check if a .csv exists (or creates it) and return a df				
							new_btc_data = pd.DataFrame([new_data]) # append new data to df
							btc_df = btc_df.append(new_btc_data)
							btc_df.to_csv(btc_path, index=False) # write out to csv
					"""
				except IOError: # in case the api connection to bittrex drops, will pass to the next cycle
				# except: # in case the api connection to bittrex drops, will pass to the next cycle
					pass	
		time.sleep(t)
	except KeyboardInterrupt:
		print('interrupted!')

def alert_volume():
	"""
	ALERTS:
	@volume_alert_ratio = ratio above which a volume alert will be triggered
	@vol_tail = 3 is the number of time steps to look back when generating a delta-volume alert
	@vol_in_btc = 7 is the threshold above which the alert will be triggered
	"""

	"""
	reorganize the df based on m h or days
	"""

	vol_tail = 3
	volume_alert_ratio = 1.2
	markets_limit = 999 # debug purpose only

	con, meta = db_connect() # connect to db, download a list of all tables
	marketList = list(meta.tables.keys())
	
	for market in marketList[:markets_limit]: #traverse the market list
		df = get_df_from_table(market,con) # get df from db table
		volumes = df.tail(vol_tail)['Volume'].tolist()
		if len(volumes)>=vol_tail: 
			av = average(volumes,vol_tail)
			vol_ratio = volumes[-1:][0]/av
			vol_percentage = (vol_ratio-1)*100
			if (vol_percentage >= volume_alert_ratio) or (vol_ratio >= (1-volume_alert_ratio)):
				time_pretty = df.tail(1).index.strftime("%A,%d. %I:%M%p")[0]
				print(">>> Alert! {} [GMT] Pair {} had a change of volume of {:.1f} percent".format(time_pretty, market, vol_percentage))
				
		# 		# add alert data to log
		# 		# new_data = {'TimeStamp':marketData[],'Market':market,'VolChange':vol_percentage,'TimeFrame':t}
		# 		vol_datalabels = marketData.keys()
		# 		vol_filename = 'log_volumes.csv'
		# 		vol_path = os.path.join('data', vol_filename)
				
		# 		vol_df = get_df_from_csv(vol_path, vol_datalabels) # check if a .csv exists (or creates it) and return a df				
		# 		new_vol_data = pd.DataFrame([marketData]) # append new data to df
		# 		vol_df = vol_df.append(new_vol_data)
		# 		vol_df.to_csv(vol_path, index=False) # write out to csv
					


def get_df_from_csv(path, dataLabels):
	"""
	read .csv file [path] and generate a df diven a list [dataLabels]
	if .csv doesn't exists creates an empty one
	"""
	# check if csv exists, if not creates it then return a handle
	if(os.path.isfile(path)):
		df = pd.read_csv(path)
		return df
	else:
		with open(path, 'w') as csvfile:
			# print(dataLabels)
			df = pd.DataFrame(columns=dataLabels)
			df.to_csv(path, index=False)
		return df

def get_df_from_table(table_name, con):
	"""
	generate a pandas df from a postgres table
	@table postgres table
	"""
	df = pd.read_sql_table(table_name, con) # get the table into a df
	df['TimeStamp'] = pd.to_datetime(df['TimeStamp']) # convert to timeStamp
	df = df.drop('index', 1) # drop the index colum
	# # df['OpenBuyOrders'] = df['OpenBuyOrders']/100000*2
	# # df['OpenSellOrders'] = df['OpenSellOrders']/100000/2
	# # df['CorrelationLastBaseVolume'] = df.corr()['Last'].tolist()[1]
	# # df = df[['TimeStamp','Last','BaseVolume','OpenBuyOrders','OpenSellOrders']]
	df=df.set_index("TimeStamp")
	return df

def df_init(df):
	"""
	THIS METHOD IS NOT IN USE ::: DELETE ME 
	convert raw data into python object according to their types
	"""
	# initialize a proper dataframe 
	df['TimeStamp'] = pd.to_datetime(df['TimeStamp']) # convert to timeStamp
	df['OpenBuyOrders'] = df['OpenBuyOrders']/100000*2
	df['OpenSellOrders'] = df['OpenSellOrders']/100000/2
	df['CorrelationLastBaseVolume'] = df.corr()['Last'].tolist()[1]
	df = df[['TimeStamp','Last','OpenBuyOrders','OpenSellOrders','CorrelationLastBaseVolume']]
	df = df[['TimeStamp','Last','BaseVolume','OpenBuyOrders','OpenSellOrders','CorrelationLastBaseVolume']]
	df=df.set_index("TimeStamp")
	# for row in df.iterrows():
		# index, data = row
		# print(index,data)
		# data = data.tolist()
		# print(data[0],data[1])
		# print(np.corrcoef(data[0],data[1]))
		# print(np.corrcoef([0.03,987],[435,987]))
	# print(df.tail())

	# print(df.corr())
	# print(df.corr()['Last'].tolist())
	# df['Correlation'] = df.corr()['Last']
	# print(df['Correlation'])
	# print(df.tail())
	# df.plot(x='TimeStamp', y=['Last','OpenBuyOrders','OpenSellOrders','Correlation'])
	# plt.show()
	# print(df['TimeStamp'])
	# print(pd.to_datetime(df['TimeStamp']).hour)
	# print(pd.to_datetime(df['TimeStamp']).dt.time)
	# print(pd.to_datetime(df['TimeStamp']).dt.minute)
	# df['datetime'].dt.time
	# pd.Datetimeindex(df['TimeStamp']).hour

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

	print_tables() # test print all tables
	# print_all_rows(market_limit=3, tail_limit=5)
	# markets_correlation()
	# alert_volume()


	"""
	tmp calls for debuggin
	"""
	# TODO: could be interesting to plot buy orders vs sell orders vs % change in price over the time period
	"""[diego@Diegos-MacBook-Pro ~/Git/davinci/api]$ psql -U cryptovan davinci_development"""

