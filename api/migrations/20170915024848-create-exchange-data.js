'use strict';
module.exports = {
  up: (queryInterface, Sequelize) => {
    return queryInterface.createTable('ExchangeData', {
      id: {
        allowNull: false,
        autoIncrement: true,
        primaryKey: true,
        type: Sequelize.INTEGER
      },
      exchange: {
        type: Sequelize.STRING
      },
      ask: {
        type: Sequelize.DOUBLE
      },
      base_volume: {
        type: Sequelize.DOUBLE
      },
      bid: {
        type: Sequelize.DOUBLE
      },
      high: {
        type: Sequelize.DOUBLE
      },
      low: {
        type: Sequelize.DOUBLE
      },
      last: {
        type: Sequelize.DOUBLE
      },
      pair: {
        type: Sequelize.STRING
      },
      open_orders: {
        type: Sequelize.INTEGER
      },
      prev_day_price: {
        type: Sequelize.DOUBLE
      },
      volume: {
        type: Sequelize.DOUBLE
      },
      createdAt: {
        allowNull: false,
        type: Sequelize.DATE
      },
      updatedAt: {
        allowNull: false,
        type: Sequelize.DATE
      }
    });
  },
  down: (queryInterface, Sequelize) => {
    return queryInterface.dropTable('ExchangeData');
  }
};