# Copyright (C) 2019 The Raphielscape Company LLC.
#
# Licensed under the Raphielscape Public License, Version 1.c (the "License");
# you may not use this file except in compliance with the License.
#
""" Userbot module for keeping control who PM you. """

from sqlalchemy.exc import IntegrityError
from telethon.tl.functions.contacts import BlockRequest, UnblockRequest
from telethon.tl.functions.messages import ReportSpamRequest
from telethon.tl.types import User

from userbot import ( 
    BOTLOG,
    BOTLOG_CHATID,
    CMD_HELP,
    COUNT_PM,
    LASTMSG,
    LOGS,
    PM_AUTO_BAN,
)
from userbot.events import register

# ========================= CONSTANTS ============================
DEF_UNAPPROVED_MSG = (
    "Hai... Ini adalah pesan balasan otomatis.\n\n"
"=======================================================\n"
    "Maaf, Saya belum menyetujui Anda untuk kirim pesan.\n"
    "Mohon tunggu sampai saya menyetujui pesan Anda.\n"
    "Sampai saat itu, tolong jangan spam pesan ke Saya.\n"
    "Jika Anda tetap melakukannya, Anda akan dilaporkan dan diblokir.\n"
"=======================================================\n\n"
    "Terima kasih.\n"
)
# ================================================================


@register(incoming=True, disable_edited=True, disable_errors=True)
async def permitpm(event):
    """Prohibits people from PMing you without approval. \
        Will block retarded nibbas automatically."""
    if PM_AUTO_BAN:
        self_user = await event.client.get_me()
        if (
            event.is_private
            and event.chat_id != 777000
            and event.chat_id != self_user.id
            and not (await event.get_sender()).bot
        ):
            try:
                from userbot.modules.sql_helper.globals import gvarstatus
                from userbot.modules.sql_helper.pm_permit_sql import is_approved
            except AttributeError:
                return
            apprv = is_approved(event.chat_id)
            notifsoff = gvarstatus("NOTIF_OFF")

            # Use user custom unapproved message
            getmsg = gvarstatus("unapproved_msg")
            if getmsg is not None:
                UNAPPROVED_MSG = getmsg
            else:
                UNAPPROVED_MSG = DEF_UNAPPROVED_MSG

            # This part basically is a sanity check
            # If the message that sent before is Unapproved Message
            # then stop sending it again to prevent FloodHit
            if not apprv and event.text != UNAPPROVED_MSG:
                if event.chat_id in LASTMSG:
                    prevmsg = LASTMSG[event.chat_id]
                    # If the message doesn't same as previous one
                    # Send the Unapproved Message again
                    if event.text != prevmsg:
                        async for message in event.client.iter_messages(
                            event.chat_id, from_user="me", search=UNAPPROVED_MSG
                        ):
                            await message.delete()
                        await event.reply(f"`{UNAPPROVED_MSG}`")
                    LASTMSG.update({event.chat_id: event.text})
                else:
                    await event.reply(f"`{UNAPPROVED_MSG}`")
                    LASTMSG.update({event.chat_id: event.text})
                    
                if notifsoff:
                    await event.client.send_read_acknowledge(event.chat_id)
                if event.chat_id not in COUNT_PM:
                    COUNT_PM.update({event.chat_id: 1})
                else:
                    COUNT_PM[event.chat_id] = COUNT_PM[event.chat_id] + 1

                if COUNT_PM[event.chat_id] > 4:
                    await event.respond(
                        "**Anda mengirim spam pesan ke saya.**\n"
                        "**Anda telah diblokir dan dilaporkan sebagai spam.**\n"
                        "**Selamat tinggal.**"
                    )

                    try:
                        del COUNT_PM[event.chat_id]
                        del LASTMSG[event.chat_id]
                    except KeyError:
                        if BOTLOG:
                        	await event.client.send_message(
                                BOTLOG_CHATID,
                                "Count PM is seemingly going retard, please restart bot!",
                            )
                        return LOGS.info("CountPM went retard")
                        
                    await event.client(BlockRequest(event.chat_id))
                    await event.client(ReportSpamRequest(peer=event.chat_id))
                
                    if BOTLOG:
                        name = await event.client.get_entity(event.chat_id)
                        name0 = str(name.first_name)
                        await event.client.send_message(
                            BOTLOG_CHATID,
                            "["
                            + name0
                            + "](tg://user?id="
                            + str(event.chat_id)
                            + ")"
                            + " was spammed your PM and got blocked",
                        )


