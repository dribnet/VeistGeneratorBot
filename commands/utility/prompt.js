const { SlashCommandBuilder, MessageFlags } = require("discord.js");
const VGenerator = require("../../models/VGenerator");

module.exports = {
    data: new SlashCommandBuilder()
        .setName('prompt')
        .setDescription(`Add a prompt to be used for generation. [Only functions for the 'prompter']`)
        .addSubcommand(subcommand =>
            subcommand.setName('add')
                .setDescription(`Add a prompt to be used for generation. [Only functions for the 'prompter']`)
                .addIntegerOption(option =>
                    option.setName('time')
                        .setDescription('Length of time that the prompt should be used (in minutes).')
                        .setRequired(true))
                .addStringOption(option =>
                    option.setName('prompt')
                        .setDescription('The prompt to use.')
                        .setRequired(true))
        )
        .addSubcommand(subcommand =>
            subcommand.setName('list')
                .setDescription('Lists what prompts are active')
        )
        .addSubcommand(subcommand =>
            subcommand.setName('clear')
                .setDescription('Clear all of the active prompts.')
        ),
    async execute(interaction) {
        if (interaction.options.getSubcommand() === 'add') {
            const gen = await VGenerator.findByPk('default');

            // Exit early if the generator is not active
            if (gen.properties.gen_type == 'none') {
                interaction.reply({
                    content: 'The prompt was not added. The generator is not active.',
                    flags: MessageFlags.Ephemeral
                });
                return;
            }

            const userId = interaction.user.id;

            // Exit if the user already has a prompt active
            if (gen.prompts.hasOwnProperty(userId)) {
                const timeLeft = gen.prompts[userId].start_time + gen.prompts[userId].duration - Date.now()

                interaction.reply({
                    content: `You already have a prompt active for ${Math.round(timeLeft / 60)}`,
                    flags: MessageFlags.Ephemeral
                });
                return;
            }

            // Construct prompt data
            const promptData = {
                start_time: Math.floor(Date.now()/1000),
                duration: interaction.options.getInteger('time') * 60,
                prompt: interaction.options.getString('prompt')
            }
            gen.prompts[userId] = promptData;
            gen.changed('prompts', true);
            gen.save();

            const endTime = promptData.start_time + promptData.duration
            interaction.reply({
                content: `:pen: Prompt "${interaction.options.getString('prompt')}" has been added until <t:${endTime}:t>.`
            })

            setTimeout(async () => {
                const gen = await VGenerator.findByPk('default');
                const prompts = gen.prompts;

                // Notify users
                const channel = interaction.client.channels.cache.get(gen.channel_id);
                channel.send(`:pen: Prompt "${prompts[userId].prompt}" has been removed.`);
                // TODO: Maybe this also sends a DM to the user who added the prompt
                // to notify them that they can add a new prompt. Probably opt-in

                // Delete the prompt
                delete gen.prompts[userId];
                gen.changed('prompts', true);
                gen.save();
                
            }, promptData.duration * 1000);
        }
        else if (interaction.options.getSubcommand() === 'list') {
            const gen = await VGenerator.findByPk('default');
            const prompts = gen.prompts;

            if (Object.keys(prompts).length === 0) {
                interaction.reply({
                    content: 'There are no active prompts.',
                    flags: MessageFlags.Ephemeral
                });
                return;
            }

            let str = "";
            for (let key in prompts) {
                if (prompts.hasOwnProperty(key)) {
                    const val = prompts[key];
                    str += `- "${val.prompt}" ending <t:${val.start_time + val.duration}:R>\n`;
                }
            }

            interaction.reply({
                content: `The following prompts are active:\n` + str,
                flags: MessageFlags.Ephemeral
            })
        }
        else if (interaction.options.getSubcommand() === 'clear') {
            const gen = await VGenerator.findByPk('default');

            gen.prompts = {};
            gen.changed('prompts', true);
            gen.save();

            interaction.reply({
                content: 'Prompts cleared.',
                flags: MessageFlags.Ephemeral
            });
        }
    }
}