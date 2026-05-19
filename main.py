import discord
import os
import json
import traceback
import shutil
import asyncio
import html
import secrets
from discord.ext import commands
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

token = os.getenv('TOKEN')

intents = discord.Intents.default()
intents.message_content = True
client = commands.Bot(command_prefix="!", intents=intents)
client.remove_command('help')

ver = "1.2a"

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

def is_development_version(version):
    return bool(version) and version[-1].isalpha()

def make_archive_run_name():
    timestamp = datetime.now().strftime("%H-%M-%S")
    random_hash = secrets.token_hex(3)
    return f"run-{timestamp}-{random_hash}"

def get_channel_category_name(channel):
    category = getattr(channel, "category", None)
    parent = getattr(channel, "parent", None)

    if category:
        return category.name

    if parent:
        parent_category = getattr(parent, "category", None)

        if parent_category:
            return parent_category.name

    return None

def generate_transcript(ctx, messages, archive_folder, attachment_data, mode, archive_version):
    if mode not in ("online", "offline"):
        raise ValueError("mode must be either 'online' or 'offline'")

    transcript_filename = f"transcript_{mode}.html"
    transcript_path = os.path.join(archive_folder, transcript_filename)

    guild_name = escape_html(ctx.guild.name if ctx.guild else "Unknown Server")
    channel_name = escape_html(ctx.channel.name)
    archived_at = escape_html(datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"))
    message_count = len(messages)
    archive_version_label = escape_html(f"v{archive_version}")

    raw_category = getattr(ctx.channel, "category", None)

    if raw_category is None and getattr(ctx.channel, "parent", None):
        raw_category = getattr(ctx.channel.parent, "category", None)

    category_name = escape_html(raw_category.name) if raw_category else ""

    category_badge_html = ""
    if category_name:
        category_badge_html = f'<div class="cn-badge"><strong>Category:</strong> {category_name}</div>'

    if ctx.guild and ctx.guild.icon:
        guild_icon_html = f'<img class="cn-server-icon" src="{escape_html(ctx.guild.icon.url)}" alt="{guild_name}">'
    else:
        guild_icon_html = '<div class="cn-server-icon cn-server-icon-fallback">✦</div>'

    messages_html = ""
    for message in messages:
        messages_html += render_message_html(
            message=message,
            attachment_data=attachment_data,
            mode=mode
        )

    mode_label = "Online / Discord CDN" if mode == "online" else "Offline / Local"

    html_output = f"""<!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{guild_name} - #{channel_name} Archive Transcript</title>

        <style>
            :root {{
                --bg-main: #050713;
                --bg-panel: rgba(12, 18, 38, 0.82);
                --bg-card: rgba(17, 25, 52, 0.78);
                --bg-card-hover: rgba(25, 38, 79, 0.82);
                --border-soft: rgba(118, 226, 255, 0.18);
                --border-glow: rgba(207, 75, 255, 0.38);
                --text-main: #eef7ff;
                --text-muted: #aab6d3;
                --text-soft: #7e8aac;
                --cyan: #6ee7ff;
                --blue: #5f8cff;
                --purple: #a855f7;
                --magenta: #ff4fd8;
                --gold: #fff2a8;
                --danger: #ff6b8a;
            }}

            * {{
                box-sizing: border-box;
            }}

            body {{
                margin: 0;
                min-height: 100vh;
                color: var(--text-main);
                font-family: Inter, "Segoe UI", Arial, sans-serif;
                background:
                    radial-gradient(circle at 20% 0%, rgba(111, 231, 255, 0.16), transparent 30%),
                    radial-gradient(circle at 80% 10%, rgba(255, 79, 216, 0.18), transparent 28%),
                    radial-gradient(circle at 50% 100%, rgba(95, 140, 255, 0.12), transparent 35%),
                    linear-gradient(135deg, #050713 0%, #0b1028 48%, #190022 100%);
                background-attachment: fixed;
            }}

            body::before {{
                content: "";
                position: fixed;
                inset: 0;
                pointer-events: none;
                opacity: 0.28;
                background-image:
                    radial-gradient(circle, rgba(255,255,255,0.8) 1px, transparent 1.5px),
                    radial-gradient(circle, rgba(110,231,255,0.7) 1px, transparent 1.5px);
                background-size: 90px 90px, 140px 140px;
                background-position: 0 0, 30px 50px;
            }}

            a {{
                color: var(--cyan);
                text-decoration: none;
            }}

            a:hover {{
                text-decoration: underline;
            }}

            .cn-page {{
                position: relative;
                width: min(1180px, calc(100% - 32px));
                margin: 0 auto;
                padding: 32px 0 56px;
            }}

            .cn-hero {{
                position: relative;
                overflow: hidden;
                border: 1px solid var(--border-soft);
                border-radius: 28px;
                padding: 28px;
                margin-bottom: 22px;
                background:
                    linear-gradient(135deg, rgba(12, 18, 38, 0.94), rgba(31, 11, 51, 0.86)),
                    radial-gradient(circle at top right, rgba(255, 79, 216, 0.22), transparent 40%);
                box-shadow:
                    0 0 40px rgba(95, 140, 255, 0.16),
                    inset 0 0 40px rgba(110, 231, 255, 0.04);
            }}

            .cn-hero::after {{
                content: "";
                position: absolute;
                inset: auto -20% -80% -20%;
                height: 160px;
                background: radial-gradient(ellipse, rgba(110, 231, 255, 0.22), transparent 65%);
            }}

            .cn-hero-top {{
                position: relative;
                display: flex;
                flex-direction: column;
                gap: 14px;
                align-items: center;
                justify-content: center;
                text-align: center;
                z-index: 1;
            }}

            .cn-server-icon {{
                width: 76px;
                height: 76px;
                border-radius: 22px;
                object-fit: cover;
                border: 1px solid rgba(255,255,255,0.18);
                box-shadow: 0 0 22px rgba(110, 231, 255, 0.3);
            }}

            .cn-server-icon-fallback {{
                display: grid;
                place-items: center;
                font-size: 42px;
                background: linear-gradient(135deg, var(--cyan), var(--purple));
            }}

            .cn-title-block h1 {{
                margin: 0;
                font-size: clamp(32px, 4.5vw, 56px);
                letter-spacing: 0.03em;
                text-align: center;
            }}

            .cn-title-block p {{
                margin: 8px 0 0;
                color: var(--text-muted);
            }}

            .cn-badges {{
                position: relative;
                display: flex;
                flex-wrap: wrap;
                justify-content: center;
                gap: 10px;
                margin-top: 20px;
                z-index: 1;
            }}

            .cn-badge {{
                padding: 8px 12px;
                border: 1px solid var(--border-soft);
                border-radius: 999px;
                background: rgba(255,255,255,0.055);
                color: var(--text-muted);
                font-size: 14px;
            }}

            .cn-badge strong {{
                color: var(--text-main);
                font-weight: 650;
            }}

            .cn-mode {{
                border-color: rgba(255, 79, 216, 0.38);
                color: #ffd7fb;
            }}

            .cn-chatlog {{
                border: 1px solid var(--border-soft);
                border-radius: 24px;
                overflow: hidden;
                background: rgba(5, 7, 19, 0.45);
                backdrop-filter: blur(14px);
            }}

            .cn-message {{
                display: grid;
                grid-template-columns: 48px minmax(0, 1fr);
                gap: 14px;
                padding: 18px 20px;
                border-bottom: 1px solid rgba(255,255,255,0.065);
                background: rgba(11, 16, 40, 0.45);
                transition: background 0.2s ease, box-shadow 0.2s ease;
            }}

            .cn-message:hover {{
                background: var(--bg-card-hover);
                box-shadow: inset 3px 0 0 rgba(110, 231, 255, 0.6);
            }}

            .cn-avatar {{
                width: 44px;
                height: 44px;
                border-radius: 50%;
                object-fit: cover;
                border: 1px solid rgba(255,255,255,0.14);
                box-shadow: 0 0 16px rgba(168, 85, 247, 0.26);
            }}

            .cn-message-header {{
                display: flex;
                align-items: baseline;
                flex-wrap: wrap;
                gap: 8px;
                margin-bottom: 5px;
            }}

            .cn-author {{
                color: var(--text-main);
                font-weight: 700;
            }}

            .cn-username,
            .cn-timestamp,
            .cn-edited {{
                color: var(--text-soft);
                font-size: 13px;
            }}

            .cn-bot-tag {{
                padding: 2px 5px;
                border-radius: 5px;
                color: white;
                background: linear-gradient(135deg, var(--blue), var(--purple));
                font-size: 11px;
                font-weight: 800;
            }}

            .cn-jump {{
                margin-left: auto;
                font-size: 13px;
                color: var(--cyan);
            }}

            .cn-message-content {{
                line-height: 1.45;
                white-space: normal;
                overflow-wrap: anywhere;
            }}

            .cn-attachments,
            .cn-embeds {{
                margin-top: 8px;
            }}

            .cn-attachment {{
                display: inline-block;
                max-width: min(520px, 100%);
                margin: 8px 8px 0 0;
                border: 1px solid rgba(110, 231, 255, 0.18);
                border-radius: 14px;
                overflow: hidden;
                background: rgba(255,255,255,0.045);
            }}

            .cn-attachment-image {{
                display: block;
                max-width: 520px;
                max-height: 420px;
                width: auto;
                height: auto;
            }}

            .cn-attachment-file {{
                display: flex;
                align-items: center;
                gap: 10px;
                padding: 12px;
            }}

            .cn-file-icon {{
                font-size: 24px;
            }}

            .cn-attachment-meta {{
                padding: 9px 11px;
                color: var(--text-muted);
                font-size: 13px;
            }}

            .cn-attachment-meta span {{
                display: block;
                margin-top: 3px;
                color: var(--text-soft);
            }}

            .cn-embed {{
                display: flex;
                max-width: 560px;
                margin-top: 10px;
                border-radius: 14px;
                overflow: hidden;
                background: rgba(0,0,0,0.22);
                border: 1px solid rgba(255,255,255,0.09);
            }}

            .cn-embed-pill {{
                width: 5px;
                flex: 0 0 5px;
            }}

            .cn-embed-body {{
                padding: 12px;
                width: 100%;
            }}

            .cn-embed-main {{
                display: flex;
                gap: 14px;
            }}

            .cn-embed-text {{
                flex: 1;
                min-width: 0;
            }}

            .cn-embed-author {{
                display: flex;
                align-items: center;
                gap: 7px;
                margin-bottom: 8px;
                font-size: 13px;
                font-weight: 700;
            }}

            .cn-embed-author-icon,
            .cn-embed-footer-icon {{
                width: 20px;
                height: 20px;
                border-radius: 50%;
            }}

            .cn-embed-title {{
                display: block;
                margin-bottom: 7px;
                font-weight: 750;
            }}

            .cn-embed-description {{
                color: var(--text-muted);
                font-size: 14px;
                line-height: 1.42;
            }}

            .cn-embed-fields {{
                display: flex;
                flex-wrap: wrap;
                gap: 10px;
                margin-top: 10px;
            }}

            .cn-embed-field {{
                min-width: 100%;
            }}

            .cn-embed-field-inline {{
                min-width: 160px;
                flex: 1;
            }}

            .cn-embed-field-name {{
                font-size: 13px;
                font-weight: 800;
                color: var(--text-main);
            }}

            .cn-embed-field-value {{
                margin-top: 3px;
                color: var(--text-muted);
                font-size: 13px;
            }}

            .cn-embed-thumbnail {{
                width: 80px;
                height: 80px;
                object-fit: cover;
                border-radius: 10px;
            }}

            .cn-embed-image {{
                max-width: 100%;
                max-height: 380px;
                border-radius: 12px;
                margin-top: 10px;
            }}

            .cn-embed-footer {{
                display: flex;
                align-items: center;
                gap: 6px;
                margin-top: 10px;
                color: var(--text-soft);
                font-size: 12px;
            }}

            .cn-postamble {{
                margin-top: 18px;
                color: var(--text-soft);
                text-align: center;
                font-size: 13px;
            }}

            @media (max-width: 720px) {{
                .cn-page {{
                    width: min(100% - 16px, 1180px);
                    padding-top: 12px;
                }}

                .cn-hero {{
                    padding: 20px;
                    border-radius: 20px;
                }}

                .cn-message {{
                    grid-template-columns: 40px minmax(0, 1fr);
                    gap: 10px;
                    padding: 15px 12px;
                }}

                .cn-avatar {{
                    width: 38px;
                    height: 38px;
                }}

                .cn-jump {{
                    margin-left: 0;
                }}
            }}
        </style>
    </head>

    <body>
        <main class="cn-page">
            <header class="cn-hero">
                <div class="cn-hero-top">
                    {guild_icon_html}
                    <div class="cn-title-block">
                        <h1>Cosmic Nest Archives</h1>
                        <p>Archive Transcript</p>
                    </div>
                </div>

                <div class="cn-badges">
                    {category_badge_html}
                    <div class="cn-badge"><strong>Channel:</strong> #{channel_name}</div>
                    <div class="cn-badge"><strong>Messages:</strong> {message_count}</div>
                    <div class="cn-badge"><strong>Version:</strong> {archive_version_label}</div>
                    <div class="cn-badge"><strong>Archived:</strong> {archived_at}</div>
                    <div class="cn-badge cn-mode"><strong>Mode:</strong> {mode_label}</div>
                </div>
            </header>

            <section class="cn-chatlog">
                {messages_html}
            </section>

            <footer class="cn-postamble">
                Generated by Cosmic Nest Archivist. This transcript is a preserved archive view.
            </footer>
        </main>
    </body>
    </html>
    """

    with open(transcript_path, "w", encoding="utf-8") as transcript_file:
        transcript_file.write(html_output)

    return transcript_path

def format_file_size(size_bytes):
    if size_bytes is None:
        return "unknown size"

    size = float(size_bytes)

    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024

    return f"{size:.1f} TB"

def format_timestamp(timestamp):
    return timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")

def escape_html(value):
    if value is None:
        return ""

    return html.escape(str(value), quote=True)

def message_content_to_html(content):
    escaped_content = escape_html(content)

    # preserve discord-style line breaks
    return escaped_content.replace("\n", "<br>")

def is_image_attachment(attachment):
    if attachment.content_type:
        return attachment.content_type.startswith("image/")

    image_extensions = [".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"]
    return attachment.filename.lower().endswith(tuple(image_extensions))

def render_attachment_html(attachment, saved_attachment_data, mode):
    filename = escape_html(attachment.filename)
    file_size = format_file_size(getattr(attachment, "size", None))

    if mode == "offline" and saved_attachment_data:
        attachment_href = escape_html(saved_attachment_data["local_name"])
    else:
        attachment_href = escape_html(attachment.url)

    if is_image_attachment(attachment):
        return f"""
        <div class="cn-attachment">
            <a href="{attachment_href}" target="_blank" rel="noopener noreferrer">
                <img class="cn-attachment-image" src="{attachment_href}" alt="{filename}">
            </a>
            <div class="cn-attachment-meta">
                <a href="{attachment_href}" target="_blank" rel="noopener noreferrer">{filename}</a>
                <span>{file_size}</span>
            </div>
        </div>
        """

    return f"""
    <div class="cn-attachment cn-attachment-file">
        <div class="cn-file-icon">📎</div>
        <div class="cn-attachment-meta">
            <a href="{attachment_href}" target="_blank" rel="noopener noreferrer">{filename}</a>
            <span>{file_size}</span>
        </div>
    </div>
    """

def render_embed_html(embed):
    embed_data = embed.to_dict()

    color_value = embed_data.get("color")
    if isinstance(color_value, int):
        embed_color = f"#{color_value:06x}"
    else:
        embed_color = "#6ee7ff"

    title = embed_data.get("title")
    url = embed_data.get("url")
    description = embed_data.get("description")
    fields = embed_data.get("fields", [])
    footer = embed_data.get("footer", {})
    author = embed_data.get("author", {})
    thumbnail = embed_data.get("thumbnail", {})
    image = embed_data.get("image", {})

    title_html = ""
    if title:
        safe_title = escape_html(title)

        if url:
            title_html = f'<a class="cn-embed-title" href="{escape_html(url)}" target="_blank" rel="noopener noreferrer">{safe_title}</a>'
        else:
            title_html = f'<div class="cn-embed-title">{safe_title}</div>'

    author_html = ""
    if author.get("name"):
        author_icon = ""
        if author.get("icon_url"):
            author_icon = f'<img class="cn-embed-author-icon" src="{escape_html(author.get("icon_url"))}" alt="">'

        author_html = f"""
        <div class="cn-embed-author">
            {author_icon}
            <span>{escape_html(author.get("name"))}</span>
        </div>
        """

    description_html = ""
    if description:
        description_html = f'<div class="cn-embed-description">{message_content_to_html(description)}</div>'

    fields_html = ""
    for field in fields:
        inline_class = " cn-embed-field-inline" if field.get("inline") else ""
        fields_html += f"""
        <div class="cn-embed-field{inline_class}">
            <div class="cn-embed-field-name">{escape_html(field.get("name"))}</div>
            <div class="cn-embed-field-value">{message_content_to_html(field.get("value"))}</div>
        </div>
        """

    thumbnail_html = ""
    if thumbnail.get("url"):
        thumbnail_html = f"""
        <img class="cn-embed-thumbnail" src="{escape_html(thumbnail.get("url"))}" alt="">
        """

    image_html = ""
    if image.get("url"):
        image_html = f"""
        <div class="cn-embed-image-wrap">
            <img class="cn-embed-image" src="{escape_html(image.get("url"))}" alt="">
        </div>
        """

    footer_html = ""
    if footer.get("text"):
        footer_icon = ""
        if footer.get("icon_url"):
            footer_icon = f'<img class="cn-embed-footer-icon" src="{escape_html(footer.get("icon_url"))}" alt="">'

        footer_html = f"""
        <div class="cn-embed-footer">
            {footer_icon}
            <span>{escape_html(footer.get("text"))}</span>
        </div>
        """

    return f"""
    <div class="cn-embed">
        <div class="cn-embed-pill" style="background: {embed_color};"></div>
        <div class="cn-embed-body">
            <div class="cn-embed-main">
                <div class="cn-embed-text">
                    {author_html}
                    {title_html}
                    {description_html}
                    <div class="cn-embed-fields">
                        {fields_html}
                    </div>
                </div>
                {thumbnail_html}
            </div>
            {image_html}
            {footer_html}
        </div>
    </div>
    """

def render_message_html(message, attachment_data, mode):
    author_name = escape_html(message.author.display_name)
    author_username = escape_html(str(message.author))
    avatar_url = escape_html(message.author.display_avatar.url)
    timestamp = escape_html(format_timestamp(message.created_at))
    jump_url = escape_html(message.jump_url)

    bot_tag = ""
    if message.author.bot:
        bot_tag = '<span class="cn-bot-tag">APP</span>'

    edited_tag = ""
    if message.edited_at:
        edited_tag = f'<span class="cn-edited">(edited {escape_html(format_timestamp(message.edited_at))})</span>'

    content_html = ""
    if message.content:
        content_html = f"""
        <div class="cn-message-content">
            {message_content_to_html(message.content)}
        </div>
        """

    message_saved_attachments = attachment_data.get(message.id, {})

    attachments_html = ""
    for attachment in message.attachments:
        saved_attachment_data = message_saved_attachments.get(attachment.id)
        attachments_html += render_attachment_html(
            attachment=attachment,
            saved_attachment_data=saved_attachment_data,
            mode=mode
        )

    embeds_html = ""
    for embed in message.embeds:
        embeds_html += render_embed_html(embed)

    return f"""
    <article class="cn-message" id="message-{message.id}">
        <div class="cn-avatar-wrap">
            <img class="cn-avatar" src="{avatar_url}" alt="{author_name}">
        </div>

        <div class="cn-message-main">
            <div class="cn-message-header">
                <span class="cn-author">{author_name}</span>
                <span class="cn-username">{author_username}</span>
                {bot_tag}
                <span class="cn-timestamp">{timestamp}</span>
                {edited_tag}
                <a class="cn-jump" href="{jump_url}" target="_blank" rel="noopener noreferrer">Jump</a>
            </div>

            {content_html}

            <div class="cn-attachments">
                {attachments_html}
            </div>

            <div class="cn-embeds">
                {embeds_html}
            </div>
        </div>
    </article>
    """

@client.command()
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
    archive_channel_folder = os.path.join(archive_folder_date, channel_name)
    archive_run_name = None

    if is_development_version(ver):
        archive_run_name = make_archive_run_name()
        archive_folder = os.path.join(archive_channel_folder, archive_run_name)
        archive_root_dir = archive_channel_folder
        archive_base_dir = archive_run_name
    else:
        archive_folder = archive_channel_folder
        archive_root_dir = archive_folder_date
        archive_base_dir = channel_name

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

    attachment_data = {}
    archive_info = {
        "archivist_version": ver,
        "development_version": is_development_version(ver),
        "archive_run_name": archive_run_name,
        "created_at_utc": datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "server_name": ctx.guild.name if ctx.guild else None,
        "server_id": ctx.guild.id if ctx.guild else None,
        "channel_name": ctx.channel.name,
        "channel_id": ctx.channel.id,
        "channel_category": get_channel_category_name(ctx.channel),
        "message_count": archive_totalentries,
        "archive_mode": "development-run-folder" if is_development_version(ver) else "final-version-folder",
    }

    with (
        open(os.path.join(archive_folder, "msg.txt"), 'w', encoding='utf-8') as file1,
        open(os.path.join(archive_folder, "msg_embeds.txt"), 'w', encoding='utf-8') as file2,
        open(os.path.join(archive_folder, "archive_info.json"), "w", encoding='utf-8') as archive_info_file,
        open(os.path.join(archive_folder, "archive_errors.txt"), 'w', encoding='utf-8') as error_file
    ):
        # make the archive info file
        json.dump(archive_info, archive_info_file, ensure_ascii=False, indent=4)

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
                    safe_attachment_name = safe_folder_name(f"{message.id}_{attachment.filename}")
                    # await attachment.save(os.path.join(archive_folder, safe_folder_name(f"{message.id}_{attachment.filename}")))
                    success, error = await save_attachment_retry(
                        attachment=attachment,
                        file_path=os.path.join(archive_folder, safe_attachment_name),
                        retries=3,
                        delay=1
                    )
                    if not success:
                        raise error

                    if message.id not in attachment_data:
                        attachment_data[message.id] = {}
                    attachment_data[message.id][attachment.id] = {
                        "filename": attachment.filename,
                        "local_name": safe_attachment_name,
                        "url": attachment.url,
                        "size": attachment.size,
                        "content_type": attachment.content_type,
                    }

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
        "Generating transcript..."
        )
    )
    
    try:
        generate_transcript(
            ctx=ctx,
            messages=archive_objlist_channeldata,
            archive_folder=archive_folder,
            attachment_data=attachment_data,
            mode="online",
            archive_version=ver
        )
        
        generate_transcript(
            ctx=ctx,
            messages=archive_objlist_channeldata,
            archive_folder=archive_folder,
            attachment_data=attachment_data,
            mode="offline",
            archive_version=ver
        )
    except Exception as error:
        print("Failed to generate transcript")
        print(traceback.format_exc())
        
        await ctx.send(
            "Archive warning - files and data were saved, but failed in generating a transcript.\n"
            f"Error: {type(error).__name__}"
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
            root_dir=archive_root_dir,
            base_dir=archive_base_dir
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
            "Preservation mostly complete - data has been saved, but wasn’t able to fully archive.\n"
            "Check the console output for details."
        )

    return

@client.command()
async def version(ctx):
    await ctx.send(
        f"Cosmic Nest Archive Librarian v{ver}"
    )
    return

@client.command()
async def contributors(ctx):
    await ctx.send(
        "Contributors: ebannox, derek"
    )
    return

@client.command()
async def baran(ctx):
    await ctx.send(
        "Baran!!!\n"
    )
    await ctx.send(
        ":moyai:"
    )

client.run(token)