@register(disable_edited=True, outgoing=True, disable_errors=True)
async def auto_accept(event):
    """ Will approve automatically if you texted them first. """
    if not PM_AUTO_BAN:
        return
    self_user = await event.client.get_me()
    if (
        event.is_private
        and event.chat_id != 777000
        and event.chat_id != self_user.id
        and not (await event.get_sender()).bot
    ):
        try:
            from userbot.modules.sql_helper.globals import gvarstatus
            from userbot.modules.sql_helper.pm_permit_sql import approve, is_approved
        except AttributeError:
            return

        # Use user custom unapproved message
        get_message = gvarstatus("unapproved_msg")
        if get_message is not None:
            UNAPPROVED_MSG = get_message
        else:
            UNAPPROVED_MSG = DEF_UNAPPROVED_MSG

        chat = await event.get_chat()
        if isinstance(chat, User):
            if is_approved(event.chat_id) or chat.bot:
                return
            async for message in event.client.iter_messages(
                event.chat_id, reverse=True, limit=1
            ):
                if (
                    message.text is not UNAPPROVED_MSG
                    and message.from_id == self_user.id
                ):
                    try:
                        approve(event.chat_id)
                    except IntegrityError:
                        return

                if is_approved(event.chat_id) and BOTLOG:
                    await event.client.send_message(
                        BOTLOG_CHATID,
                        "#AUTO-APPROVED\n"
                        + "User: "
                        + f"[{chat.first_name}](tg://user?id={chat.id})",
                    )


@register(outgoing=True, pattern=r"^\.notifoff$")
async def notifoff(noff_event):
    """ For .notifoff command, stop getting notifications from unapproved PMs. """
    try:
        from userbot.modules.sql_helper.globals import addgvar
    except AttributeError:
        return await noff_event.edit("`Running on Non-SQL mode!`")
    addgvar("NOTIF_OFF", True)
    await noff_event.edit("`Pemberitahuan dari pesan yang belum diizinakn dibisukan!`")


@register(outgoing=True, pattern=r"^\.notifon$")
async def notifon(non_event):
    """ For .notifoff command, get notifications from unapproved PMs. """
    try:
        from userbot.modules.sql_helper.globals import delgvar
    except AttributeError:
        return await non_event.edit("`Running on Non-SQL mode!`")
    delgvar("NOTIF_OFF")
    await non_event.edit("`Pemberitahuan dari pesan yang belum diizinkan dibunyikan!`")


@register(outgoing=True, pattern=r"^\.approve$")
async def approvepm(apprvpm):
    """ For .approve command, give someone the permissions to PM you. """
    try:
        from userbot.modules.sql_helper.globals import gvarstatus
        from userbot.modules.sql_helper.pm_permit_sql import approve
    except AttributeError:
        return await apprvpm.edit("`Running on Non-SQL mode!`")

    if apprvpm.reply_to_msg_id:
        reply = await apprvpm.get_reply_message()
        replied_user = await apprvpm.client.get_entity(reply.from_id)
        aname = replied_user.id
        name0 = str(replied_user.first_name)
        uid = replied_user.id

    else:
        aname = await apprvpm.client.get_entity(apprvpm.chat_id)
        name0 = str(aname.first_name)
        uid = apprvpm.chat_id

    # Get user custom msg
    getmsg = gvarstatus("unapproved_msg")
    if getmsg is not None:
        UNAPPROVED_MSG = getmsg
    else:
        UNAPPROVED_MSG = DEF_UNAPPROVED_MSG

    async for message in apprvpm.client.iter_messages(
        apprvpm.chat_id, from_user="me", search=UNAPPROVED_MSG
    ):
        await message.delete()

    try:
        approve(uid)
    except IntegrityError:
        return await apprvpm.edit(f"[{name0}](tg://user?id={uid}) `mungkin sudah diizinkan.`")

    await apprvpm.edit(f"[{name0}](tg://user?id={uid}) `diizinkan kirim pesan!`")

    if BOTLOG:
        await apprvpm.client.send_message(
            BOTLOG_CHATID,
            "#APPROVED\n" + "User: " + f"[{name0}](tg://user?id={uid})",
        )


