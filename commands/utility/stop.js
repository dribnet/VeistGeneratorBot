const { SlashCommandBuilder } = require('discord.js');
const VGenerator = require('../../models/VGenerator');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('stop')
        .setDescription('Stop the generator.'),
    async execute(interaction) {
        
    }
};