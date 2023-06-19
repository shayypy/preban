# PreBan

Preemptively ban users who are not currently in your server. This feature is known as "hackban" in some Discord bots.

## Commands

### `pb/ban <user id> [reason]`

Preban a user. You must provide the ~8 character user ID ([learn how to copy a user ID](https://support.guilded.gg/hc/en-us/articles/6183962129303)). You may optionally provide a reason, which will show up in the audit log when the user gets banned.

Once a ban is fulfilled (a prebanned user joins the server), the user **will not** be banned a second time if the ban is manually lifted by a server moderator. Use `pb/ban` again to reactivate a preban.

### `pb/unban <user id>`

Remove a preban. This will also unban the user from the server if they are currently banned.

### `pb/bans`

List all prebans for the current server. Active prebans will have an ⏲ icon before them. Fulfilled prebans will use an ✅ icon. Prebans that are inactive but not fulfilled (the ban was deleted by a moderator) will show an ❌ icon.

## Support

https://www.guilded.gg/bearger/groups/3jgxWb7D
