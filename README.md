# davinci
A prediction tool for crypto market

Use Python3 and the following dependencies: 
- pip3 install requests
- pip3 install matplotlib
- pip3 install pandas

NOTE: open the chart (.xml) with draw.io

  

## API server setup:
**Note:** make sure you navigate to the folder ```api``` before running any npm command.

Packages:
  - install postgresql v9.4+
  - install nodes.js  v7+
  - run: ```npm install sequelize-cli -g```
  - run: ```npm install```

Database setup:
  - run postgresql server (OSX: ```brew services start postgres```)
  - open postgresql console using ```psql postgres```
  - Create a user: ```CREATE ROLE cryptovan WITH LOGIN PASSWORD 'your_password' CREATEDB SUPERUSER;```
  - Create the development database: ```craete database davinci_development;```
  - Give the user permissions to the DB: ```GRANT ALL ON DATABASE davinci_development TO cryptovan;```
  - run: ```sequelize db:migrate```
 
 Running the server:
 ```npm run start:dev```
