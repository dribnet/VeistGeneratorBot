const { Sequelize } = require('sequelize');

// Using SQLite
module.exports = new Sequelize({
   dialect: 'sqlite',
   storage: './database.sqlite', // Path to SQLite file
   logging: false // Disable logging for cleaner output 
});