@register(outgoing=True, pattern=r"^\.disapprove$")
async def disapprovepm(disapprvpm):
    try:
        from userbot.modules.sql_helper.pm_permit_sql import dissprove
    except BaseException:
        return await disapprvpm.edit("`Running on Non-SQL mode!`")

    if disapprvpm.reply_to_msg_id:
        reply = await disapprvpm.get_reply_message()
        replied_user = await disapprvpm.client.get_entity(reply.from_id)
        aname = replied_user.id
        name0 = str(replied_user.first_name)
        dissprove(replied_user.id)
    else:
        dissprove(disapprvpm.chat_id)
        aname = await disapprvpm.client.get_entity(disapprvpm.chat_id)
        name0 = str(aname.first_name)
        uid = disapprvpm.chat_id

    await disapprvpm.edit(
        f"[{name0}](tg://user?id={disapprvpm.chat_id}) `belum diizinkan kirim pesan!`"
    )

    if BOTLOG:
        await disapprvpm.client.send_message(
            BOTLOG_CHATID,
            "#DISAPPROVED\n" + "User: " + f"[{name0}](tg://user?id={uid})",
        )


@register(outgoing=True, pattern=r"^\.block$")
async def blockpm(block):
    """ For .block command, block people from PMing you! """
    if block.reply_to_msg_id:
        reply = await block.get_reply_message()
        replied_user = await block.client.get_entity(reply.from_id)
        aname = replied_user.id
        name0 = str(replied_user.first_name)
        await block.client(BlockRequest(replied_user.id))
        await block.edit("`Anda telah diblokir!`")
        uid = replied_user.id
    elif block.is_group and not block.reply_to_msg_id:
    	return await block.edit("`Harap balas pengguna yang ingin Anda blokir`")
    else:
        await block.client(BlockRequest(block.chat_id))
        aname = await block.client.get_entity(block.chat_id)
        await block.edit("`Anda telah diblokir!`")
        name0 = str(aname.first_name)
        uid = block.chat_id

    try:
        from userbot.modules.sql_helper.pm_permit_sql import dissprove

        dissprove(uid)
    except AttributeError:
        pass

    if BOTLOG:
        await block.client.send_message(
            BOTLOG_CHATID,
            "#BLOCKED\n" + "User: " + f"[{name0}](tg://user?id={uid})",
        )


@register(outgoing=True, pattern=r"^\.unblock$")
async def unblockpm(unblock):
    """ For .unblock command, let people PMing you again! """
    if unblock.reply_to_msg_id:
        reply = await unblock.get_reply_message()
        replied_user = await unblock.client.get_entity(reply.from_id)
        name0 = str(replied_user.first_name)
        await unblock.client(UnblockRequest(replied_user.id))
        await unblock.edit("`Anda sudah tidak diblokir.`")
        uid = replied_user.id
        if BOTLOG:
            await unblock.client.send_message(
                BOTLOG_CHATID,
                f"#UNBLOCKED\n" + "User: " + f"[{name0}](tg://user?id={uid})",
            )
    elif unblock.is_group and not unblock.reply_to_msg_id:
    	return await unblock.edit("`Harap balas pengguna yang ingin Anda buka blokirnya`")
    else:
    	await unblock.edit(f"[{name0}](tg://user?id={uid}) `sudah tidak diblokir`")


