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
    current_upvotes: {
        type: DataTypes.INTEGER,
        allowNull: false,
        defaultValue: 0
    },
    current_downvotes: {
        type: DataTypes.INTEGER,
        allowNull: false,
        defaultValue: 0
    },
    users : {
        type: DataTypes.JSON,
        allowNull: false,
        defaultValue: { list: [] }
    }
});