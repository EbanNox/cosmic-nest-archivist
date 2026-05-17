import discord
from discord.ext import commands
import os
import json
import traceback
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

token = os.getenv('TOKEN')

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

ver = "1.0e"

def log_archive_error(error_file, message, error, error_area):
    error_text = traceback.format_exc()
    
    log_text = (
        "\n"
        "================ ARCHIVE ERROR ================\n"
        f"area: {error_area}\n"
        f"message_id: {message.id}\n"
        f"message_date: {message.created_at}\n"
        f"message_author: {message.author}\n"
        f"error_type: {type(error).__name__}\n"
        f"error_message: {error}\n"
        f"\n"
        f"Full traceback:\n"
        f"{error_text}\n"
        f"================================================\n\n"
    )

    error_file.write(log_text)
    error_file.flush()
    
    print(log_text)

def safe_folder_name(name):
    unsafe_chars = '<>:"/\\|?*'

    if not name:
        name = "output"

    for char in unsafe_chars:
        name = name.replace(char, "-")

    name = name.strip()

    if not name:
        name = "output"

    return name

@bot.command()
async def archive(ctx):
    # Check permission
    if not ctx.author.guild_permissions.administrator:
        await ctx.send(
            "The Nest cannot begin preservation without administrator clearance.\n"
            "Archive request denied — admin access is required."
        )
        return

    msg_a1 = await ctx.send(
        "Quiet please... The librarian is preparing to collect memories.\n"
        "Loading..."
    )
    
    channel_name = safe_folder_name(ctx.channel.name)

    current_date = datetime.now().strftime("%Y-%m-%d")

    archive_folder = os.path.join("..", "archives", current_date, channel_name)

    # Create output directory if it doesn't exist
    os.makedirs(archive_folder, exist_ok=True)

    # Load all channel history data
    archive_objlist_channeldata = [
        a async for a in ctx.channel.history(limit=None, oldest_first=True)
        if a.id not in (ctx.message.id, msg_a1.id)
    ]

    # Get a sum of total value of enteries loaded
    archive_totalentries = len(archive_objlist_channeldata)
    
    if archive_totalentries == 0:
        await msg_a1.edit (
            content = (
                "Quiet please... The librarian is collecting memories.\n"
                "Nothing to archive..."
            )
        )
        return

    with (
        open(os.path.join(archive_folder, "msg.txt"), 'w', encoding='utf-8') as file1,
        open(os.path.join(archive_folder, "msg_embeds.txt"), 'w', encoding='utf-8') as file2,
        open(os.path.join(archive_folder, "archive_errors.txt"), 'w', encoding='utf-8') as error_file
    ):
        # Fetch all messages loaded in archive_objlist_channeldata
        for current_entry, message in enumerate(archive_objlist_channeldata, start=1):

            # Writing basic message content, such as: author, timestamp and basic message
            try:
                file1.write(
                    f"[id:{message.id}]-[date:{message.created_at}]-[{message.author}]: {message.content}\n"
                )
            except Exception as error:
                log_archive_error(
                    error_file=error_file,
                    message=message,
                    error=error,
                    error_area="writing basic message content"
                )
                await ctx.send(
                    f"Archive warning - failed to write general message content from ID: {message.id}.\n"
                    "Error logged. Librarian continues with archiving!"
                )
                continue

            # Writing embeds in JSON format
            for embed in message.embeds:
                try:
                    file2.write(
                        f"[id:{message.id}]-[{message.created_at}]-[{message.author}]:\n"
                        + json.dumps(embed.to_dict(), ensure_ascii=False, indent=4)
                        + "\n\n\n"
                    )

                except Exception as error:
                    log_archive_error(
                        error_file=error_file,
                        message=message,
                        error=error,
                        error_area="writing embeds"
                    )
                    await ctx.send(
                        f"Archive warning - failed to write embeds from ID: {message.id}"
                        "Error logged. Librarian continues with archiving!"
                    )
                    continue

            # Save attachments
            for attachment in message.attachments:
                try:
                    file_path = os.path.join(archive_folder, f"{message.id}_{attachment.filename}")
                    await attachment.save(file_path)

                except Exception as error:
                    log_archive_error(
                        error_file=error_file,
                        message=message,
                        error=error,
                        error_area=f"saving attachment: {attachment.filename}"
                    )
                    await ctx.send(
                        f"Archive warning - failed to save attachment from ID: {message.id}.\n"
                        f"Attachment: {attachment.filename}.\n"
                        "Error logged. Librarian continues with archiving!"
                    )
                    continue

            if current_entry % 25 == 0 or current_entry == archive_totalentries:
                progress = int((current_entry * 100) / archive_totalentries)
                anim_dots = (current_entry // 25) % 3 + 1
                dots = "." * anim_dots
                
                await msg_a1.edit(
                    content = (
                        "Quiet please... The librarian is collecting memories.\n"
                        f"Working{dots} {progress}%"
                    )
                )

    await msg_a1.edit(
        content = (
            "Quiet please... The librarian is collecting memories.\n"
            "Done!"
        )
    )

    await ctx.send(
        "Preservation complete — this archive of the nest has been safely remembered!\n"
        "This chapter has been marked, stored, and settled into the archives."
    )
    return

@bot.command()
async def version(ctx):
    await ctx.send(
        f"Cosmic Nest Archive Librarian v{ver}"
    )
    return

@bot.command()
async def contributors(ctx):
    await ctx.send(
        f"Contributors: ebannox, derek"
    )
    return

bot.run(token)