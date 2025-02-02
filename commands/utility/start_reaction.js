const { SlashCommandBuilder, MessageFlags } = require("discord.js");
const VGenerator = require("../../models/VGenerator");
const VPost = require("../../models/VPost");
const { hf_token } = require('../../config.json');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('start_reaction')
        .setDescription('Start running the generator using the flux API endpoint. Reactions gathered and used an input.'),
    async execute(interaction) {
        const gen = await VGenerator.findByPk('default');

        // Exit immediately if the generator is already running
        if (gen.timer_active) {
            interaction.reply({
                content: 'The generator is already active. Stop it with /stop before starting a new one.',
                flags: MessageFlags.Ephemeral
            });
            return;
        }

        const channelId = gen.channel_id;
        const genInterval = gen.properties.gen_interval;

        const channel = interaction.client.channels.cache.get(channelId);

        if (!channel) {
            interaction.reply({
                content: 'Target channel was not found. Make sure a target channel has been set with /setChannel.',
                flags: MessageFlags.Ephemeral
            });
            return;
        }

        // Set timer_active to be running
        gen.timer_active = true;

        const prop = gen.properties;
        prop.gen_type = 'reaction';
        gen.properties = prop;
        gen.changed('properties', true);
        
        await gen.save();

        interaction.reply({
            content: `Starting generation at ${genInterval / 1000} second intervals.`,
            flags: MessageFlags.Ephemeral
        });

        postImage(channel, genInterval);
    }
}

async function postImage(channel, genInterval) {
    let post = null;
    let imgPath = `test_${Math.floor(Math.random() * 36)+1}.png`;
    channel.send({
        files: [`./test_images/${imgPath}`]
    })
    .then(data => {
        post = data;
        VPost.findOrCreate({
            where: {
                message_id: post.id
            },
            defaults: {
                prompt: imgPath
            }
        });

        startCollector(post, genInterval);

        // post.react('👍');
    })
    .catch(console.error);
}

async function startCollector(message, genInterval) {
    const collector = message.createReactionCollector({ time: genInterval });

    collector.on('collect', async (reaction, user) => {
        const post = await VPost.findByPk(collector.message.id);

        post.users.list.push(user.id);
        post.reactions[user.id] = reaction.emoji.name;
        post.changed('users', true);
        post.changed('reactions', true);

        await post.save();
    });

    collector.on('dispose', async (reaction, user) => {
        const post = await VPost.findByPk(collector.message.id);

        const index = post.users.list.indexOf(user.id);
        if (index > -1) {
            post.users.list.splice(index, 1);
        }
        else {
            console.log(`Error: ${user.name} tried to remove a reaction, but they were not found in the post's users.`);
            return;
        }

        delete post.reactions[user.id];

        post.changed(['users', 'reactions'], true);

        await post.save();
    });

    collector.on('end', collected => {
        console.log(`Collected ${collected.size} items`);
    });
}