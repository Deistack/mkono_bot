import argparse
import os
from dotenv import load_dotenv
load_dotenv()
import json
from datetime import datetime
from ivas_client import IvasClient


def load_cookies():
    path = os.getenv("IVAS_COOKIES_FILE", "cookies.json")
    if os.path.exists(path):
        return None, path
    return None, None


def build_client():
    cookies_file = os.getenv("IVAS_COOKIES_FILE", "cookies.json")
    c = IvasClient(cookies_file=cookies_file if os.path.exists(cookies_file) else None)
    c.login()
    return c


def cmd_numbers(args):
    c = build_client()
    res = c.check_otps(from_date=args.date or datetime.now().strftime("%d/%m/%Y"))
    if not res:
        print("Failed to fetch data")
        return
    print(f"Total: {res['count_sms']} Paid: {res['paid_sms']} Unpaid: {res['unpaid_sms']} Revenue: {res['revenue']}")
    for d in res.get("sms_details", []):
        print(f"{d['country_number']} count={d['count']} paid={d['paid']} unpaid={d['unpaid']} revenue={d['revenue']}")


def cmd_otps(args):
    c = build_client()
    date = args.date or datetime.now().strftime("%d/%m/%Y")
    data = c.get_all_otps(from_date=date, to_date=args.to_date or "", limit=args.limit)
    for item in data:
        print(f"{item['phone_number']} | {item['range']} | {item['otp_message']}")


def cmd_bot(args):
    import telegram_bot
    telegram_bot.main()


def main():
    parser = argparse.ArgumentParser(description="IVAS custom tool")
    sub = parser.add_subparsers(dest="command")
    p_num = sub.add_parser("numbers", help="List received SMS ranges")
    p_num.add_argument("--date", default=None)
    p_num.set_defaults(func=cmd_numbers)
    p_otp = sub.add_parser("otps", help="Fetch OTP messages")
    p_otp.add_argument("--date", default=None)
    p_otp.add_argument("--to-date", dest="to_date", default=None)
    p_otp.add_argument("--limit", type=int, default=None)
    p_otp.set_defaults(func=cmd_otps)
    p_bot = sub.add_parser("bot", help="Run Telegram bot")
    p_bot.set_defaults(func=cmd_bot)
    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        return
    args.func(args)


if __name__ == "__main__":
    main()
