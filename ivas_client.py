import os
import shutil
import time
from datetime import datetime
from urllib.parse import urlencode
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service

PROFILE_SRC = os.path.expandvars(r"%APPDATA%\Mozilla\Firefox\Profiles\36qopov3.default-release")
GECKO = r"C:\Users\User\ZAP\webdriver\windows\32\geckodriver.exe"
FIREFOX = r"C:\Program Files\Mozilla Firefox\firefox.exe"


def copy_profile(dst):
    if os.path.exists(dst):
        shutil.rmtree(dst, ignore_errors=True)
    os.makedirs(dst, exist_ok=True)
    for root, dirs, files in os.walk(PROFILE_SRC):
        rel = os.path.relpath(root, PROFILE_SRC)
        target_root = os.path.join(dst, rel) if rel != "." else dst
        os.makedirs(target_root, exist_ok=True)
        for f in files:
            if f == "parent.lock":
                continue
            src_file = os.path.join(root, f)
            dst_file = os.path.join(target_root, f)
            try:
                shutil.copy2(src_file, dst_file)
            except Exception:
                pass


class IvasClient:
    def __init__(self, cookies=None, cookies_file=None, user_agent=None):
        self.profile_dir = os.path.join(os.environ.get("TEMP", "C:\\temp"), "opencode", "ivas_profile")
        copy_profile(self.profile_dir)
        opts = Options()
        opts.binary_location = FIREFOX
        opts.add_argument("-profile")
        opts.add_argument(self.profile_dir)
        opts.add_argument("--headless")
        svc = Service(GECKO)
        self.driver = webdriver.Firefox(service=svc, options=opts)
        self.base_url = "https://www.ivasms.com"
        self.csrf_token = None
        self.logged_in = False

    def close(self):
        try:
            self.driver.quit()
        except Exception:
            pass

    def _sync_xhr(self, url, data=None):
        if data is None:
            script = """
            const xhr = new XMLHttpRequest();
            xhr.open('GET', arguments[0], false);
            xhr.send();
            return xhr.responseText;
            """
            return self.driver.execute_script(script, url)
        payload = urlencode(data)
        script = """
        const xhr = new XMLHttpRequest();
        xhr.open('POST', arguments[0], false);
        xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded; charset=UTF-8');
        xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
        xhr.send(arguments[1]);
        return xhr.responseText;
        """
        return self.driver.execute_script(script, url, payload)

    def login(self):
        try:
            self.driver.get(f"{self.base_url}/portal/sms/received")
            time.sleep(3)
            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            token_input = soup.find("input", {"name": "_token"})
            if token_input and token_input.get("value"):
                self.csrf_token = token_input.get("value")
                self.logged_in = True
                return True
            return False
        except Exception:
            return False

    def ensure_login(self):
        if not self.logged_in:
            return self.login()
        return True

    def check_otps(self, from_date="", to_date=""):
        if not self.ensure_login():
            return None
        try:
            text = self._sync_xhr(
                f"{self.base_url}/portal/sms/received/getsms",
                {"from": from_date, "to": to_date, "_token": self.csrf_token},
            )
            soup = BeautifulSoup(text, "html.parser")
            count_sms = soup.select_one("#CountSMS")
            paid_sms = soup.select_one("#PaidSMS")
            unpaid_sms = soup.select_one("#UnpaidSMS")
            revenue_sms = soup.select_one("#RevenueSMS")
            details = []
            for item in soup.select("div.item"):
                country_number = item.select_one(".col-sm-4")
                count = item.select_one(".col-3:nth-child(2) p")
                paid = item.select_one(".col-3:nth-child(3) p")
                unpaid = item.select_one(".col-3:nth-child(4) p")
                revenue = item.select_one(".col-3:nth-child(5) p span.currency_cdr")
                details.append({
                    "country_number": country_number.text.strip() if country_number else "",
                    "count": count.text.strip() if count else "0",
                    "paid": paid.text.strip() if paid else "0",
                    "unpaid": unpaid.text.strip() if unpaid else "0",
                    "revenue": revenue.text.strip() if revenue else "0",
                })
            return {
                "count_sms": count_sms.text.strip() if count_sms else "0",
                "paid_sms": paid_sms.text.strip() if paid_sms else "0",
                "unpaid_sms": unpaid_sms.text.strip() if unpaid_sms else "0",
                "revenue": revenue_sms.text.strip().replace(" USD", "") if revenue_sms else "0",
                "sms_details": details,
            }
        except Exception:
            return None

    def get_number_details(self, phone_range, from_date="", to_date=""):
        if not self.ensure_login():
            return None
        try:
            text = self._sync_xhr(
                f"{self.base_url}/portal/sms/received/getsms/number",
                {"_token": self.csrf_token, "start": from_date, "end": to_date, "range": phone_range},
            )
            soup = BeautifulSoup(text, "html.parser")
            details = []
            for item in soup.select("div.card.card-body"):
                col4 = item.select_one(".col-sm-4")
                phone_number = col4.text.strip() if col4 else ""
                onclick = col4.get("onclick", "") if col4 else ""
                id_number = ""
                if onclick:
                    parts = onclick.split("'")
                    if len(parts) >= 4:
                        id_number = parts[3]
                count = item.select_one(".col-3:nth-child(2) p")
                paid = item.select_one(".col-3:nth-child(3) p")
                unpaid = item.select_one(".col-3:nth-child(4) p")
                revenue = item.select_one(".col-3:nth-child(5) p span.currency_cdr")
                details.append({
                    "phone_number": phone_number,
                    "count": count.text.strip() if count else "0",
                    "paid": paid.text.strip() if paid else "0",
                    "unpaid": unpaid.text.strip() if unpaid else "0",
                    "revenue": revenue.text.strip() if revenue else "0",
                    "id_number": id_number,
                    "range": phone_range,
                })
            return details
        except Exception:
            return None

    def get_otp_message(self, phone_number, phone_range, from_date="", to_date=""):
        if not self.ensure_login():
            return None
        try:
            text = self._sync_xhr(
                f"{self.base_url}/portal/sms/received/getsms/number/sms",
                {"_token": self.csrf_token, "start": from_date, "end": to_date, "Number": phone_number, "Range": phone_range},
            )
            soup = BeautifulSoup(text, "html.parser")
            msg = soup.select_one(".col-9.col-sm-6 p")
            return msg.text.strip() if msg else None
        except Exception:
            return None

    def get_all_otps(self, from_date="", to_date="", limit=None):
        result = self.check_otps(from_date=from_date, to_date=to_date)
        if not result:
            return []
        otps = []
        for detail in result.get("sms_details", []):
            range_name = detail["country_number"]
            numbers = self.get_number_details(range_name, from_date, to_date)
            if not numbers:
                continue
            for num in numbers:
                if limit is not None and len(otps) >= limit:
                    return otps
                msg = self.get_otp_message(num["phone_number"], range_name, from_date, to_date)
                if msg:
                    otps.append({
                        "range": range_name,
                        "phone_number": num["phone_number"],
                        "otp_message": msg,
                    })
        return otps

    def get_live_page(self):
        try:
            self.driver.get(f"{self.base_url}/portal/live")
            time.sleep(2)
            return self.driver.page_source
        except Exception:
            return None
