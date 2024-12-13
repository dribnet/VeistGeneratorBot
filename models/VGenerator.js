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
        defaultValue: 30000 // 30s
    },
    timer_active: {
        type: DataTypes.BOOLEAN,
        allowNull: false,
        defaultValue: false
    },
    current_post_id: {
        type: DataTypes.STRING,
        allowNull: true,
        defaultValue: null
    }
});