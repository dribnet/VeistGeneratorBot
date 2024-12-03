const { DataTypes } = require('sequelize');
const sequelize = require('../sql-database');

// Define VChannel
module.exports = sequelize.define('VChannel', {
    name: {
        type: DataTypes.STRING,
        allowNull: false
    },
    id: {
        type: DataTypes.INTEGER,
        allowNull: false,
        primaryKey: true
    }
});

