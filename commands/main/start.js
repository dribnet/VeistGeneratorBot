const {
    SlashCommandBuilder,
    MessageFlags
} = require("discord.js");
const VGenerator = require("../../models/VGenerator");
const VPost = require("../../models/VPost");
const {
    hf_token
} = require('../../config.json');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('start')
        .setDescription('Start the generator.')
        .addStringOption(option =>
			option.setName('metric')
				.setDescription('The metric to use for voting.')
				.setRequired(true)
				.addChoices(
					{ name: 'Reactions', value: 'reactions' },
					{ name: 'Poll', value: 'poll' },
				)),
    async execute(interaction) {
        const metric = interaction.options.getString('metric');

        const generator = await VGenerator.findByPk(interaction.guildId);

        // This check may become deprecated in the future once the database entry is
        // created when the bot joins the server
        if (!generator) {
            interaction.reply({
                content: 'The generator has not been initialised in this guild.',
                flags: MessageFlags.Ephemeral
            });
            return;
        }

        const genInterval = generator.properties.generator_interval;

        // Exit if the generator is already running
        if (generator.is_active) {
            interaction.reply({
                content: 'The generator is already active',
                flags: MessageFlags.Ephemeral
            });
            return;
        }

        const channelId = generator.properties.target_channel_id;

        if (channelId == -1) {
            interaction.reply({
                content: 'A target channel has not been set. Use /setChannel to target a channel for the generator to run in.',
                flags: MessageFlags.Ephemeral
            });
            return;
        }

        const channel = interaction.guild.channels.cache.get(channelId);

        if (!channel) {
            interaction.reply({
                content: 'The target channel couldn\'t be found. Try setting the channel again with /setChannel',
                flags: MessageFlags.Ephemeral
            });
            return;
        }

        generator.is_active = true;
        generator.properties.voting_metric = metric;
        generator.changed('properties', true);
        await generator.save();

        interaction.reply({
            content: `🔄 Starting generation at ${genInterval / 1000} second intervals.`,
            flags: MessageFlags.Ephemeral
        });

        await postImage(generator, channel, metric);
        const timerId = setInterval(async () => {
            const gen = await VGenerator.findByPk(interaction.guildId);
            if (!gen.is_active) {
                clearInterval(timerId);
                return;
            }

            await postImage(gen, channel, metric);
        }, genInterval);

    }
}

async function postImage(generator, channel, metric) {
    // Generate image
    const {
        Client
    } = await import('@gradio/client'); // Dynamic import
    const client = await Client.connect('black-forest-labs/FLUX.1-schnell', {
        hf_token: hf_token
    });

    // Construct prompt
    let prompt = "";
    for (let key in generator.prompts) {
        if (gen.prompts.hasOwnProperty(key)) {
            const val = generator.prompts[key].prompt;
            prompt += `${val}, `;
        }
    }
    prompt = prompt.replace(/,\s*$/, '');

    try {
        const response = await client.predict('/infer', {
            prompt,
            seed: 0,
            randomize_seed: true,
            width: 512,
            height: 512,
            num_inference_steps: 4
        });
        const imgData = response.data;
        const imgPost = await channel.send({
            content: "🎨 New generation",
            files: [imgData[0].url]
        })

        await VPost.findOrCreate({
            where: {
                guild_id: channel.guildId,
                message_id: imgPost.id
            },
            defaults: {
                prediction_response: imgData[0],
                prompt: prompt,
                seed: imgData[1]
            }
        });
        
        if (metric == 'reactions') {
            // I get the reactions once at the end of the cycle to guarantee the correct numbers of reactions are collected. ReactionCollector doesn't detect when reactions are removed
            const reactionsTimer = setTimeout(async () => {
                const postData = await VPost.findOne({
                    where: { guild_id: channel.guildId, message_id: imgPost.id },
                    rejectOnEmpty: true
                })

                const message = await channel.messages.fetch(imgPost.id); // We have to re-fetch the message 'imgPost' only has the data from when it was posted.
                const reactions = message.reactions.cache.map(reaction => ({
                    emoji: reaction.emoji.name,
                    users: reaction.users.cache.map(user => user.id)
                }));

                postData.reactions.cache = reactions;
                postData.changed('reactions', true);

                postData.users.cache = [...new Set(reactions.flatMap(item => item.users))];
                postData.changed('users', true);

                await postData.save();

                message.reply({
                    content: `Received ${reactions.length} rea`
                });
            }, generator.properties.generator_interval);
        }
        else if (metric == 'poll') {
    
        }
    } catch (error) {
        console.error(error);
    }

}