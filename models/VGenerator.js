const { DataTypes } = require('sequelize');
const sequelize = require('../sql-database');

module.exports = sequelize.define('VGenerator', {
    name: {
        type: DataTypes.STRING,
        allowNull: false,
        primaryKey: true
    },
    properties: {
        type: DataTypes.JSON,
        allowNull: false,
        defaultValue: {
            gen_interval: 30000,
            max_prompt_length: 100,
            gen_type: 'none'
        }
    },
    channel_id: {
        type: DataTypes.STRING,
        allowNull: false,
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
    },
    prompts: {
        type: DataTypes.JSON,
        allowNull: false,
        defaultValue: {}
    }
});