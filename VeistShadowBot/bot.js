const { Events } = require("discord.js");
const twemoji = require('twemoji');
const fetch = require('node-fetch');
const sharp = require('sharp');

module.exports = function run(client) {
    const lastReactions = {};

    client.on(Events.MessageReactionAdd, async (reaction, user) => {
        // We don't want to collect reactions that are made by bots, or are not on messages that aren't sent by the Generator Bot
        if (user.bot || reaction.message.author.id !== "1312889672053035008") return;

        if (reaction.emoji.name == `shadow_${user.username.replace('.', 'dot')}`) {
            // The user has reacted to the post by selecting the reaction created by the shadow
            // TODO: Apply positive feedback to reinforcement learning
        }
        else if (reaction.emoji.name.startsWith('shadow')) {
            // The user has reacted to a shadow reaction that does not reference themself
            await reaction.users.remove(user);
        }
        else {
            // Update the list of reactions
            lastReactions[user.id] = reaction.emoji.name;
            // TODO: Apply negative feedback to reinforcement learning
        }


        // Check if the message has a shadow reaction for the user, and 
    });

    client.on(Events.MessageCreate, async message => {
        if (!message.author.bot || 
            message.author.id !== "1312889672053035008" ||
            !message.content.startsWith('🎨')
        ) return;

        const members = await message.guild.members.fetch({ user: Object.keys(lastReactions) });
        members.forEach(async member => {

            const filter = (reaction, user) => {
                return user.id === member.id;
            }

            const collector = message.createReactionCollector({ filter, time: 10_000 });

            collector.on('collect', (reaction, user) => {
                // User reacted before the timer ended
                collector.stop('reacted');
            });

            collector.on('end', async (collected, reason) => {
                // If the user hasn't reacted before the timer runs out, a shadow reaction will be added.
                if (reason === "time") {
                    const emoji = lastReactions[member.id];

                    try {
                        const response = await fetch(member.displayAvatarURL());
                        const buffer = await response.buffer();
                        const customReactionImg = await overlayImages(buffer, emoji);
            
                        const guildEmojiManager = message.guild.emojis;
                        const guildEmoji = await guildEmojiManager.create({ attachment: customReactionImg, name: `shadow_${member.user.username.replace('.', 'dot')}` })
            
                        await message.react(guildEmoji);

                        await guildEmojiManager.delete(guildEmoji);

                        // DM the user notifying of reaction
                        const dmChannel = await member.createDM();
                        await dmChannel.send(`👤 Shadow Bot reacted with ${emoji} to ${message.url} for you.`)
                        
                    } catch (error) {
                        console.error('❌ Error creating guild emoji:', error);
                    }
                }
            })

            
        })
    })


}

async function createEmojiPNG(emoji) {
    let emojiCode = twemoji.convert.toCodePoint(emoji);

    if (emojiCode.endsWith("-fe0f")) emojiCode = emojiCode.replace("-fe0f", "");

    const emojiUrl = `https://cdn.jsdelivr.net/npm/twemoji@12.0.1/2/svg/${emojiCode}.svg`;

    try {
        const response = await fetch(emojiUrl);
        if (!response.ok) throw new Error(`Failed to fetch emoji SVG for ${emojiCode} (${emoji}): ${response.statusText}`);
        const svgContent = await response.text();

        // Convert SVG to PNG (128x128)
        const pngBuffer = await sharp(Buffer.from(svgContent))
            .resize(64, 64)
            .png()
            .toBuffer()

        return pngBuffer; // Return buffer for further processing
    } catch (error) {
        console.error("❌ Error processing emoji:", error);
    }
}

async function overlayImages(avatarPath, emoji) {
    try {
        // Create a circular mask
        const mask = Buffer.from(
            `<svg width="96" height="96">
                <circle cx="48" cy="48" r="48" fill="white"/>
            </svg>`
        );

        // Load base image
        const avatar = await sharp(avatarPath)
            .resize(96, 96)
            .composite([{ input: mask, blend: 'dest-in' }]) // Apply the mask
            .png() // Ensure output format supports transparency
            .toBuffer()

        // Generate emoji PNG
        const emojiBuffer = await createEmojiPNG(emoji);

        // Overlay emoji onto base image
        return sharp({
            create: {
                width: 128,
                height: 128,
                channels: 4,
                background: { r: 0, g: 0, b: 0, alpha: 0 } // Transparent background
            }
        })
        .composite([
            { input: avatar, top: 5, left: 5 },
            { input: emojiBuffer, top: 59, left: 59 }
        ])
        .webp()
        .toBuffer();
    } catch (error) {
        console.error("❌ Error overlaying images:", error);
    }
}