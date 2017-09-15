'use strict';
module.exports = (sequelize, DataTypes) => {
  var ExchangeData = sequelize.define('ExchangeData', {
    exchange: DataTypes.STRING,
    ask: DataTypes.DOUBLE,
    base_volume: DataTypes.DOUBLE,
    bid: DataTypes.DOUBLE,
    high: DataTypes.DOUBLE,
    low: DataTypes.DOUBLE,
    last: DataTypes.DOUBLE,
    pair: DataTypes.STRING,
    open_orders: DataTypes.INTEGER,
    prev_day_price: DataTypes.DOUBLE,
    volume: DataTypes.DOUBLE
  }, {
    classMethods: {
      associate: function(models) {
        // associations can be defined here
      }
    }
  });
  return ExchangeData;
};