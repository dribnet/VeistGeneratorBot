const { DataTypes } = require('sequelize');
const sequelize = require('../sql-database');

module.exports = sequelize.define('VPost', {
    message_id: {
        type: DataTypes.STRING,
        allowNull: false,
        primaryKey: true
    },
    prediction_response: {
        type: DataTypes.JSON,
        allowNull: true
    },
    prompt: {
        type: DataTypes.STRING,
        allowNull: false,
        defaultValue: ""
    },
    seed: {
        type: DataTypes.STRING,
        allowNull: true
    },
    upvotes: {
        type: DataTypes.INTEGER,
        allowNull:false,
        defaultValue: 0
    },
    downvotes: {
        type: DataTypes.INTEGER,
        allowNull: false,
        defaultValue: 0
    },
    reactions: {
        type: DataTypes.JSON,
        allowNull: false,
        defaultValue: {}
    },
    users: {
        type: DataTypes.JSON,
        allowNull: false,
        defaultValue: { list: [] }
    }
});