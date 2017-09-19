from bittrex import Bittrex
import json, csv, os, threading, sched, time
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import seaborn as sns
volumes = []
prices = []
# graph type
plt.style.use('ggplot')
# set pandas stdout options
pd.set_option('display.height', 1000)
pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 1000)

def new_markets(daysback=120):
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
	# TODO: could be interesting to plot buy orders vs sell orders vs % change in price over the time period
	marketsList = []
	bittrex = Bittrex(None, None)
	markets = bittrex.get_market_summaries()
	markets = markets['result']
	for i in range(len(markets)):
		market_name = markets[i]['MarketName'] 
		if (market_name.split('-')[0] == 'BTC'): # isolate only BTC markets
			marketsList.append(markets[i]['MarketName'])
	return marketsList
	
# def currency_price():
# 	bittrex = Bittrex(None, None)
# 	currencies = bittrex.get_currencies()
# 	currencies = currencies['result']
# 	print(currencies)
# 	for i in range(len(currencies)):
# 		print(i,currencies[i]['Currency'])

# def get_ticker(market='USDT-BTC'):
# 	bittrex = Bittrex(None, None)
# 	ticker = bittrex.get_ticker(market)
# 	last = ticker['result']
# 	print(last)
# 	return last

# def get_market_volume(market):
# 	# print(market)
# 	bittrex = Bittrex(None, None)
# 	market_summary = bittrex.get_marketsummary(market)
# 	summary = market_summary['result']
# 	volume = summary[0]['Volume']
# 	# print(market, volume)
# 	return volume

# def get_buy_orders(market):
# 	# print(market)
# 	bittrex = Bittrex(None, None)
# 	market_summary = bittrex.get_marketsummary(market)
# 	summary = market_summary['result']
# 	orders = summary[0]['OpenBuyOrders']
# 	# print(market, volume)
# 	return orders 

# def get_sell_orders(market):
# 	# print(market)
# 	bittrex = Bittrex(None, None)
# 	market_summary = bittrex.get_marketsummary(market)
# 	summary = market_summary['result']
# 	orders = summary[0]['OpenSellOrders']
# 	# print(market, volume)
# 	return orders

# def get_last_price(market):
# 	bittrex = Bittrex(None, None)
# 	market_summary = bittrex.get_marketsummary(market)
# 	summary = market_summary['result']
# 	last_price = summary[0]['Last']
# 	# print(market, volume)
# 	return last_price

def write_to_log(data='fffff'):
	for n in range(10):
		with open("log.txt", "a") as myfile:
			myfile.write(data+'\n')

def schedulerThreaded():
	s = sched.scheduler(time.time, time.sleep)
	for i in range(3):
		data = get_market_volume()
		s.enter(i*60, 1, write_to_log, argument=(str(data),))
	s.run()

def average(list,size):
	if len(list)>=size:
		average = sum(list)/size
	else:
		average = -1
	return average

def get_market_data(market, labels):
	bittrex = Bittrex(None, None)
	market_summary = bittrex.get_marketsummary(market)
	summary = market_summary['result']
	# print(market)
	data = {}
	data['Marnbket'] = market
	for key in labels:
		data[key] = summary[0][key]
	return data

def markets_correlation():
	
	x = 300 # limit of markets to test
	vol_threshold = 30000000

	marketsList = get_markets()
	main_df = pd.DataFrame() # empty df
	corr_threshold = 0.8

	for market in marketsList[:x]: #traverse the markets 
		filename = market+'.csv'
		path = os.path.join('data', filename)
		df = pd.read_csv(path,
							header=0, 
							usecols=['TimeStamp','Last','Volume']) # read csv with timestamp-object as index doing a partial loading
		df['TimeStamp'] = pd.to_datetime(df['TimeStamp'])
		df['TimeStamp'] = df['TimeStamp'].values.astype('<M8[h]') # recalculate timestamp
		volume_mean = df['Volume'].mean() # find volume mean
		df = df.drop('Volume',axis=1) # drop the volume column
		df = df.drop_duplicates(subset='TimeStamp', keep='last') # remove duplicates
		df.set_index('TimeStamp', inplace=True)
		df.rename(columns={'Last':market},inplace=True) # rename the colum with the pair name

		if volume_mean >= vol_threshold:
			if main_df.empty: # join df
				main_df = df
			else:
				main_df = main_df.join(df)
		else:
			main_df = main_df
		main_df.fillna(method='ffill', inplace=True) # fill NANs

	# print(main_df.tail(20))
	if not main_df.empty:
		corr_df = main_df.corr()
		# print(corr_df)
		for row in corr_df.iterrows():
			index, data = row
			# print(data.tolist())
			drop_row = True
			for item in data.tolist():
				if item < 1 and item >= corr_threshold:
					# print(item)
					drop_row = False # there is a candidate value
				# else:
					# corr_df = corr_df.drop(corr_df[index])
					# df.drop(df.index[[1,3]], inplace=True)
					# print(index)
			if drop_row == True:
				corr_df.drop(index, inplace=True)
				corr_df.drop(index, axis=1, inplace=True)

		# print(corr_df)
		# plt.matshow(corr_df)
		sns.heatmap(corr_df, # display correlation table
	            xticklabels=corr_df.columns.values,
	            yticklabels=corr_df.columns.values)
		plt.subplots_adjust(bottom=0.2,top=0.9, left=0.14)
		plt.show()
	else:
		print('Dataframe is empty')

def scheduler(t=60,n=3,vol_in_btc=2):
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

					# new_date = datetime.now()
					# new_volume = get_market_volume(market)
					# new_buy_orders = get_buy_orders(market)
					# new_sell_orders = get_sell_orders(market)
					# new_last_price = get_last_price(market)
					
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

def get_df_from_csv(path, dataLabels):
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

def write_csv(path, data):
	# not really needed since I am not using pandas. Pandas is awesome 
	# data should be a list 
	with open(path, 'w') as csvfile:
		csvwriter = csv.DictWriter(csvfile, fieldnames=data.keys())
		csvwriter.writeheader()
		for key,value in data.items():
			csvwriter.writerow({key:value})

def df_init(df):

	# initialize a proper dataframe 
	df['TimeStamp'] = pd.to_datetime(df['TimeStamp']) # convert to timeStamp
	df['OpenBuyOrders'] = df['OpenBuyOrders']/100000*2
	df['OpenSellOrders'] = df['OpenSellOrders']/100000/2
	df['CorrelationLastBaseVolume'] = df.corr()['Last'].tolist()[1]
	# df = df[['TimeStamp','Last','OpenBuyOrders','OpenSellOrders','CorrelationLastBaseVolume']]
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

def plot():
	plt.plot([1,2,3],[4,7,4])
	plt.show()

if __name__ == '__main__':
	# new_markets()
	# currency_price()
	# get_markets()
	# get_ticker()
	# get_market_volume()
	# write_to_log('something')
	# scheduler()
	#
	# dataLabels = ['TimeStamp','High','Low','Volume','BaseVolume','Bid','Ask','Last','OpenBuyOrders','OpenSellOrders','PrevDay']
	# get_market_data('BTC-LTC',dataLabels)

	# correlation
	# df = pd.read_csv('data/BTC-ETH.csv')
	# df_init(df)

	markets_correlation()
	# plot()
	# write_to_log()
	# print(average([1,2,3,4,5],4))
	# plot()
