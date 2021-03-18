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


def generate_toot(container):
    data_yesterday = container[datetime.date.today() - datetime.timedelta(days=1)]
    eight_days_ago = container[datetime.date.today() - datetime.timedelta(days=8)]

    message = (
        f"Impfungen gestern ({yesterday.isoformat()}): {format_number(data_yesterday.doses_new)}\n"
        f"Impfungen eine Woche zuvor: {format_number(eight_days_ago.doses_new)}\n\n"
        f"7-Tage-Durchschnitt gestern: {format_number(int(container.sevenDayAverage()))}\n"
        f"7-Tage-Durchschnitt eine Woche zuvor: {format_number(int(container.sevenDayAverage(eight_days_ago.date)))}"
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
