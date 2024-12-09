const { DataTypes } = require('sequelize');
const sequelize = require('../sql-database');

// Define VChannel
module.exports = sequelize.define('VGenerator', {
    name: {
        type: DataTypes.STRING,
        allowNull: false,
        primaryKey: true
    },
    channel_id: {
        type: DataTypes.STRING,
        allowNull: false,
    },
    gen_interval: {
        type: DataTypes.INTEGER, // ms
        allowNull: false,
        defaultValue: 60000 // 1 minute
    },
    timer_id: {
        type: DataTypes.BIGINT,
        allowNull: false,
        defaultValue: 0
    }
});