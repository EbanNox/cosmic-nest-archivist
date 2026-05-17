import discord
from discord.ext import commands
import os
import json
import traceback
import shutil
import asyncio
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

token = os.getenv('TOKEN')

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

ver = "1.1a"

def log_archive_error(error_file, message, error, error_area):
    log_text = (
        "\n"
        "================ ARCHIVE ERROR ================\n"
        f"area: {error_area}\n"
        f"message_id: {message.id}\n"
        f"message_url: {message.jump_url}\n"
        f"message_date: {message.created_at}\n"
        f"message_author: {message.author}\n"
        f"error_type: {type(error).__name__}\n"
        f"error_message: {error}\n"
        f"\n"
        f"Full traceback:\n"
        f"{traceback.format_exc()}\n"
        f"================================================\n\n\n\n\n"
    )

    error_file.write(log_text)
    error_file.flush()
    
    print(log_text)

def safe_folder_name(name, max_length=120):
    unsafe_chars = '<>:"/\\|?*'

    if not name:
        name = "file"

    for char in unsafe_chars:
        name = name.replace(char, "-")

    name = name.strip()

    if not name:
        name = "file"

    filename, extension = os.path.splitext(name)
    max_filename_length = max_length - len(extension)
    if len(filename) > max_filename_length:
        filename = filename[:max_filename_length]

    return filename + extension

async def save_attachment_retry(attachment, file_path, retries=3, delay=1):
    for attempt in range(1, retries + 1):
        try:
            await attachment.save(file_path)
            return True, None
        except Exception as error:
            if attempt == retries:
                return False, error
            await asyncio.sleep(delay)
    return False, None

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

    archive_folder_date = os.path.join("..", "archives", current_date)

    archive_folder = os.path.join(archive_folder_date, channel_name)

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
                    "Archive warning - failed to write general message content!\n"
                    f"Message ID: {message.id}.\n"
                    f"Message URL: {message.jump_url}.\n"
                    "Error logged. Librarian continues with archiving!\n"
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
                        "Archive warning - failed to write embeds!\n"
                        f"Message ID: {message.id}\n"
                        f"Message URL: {message.jump_url}\n"
                        "Error logged. Librarian continues with archiving!\n"
                    )
                    continue

            # Save attachments
            for attachment in message.attachments:
                try:
                    # await attachment.save(os.path.join(archive_folder, safe_folder_name(f"{message.id}_{attachment.filename}")))
                    success, error = await save_attachment_retry(
                        attachment=attachment,
                        file_path=os.path.join(archive_folder, safe_folder_name(f"{message.id}_{attachment.filename}")),
                        retries=3,
                        delay=1
                    )
                    if not success:
                        raise error

                except Exception as error:
                    log_archive_error(
                        error_file=error_file,
                        message=message,
                        error=error,
                        error_area=f"saving attachment: {attachment.filename}"
                    )
                    await ctx.send(
                        "Archive warning - failed to save attachment\n"
                        f"Message ID: {message.id}.\n"
                        f"Message URL: {message.jump_url}.\n"
                        f"Attachment: {attachment.filename}.\n"
                        "Error logged. Librarian continues with archiving!\n"
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
        content=(
            "Quiet please... The librarian is collecting memories.\n"
            "Sealing up the archive..."
        )
    )

    FullArchiveState = True
    try:
        shutil.make_archive(
            base_name=archive_folder,
            format="zip",
            root_dir=archive_folder_date,
            base_dir=channel_name
        )
    except Exception as error:
        FullArchiveState = False
        print("Failed to fully create the archive")
        print(traceback.format_exc())
        await ctx.send(
            "Archive warning - the files were saved, but could not be fully archived.\n"
            f"Error: {type(error).__name__}\n"
        )

    await msg_a1.edit(
        content = (
            "Quiet please... The librarian is collecting memories.\n"
            "Done!\n"
        )
    )

    if FullArchiveState:
        await ctx.send(
            "Preservation complete — this section of the nest has been archived!\n"
            "The chapter has been marked, stored, and sealed."
        )
    else:
        await ctx.send(
            "Preservation mostly complete - data has been saved, but wasent able to fully archive.\n"
            "Check the console output for details."
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
        "Contributors: ebannox, derek"
    )
    return

bot.run(token)