import smtplib, imaplib, email, random, time, threading, pandas as pd, os
from email.mime.text import MIMEText
from datetime import datetime
import schedule

EMAIL_LIST_FILE = "email_accounts.csv"
MAX_WARMUPS_PER_DAY = 10

email_accounts = []

def load_accounts():
    global email_accounts
    if not os.path.exists(EMAIL_LIST_FILE):
        return
    df = pd.read_csv(EMAIL_LIST_FILE)
    email_accounts.clear()
    for _, row in df.iterrows():
        acc = {
            "email": row["email"],
            "password": row["password"],
            "smtp": row["smtp"],
            "smtp_port": int(row["smtp_port"]),
            "imap": row["imap"],
            "imap_port": int(row["imap_port"])
        }
        email_accounts.append(acc)

def send_email(sender, recipient, subject, body, smtp_server, smtp_port, password):
    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = recipient
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, [recipient], msg.as_string())
        server.quit()
        print(f"[{datetime.now()}] Sent: {sender} → {recipient}")
    except Exception as e:
        print(f"[ERROR] Sending failed for {sender}: {e}")

def reply_to_emails(account):
    try:
        mail = imaplib.IMAP4_SSL(account["imap"], account["imap_port"])
        mail.login(account["email"], account["password"])
        mail.select("inbox")
        typ, data = mail.search(None, "UNSEEN")
        for num in data[0].split():
            typ, msg_data = mail.fetch(num, "(RFC822)")
            msg = email.message_from_bytes(msg_data[0][1])
            sender = email.utils.parseaddr(msg["From"])[1]
            subject = msg["Subject"]
            reply = f"Hi, this is an automated warm-up reply."
            send_email(account["email"], sender, f"Re: {subject}", reply,
                       account["smtp"], account["smtp_port"], account["password"])
        mail.logout()
    except Exception as e:
        print(f"[ERROR] Reply failed for {account['email']}: {e}")

def get_daily_limit(email):
    start_day = hash(email) % 5
    days_running = (datetime.now() - datetime(2025, 5, 20)).days - start_day
    return min(MAX_WARMUPS_PER_DAY, max(1, days_running + 1))

def warmup_cycle():
    load_accounts()
    for acc in email_accounts:
        other_emails = [e["email"] for e in email_accounts if e["email"] != acc["email"]]
        daily_limit = get_daily_limit(acc["email"])
        targets = random.sample(other_emails, min(len(other_emails), daily_limit))
        for target in targets:
            subject = f"Warmup: Hello from {acc['email']}"
            body = "This is an auto warm-up test email. Please ignore."
            send_email(acc["email"], target, subject, body, acc["smtp"], acc["smtp_port"], acc["password"])
        reply_to_emails(acc)

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(60)

def monitor_file_changes():
    last_mtime = 0
    while True:
        try:
            mtime = os.path.getmtime(EMAIL_LIST_FILE)
            if mtime != last_mtime:
                load_accounts()
                print(f"[{datetime.now()}] Reloaded email list.")
                last_mtime = mtime
        except:
            pass
        time.sleep(15)

def random_scheduler():
    interval = random.randint(30, 90)  # Every 30 to 90 minutes
    schedule.every(interval).minutes.do(warmup_cycle)
    print(f"[{datetime.now()}] Scheduler set: Every {interval} minutes")

if __name__ == "__main__":
    print("Warmup tool started.")
    load_accounts()
    random_scheduler()
    threading.Thread(target=run_scheduler).start()
    threading.Thread(target=monitor_file_changes).start()