import discord
import aiohttp
import os
from discord import app_commands
from discord.ext import commands, tasks
from database import init_database, Course, HitListEntry, User
from course import fetch_course_details, CURRENT_SEMESTER

description = """Notification bot to get that GT class that you really want!"""

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

client = discord.Client(description=description, intents=intents)
tree = app_commands.CommandTree(client)


@client.event
async def on_ready():
    print(f"Logged in as {client.user} (ID: {client.user.id})")

    await tree.sync()

    init_database()
    check_courses.start()


@tree.command(name="add-course", description="Add a course to your hit list")
async def add_course(interaction, crn: int):
    async with aiohttp.ClientSession() as session:
        details, _ = await fetch_course_details(crn, session)

    course, created = Course.get_or_create(
        crn=details.crn,
        semester=CURRENT_SEMESTER,
        defaults={
            "name": details.name,
            "subject_code": details.subject_code,
            "course_number": details.course_number,
            "section": details.section,
        },
    )

    user, _ = User.get_or_create(discord_id=interaction.user.id)

    _, created = HitListEntry.get_or_create(user=user, course=course)
    if not created:
        await interaction.response.send_message(
            f"{course.subject_code} {course.course_number}{course.section}: {course.name} is already on your hitlist."
        )
        return

    await interaction.response.send_message(
        f"Added course {course.subject_code} {course.course_number}{course.section}: {course.name} to your hitlist."
    )


@tree.command(
    name="delete-course",
    description="Remove a course from your hit list",
)
async def delete_course(interaction, list_index: int):
    user, _ = User.get_or_create(discord_id=interaction.user.id)

    if list_index <= 0 or list_index > len(user.entries):
        await interaction.response.send_message(
            f"Invalid list index. Try again bozo.",
        )
        return

    entry = user.entries[list_index - 1]
    course = entry.course
    entry.delete_instance()
    await interaction.response.send_message(
        f"Successfully removed {course.subject_code} {course.course_number}{course.section}: {course.name} from your hitlist.",
    )
    return


@tree.command(name="view", description="View your hit list")
async def view_courses(interaction):
    embed = discord.Embed(
        title=f"{interaction.user.global_name}'s Hitlist",
        color=0xFF0000,
        description="Add courses to your hitlist with /add-course",
    )

    user, _ = User.get_or_create(discord_id=interaction.user.id)

    embed_string = ""
    for i, entry in enumerate(user.entries):
        embed_string += f"{i}. {entry.course.subject_code} {entry.course.course_number}{entry.course.section}: {entry.course.name}\n"

    if len(embed_string) == 0:
        embed.add_field(name="Notice", value="You have no courses on your hit list!")
    else:
        embed.add_field(name="Courses", value=embed_string, inline=False)
    embed.set_footer(
        icon_url="https://cdn.discordapp.com/avatars/1238188657748217876/6367cdd82cde0b6c22df0a301308be59?size=256",
        text="Sniper developed by Raymond Bian.",
    )

    await interaction.response.send_message(embed=embed)


@tasks.loop(seconds=5)
async def check_courses():
    courses = Course.select()
    async with aiohttp.ClientSession() as session:
        for course in courses:
            _, seating = await fetch_course_details(course.crn, session)
            if seating[0] - seating[1] > 0:
                await alert_users(course.crn)


async def alert_users(crn: int):
    course = Course.get(semester=CURRENT_SEMESTER, crn=crn)

    for entry in course.desired_by:
        if not entry.notify:
            continue

        user = client.get_user(entry.user.discord_id)

        embed = discord.Embed(
            title=f"Kill Confirmation",
            color=0xFF0000,
            description=f"CRN: {course.crn}",
        )
        embed.add_field(
            name="Course",
            value=f"{course.subject_code} {course.course_number}{course.section}: {course.name}",
            inline=False,
        )
        embed.add_field(
            name="Message",
            value="Your course has been sniped! Register for it here: https://registration.banner.gatech.edu/StudentRegistrationSsb/ssb/term/termSelection?mode=registration",
            inline=False,
        )
        embed.add_field(
            name="Notice",
            value="This course is believed to be dead. If this is not the case, you can re-add it to your hitlist by reacting below.",
            inline=False,
        )
        embed.set_footer(
            icon_url="https://cdn.discordapp.com/avatars/1238188657748217876/6367cdd82cde0b6c22df0a301308be59?size=256",
            text="Sniper developed by Raymond Bian.",
        )

        msg = await user.send(user.mention, embed=embed)
        await msg.add_reaction("❌")
        entry.notify = False
        entry.save()


@client.event
async def on_reaction_add(reaction: discord.Reaction, user):
    message = reaction.message
    if (
        message.author == client.user
        and message.embeds[0].title[:4] == "Kill"
        and reaction.emoji == "❌"
    ):
        db_user = User.get(discord_id=message.content.lstrip("<@").rstrip(">"))
        db_course = Course.get(
            semester=CURRENT_SEMESTER, crn=message.embeds[0].description.split(": ")[1]
        )
        entry = HitListEntry.get(user=db_user, course=db_course)
        entry.notify = True
        entry.save()


client.run(os.environ["gt-sniper-token"])