@register(outgoing=True, pattern=r"^\.(set|get|reset) pm_msg(?: |$)(\w*)")
async def add_pmsg(cust_msg):
    """Set your own Unapproved message"""
    if not PM_AUTO_BAN:
        return await cust_msg.edit("Anda harus merubah `PM_AUTO_BAN` menjadi `True`")
    try:
        import userbot.modules.sql_helper.globals as sql
    except AttributeError:
        await cust_msg.edit("`Running on Non-SQL mode!`")
        return

    await cust_msg.edit("Memproses...")
    conf = cust_msg.pattern_match.group(1)

    custom_message = sql.gvarstatus("unapproved_msg")

    if conf.lower() == "set":
        message = await cust_msg.get_reply_message()
        status = "Saved"

        # check and clear user unapproved message first
        if custom_message is not None:
            sql.delgvar("unapproved_msg")
            status = "Updated"

        if message:
            # TODO: allow user to have a custom text formatting
            # eg: bold, underline, striketrough, link
            # for now all text are in monoscape
            msg = message.message  # get the plain text
            sql.addgvar("unapproved_msg", msg)
        else:
            return await cust_msg.edit("`Balas sebuah pesan`")

        await cust_msg.edit("`Pesan disimpan sebagai pesan belum diizinkan.`")

        if BOTLOG:
            await cust_msg.client.send_message(
                BOTLOG_CHATID, f"**{status} Pesan belum diizinkan:** \n\n{msg}"
            )

    if conf.lower() == "reset":
        if custom_message is not None:
            sql.delgvar("unapproved_msg")
            await cust_msg.edit("`Pesan belum diizinkan disetel ulang ke default`")
        else:
            await cust_msg.edit("`Anda belum menyetel pesan khusus`")

    if conf.lower() == "get":
        if custom_message is not None:
            await cust_msg.edit(
                "**Ini adalah pesan Anda yg belum diizinkan:**" f"\n\n{custom_message}"
            )
        else:
            await cust_msg.edit(
                "**Anda belum menyetel pesan yg belum diizinkan**\n"
                f"Menggunakan pesan default: \n\n`{DEF_UNAPPROVED_MSG}`"
            )


CMD_HELP.update(
    {
        "pmpermit": ">`.approve`"
        "\nUntuk: Menyetujui orang yang disebutkan/menjawab pesan."
        "\n\n>`.disapprove`"
        "\nUntuk: Menolak orang yang disebutkan/membalas pesan."
        "\n\n>`.block`"
        "\nUntuk: Blokir orang tersebut."
        "\n\n>`.unblock`"
        "\nUntuk: Batalkan pemblokiran orang tersebut agar mereka dapat kirim pesan kepada Anda."
        "\n\n>`.notifoff`"
        "\nUntuk: Menghapus/Menonaktifkan pemberitahuan apa pun dari PM yang belum disetujui."
        "\n\n>`.notifon`"
        "\nUntuk: Mengizinkan pemberitahuan untuk PM yang belum disetujui."
        "\n\n>`.set pm_msg` <balas pesan>"
        "\nUntuk: Setel pesan Anda yang belum disetujui."
        "\n\n>`.get pm_msg`"
        "\nUntuk: Dapatkan pesan Anda yang belum disetujui saat ini."
        "\n\n>`.reset pm_msg`"
        "\nUntuk: Menyetel ulang pesan yang belum Anda setujui."
        "\n\nPesan kustom yang belum disetujui saat ini tidak dapat disetel"
        "\nteks yang diformat seperti cetak tebal, garis bawah, tautan, dll."
        "\nPesan hanya akan dikirim dalam monospace."
    }
)
