import argparse
import csv
import datetime
import json
import sys
from dataclasses import dataclass

from vaccination import Container, VaccinationDay, download_data
from mastodon import Mastodon

STATE = "./vaxbot_state.json"

today = datetime.date.today()
yesterday = today - datetime.timedelta(days=1)


def format_number(number):
    """ Don't mess with locale, just use . as thousands separator """
    return f"{number:,}".replace(",", ".")


def format_percentage(number):
    if number >= 10:
        emoji = "⬆️"
    elif number < 10 and number >= 1:
        emoji = "↗️"
    elif number < 1 and number > -1:
        emoji = "➡️"
    elif number <= -1 and number > -10:
        emoji = "↘️"
    else:
        emoji = "⬇️"
    return f"{number:.2f}% {emoji})"


def generate_toot(container):
    data_yesterday = container[datetime.date.today() - datetime.timedelta(days=1)]
    eight_days_ago = container[datetime.date.today() - datetime.timedelta(days=8)]

    doses_yesterday = data_yesterday.doses_new
    doses_week_before = eight_days_ago.doses_new

    percentage_total = (doses_yesterday / doses_week_before - 1) * 100

    average_yesterday = container.sevenDayAverage()
    average_week_before = container.sevenDayAverage(eight_days_ago.date)
    percentage_average = (average_yesterday / average_week_before - 1) * 100

    message = (
        "Impfungen gestern ({yesterday_date}): {yesterday_doses} ({percentage_total})\n"
        "Impfungen eine Woche zuvor: {last_week_doses}\n\n"
        "7-Tage-Durchschnitt gestern: {average} ({percentage_average})\n"
        "7-Tage-Durchschnitt eine Woche zuvor: {average_last_week}"
    ).format(
        yesterday_date=yesterday.isoformat(),
        yesterday_doses=format_number(doses_yesterday),
        last_week_doses=format_number(doses_week_before),
        average=format_number(int(average_yesterday)),
        average_last_week=format_number(int(average_week_before)),
        percentage_total=format_percentage(percentage_total),
        percentage_average=format_percentage(percentage_average),
    )
    return message


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Toot about the current COVID-19 vaccination status in Germany"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="If given only prints the content of the toot",
    )
    parser.add_argument(
        "access_token", type=str, help="access token for the targeted Mastodon account."
    )

    args = parser.parse_args()

    if not args.dry_run:
        try:
            with open(STATE, "r") as f:
                state = f.read()
            state = json.loads(state)
        except FileNotFoundError:
            state = {"last_toot": yesterday.isoformat()}

        if not state["last_toot"] < today.isoformat():
            print("Already tooted today.")
            sys.exit(0)
        else:
            state["last_toot"] = today.isoformat()

    # Now download and structure the data
    container = Container()

    reader = csv.DictReader(download_data(), delimiter="\t")
    for row in reader:
        container.add(VaccinationDay(row))

    try:
        container[yesterday]
    except KeyError:
        print("Data for yesterday not present.")
        sys.exit(1)

    message = generate_toot(container)
    if args.dry_run:
        print(message)
    else:
        mastodon = Mastodon(
            api_base_url="https://botsin.space", access_token=args.access_token
        )
        mastodon.status_post(message, visibility="unlisted")
        print("{0}: Successfully tooted!".format(datetime.datetime.now().isoformat()))

        # write state
        with open(STATE, "w") as f:
            f.write(json.dumps(state))
