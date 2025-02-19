const { SlashCommandBuilder, MessageFlags } = require("discord.js");
const VGenerator = require("../../models/VGenerator");
const VPost = require("../../models/VPost");
const { hf_token } = require('../../config.json');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('start_prompter')
        .setDescription('Start running the generator using the flux API endpoint.'),
    async execute(interaction) {
        const generator = await VGenerator.findByPk('default');

        // Exit immediately if the generator is already running
        if (generator.timer_active) {
            interaction.reply({
                content: 'The generator is already active. Stop it with /stop before starting a new one.',
                flags: MessageFlags.Ephemeral
            });
            return;
        }

        const channelId = generator.channel_id;
        const genInterval = generator.properties.gen_interval;

        const channel = interaction.client.channels.cache.get(channelId);

        if (!channel) {
            interaction.reply({
                content: 'Target channel was not found. Make sure a target channel has been set with /setChannel.',
                flags: MessageFlags.Ephemeral
            });
            return;
        }

        // Set timer_active to be running
        const gen = await VGenerator.findByPk('default');

        gen.timer_active = true;

        const prop = gen.properties;
        prop.gen_type = 'prompter';
        gen.properties = prop;
        gen.changed('properties', true);
        
        await gen.save();

        interaction.reply({
            content: `Starting generation at ${genInterval / 1000} second intervals.`,
            flags: MessageFlags.Ephemeral
        });

        // Schedule the image posting
        postImage(channel, genInterval); // Post one image immediately, then start timer
        const timerId = setInterval(async () => {
            // Check if timer is still active and clear it if it is not
            const gen = await VGenerator.findByPk("default");
            if (!gen?.timer_active) {
                clearInterval(timerId);
                return;
            }

            postImage(channel, genInterval);
        }, genInterval);
    }
}

async function postImage(channel, genInterval) {
    // Generate image
    const { Client } = await import('@gradio/client'); // Dynamic import
    const client = await Client.connect('black-forest-labs/FLUX.1-schnell', { hf_token: hf_token });
    const prompt = await getPrompt();

    let imgData = null;
    await client.predict('/infer', {
        prompt: prompt,
        seed: 0,
        randomize_seed: true,
        width: 512,
        height: 512,
        num_inference_steps: 4
    })
    .then(response => {
        imgData = response.data;
        console.log(response.data)
    })
    .catch(err => console.error(err));

    var imgPost = null;
    channel.send({
        files: [imgData[0].url]
    })
    .then(data => {
        imgPost = data;
        VPost.findOrCreate({
            where: {
                message_id: imgPost.id
            },
            defaults: {
                prediction_response: imgData[0],
                prompt: prompt,
                seed: imgData[1]
            }
        });
    })
    .catch(console.error);
}

async function getPrompt() {
    const gen = await VGenerator.findByPk('default');

    let str = "";
    for (let key in gen.prompts) {
        if (gen.prompts.hasOwnProperty(key)) {
            const val = gen.prompts[key].prompt;
            str += `${val}, `;
        }
    }
    str = str.replace(/,\s*$/, '');
    return str;
}