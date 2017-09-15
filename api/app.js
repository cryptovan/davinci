const express = require('express');
const logger = require('morgan');
// const bodyParser = require('body-parser');
const app = express();
const server = require('http').Server(app);;

var io = require("socket.io")(server);

var models = require('./models/index');
// Set up the express app


// Log requests to the console.
app.use(logger('dev'));

// Parse incoming requests data (https://github.com/expressjs/body-parser)
// app.use(bodyParser.json());
// app.use(bodyParser.urlencoded({ extended: false }));

// Setup a default catch-all route that sends back a welcome message in JSON format.
app.get('/', (req, res) => res.status(200).send({
  message: 'Welcome to davinci api',
}));

app.get('/test', (req, res) => {
	res.sendFile(__dirname + '/static/ws_test.html');
});



io.on('connection',function(socket){  
    console.log("A user is connected");
    var count = 0;
    setInterval(
    	function() {
    		io.emit("updates", "Hello! " + count++);
    	}
    , 1000);
    
});

var check_last_updates = function(callback) {

}

// module.exports = app;

const port = parseInt(process.env.PORT, 10) || 8000;
app.set('port', port);

// const server = http.createServer(app);
server.listen(port);