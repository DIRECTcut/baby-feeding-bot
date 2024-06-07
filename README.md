# Baby Feeding Tracker Bot

This Telegram bot helps parents track their baby's feeding times and types. It logs feedings, provides statistics, and sends reminders if the baby hasn't been fed for a set time period.

## Features

- **Record Feedings**: Log feeding times and types (bottle, left breast, right breast) with a simple interface.
- **View Last Feeding**: Quickly check the last recorded feeding time and type.
- **24-Hour Statistics**: Get a summary of all feedings in the last 24 hours, including intervals between feedings.
- **Notifications**: Receive alerts if the baby hasn't been fed within a specified interval.

## Usage

1. **Start the Bot**: Use the `/start` command to initiate the bot.
2. **Log a Feeding**: Select "Записать кормление" to record a new feeding.
3. **Check Last Feeding**: Select "Проверить последнее кормление" to view the last feeding log.
4. **View 24-Hour Stats**: Select "Статистика за последние 24 часа" to see feedings in the last 24 hours.

## Install and run

1. Clone the repository:
    ```sh
    git clone https://github.com/DIRECTcuts/baby-feeding-bot.git
    cd baby-feeding-bot
    ```
2. Create a new bot in Telegram, or reuse an existing one
3. Configure environment variables in `env.py`

### Production

```sh
docker compose up -d
```

### Development

1. Install dependencies:
    ```sh
    make venv
    ```
2. Run bot
    ```sh
    make run
    ```
    Or use vscode launch configs (see .vscode/launch.json)

**Before** installing new packages:

```sh
source venv/bin/activate
```

**After** installing new packages:

```sh
pip freeze > requirements.txt
```

## Environment Variables

- `TELEGRAM_TOKEN`: Your Telegram bot token.
- `TELEGRAM_USERNAME_WHITELIST`: List of authorized usernames.
- `NOTIFICATION_JOB_QUEUE_INTERVAL_SECONDS`: Interval for notification checks.
- `NOTIFICATION_JOB_QUEUE_FIRST_SECONDS`: Initial delay for notification checks.
- `NOTIFY_IF_UNFED_FOR_SECONDS`: Time threshold for feeding notifications.

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request.

### Planned features
- i18n
- groups: create, join, invite
- more in-depth stats
- delete, edit feeding entries
- pause alerts
- timezones support (currently the app works only for the Buenos Aires timezone)
## License

This project is licensed under the MIT License.
