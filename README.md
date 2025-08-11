Music Rating and Recommendation Archival Bot for Discord

1) Scans messages from specified user in channels specified in src/config json files
2) Uses regex/string operations to parse message and retrieve rating/recommendation data from message
3) Stores rating/recommendation data in /db
4) Responds to user queries for ratings/recommendations

Commands (prefix is @[bot-username]):

@bot process - This command tells the bot to loop through historical messages to process entries from when it was not running
@bot ratings - Presents options for querying ratings data
@bot recommendations - Presents options for querying recommendations data