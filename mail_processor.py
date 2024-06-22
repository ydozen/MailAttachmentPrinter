import imaplib
import email
import os
import json
import time
import threading
import traceback
from email.header import decode_header
from datetime import datetime
import re
import logging

# ログ設定
LOG_FILE = '/var/log/mail_processor.log'
logging.basicConfig(filename=LOG_FILE, level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

# 設定ファイルのパス
CONFIG_FILE = 'mail_config.json'

# 設定読み込み関数
def load_config():
    try:
        with open(CONFIG_FILE, 'r') as file:
            config = json.load(file)
            # アカウント設定のバリデーション
            for account in config['accounts']:
                if not all(key in account for key in ('server', 'email', 'password', 'save_dir')):
                    raise ValueError(f"Account configuration is missing required fields: {account}")
            return config
    except FileNotFoundError:
        logging.error(f"{CONFIG_FILE} not found.")
    except json.JSONDecodeError as e:
        logging.error(f"Error reading {CONFIG_FILE}: {e}")
    except ValueError as e:
        logging.error(f"Invalid configuration: {e}")
    return None

# ファイル名に使用できない文字を置き換える関数
def sanitize_filename(filename):
    return re.sub(r'[\/:*?"<>|]', '_', filename)

# 添付ファイル名をデコードする関数
def decode_filename(filename):
    decoded_parts = decode_header(filename)
    decoded_filename = ''.join(
        part.decode(charset or 'utf-8') if isinstance(part, bytes) else part
        for part, charset in decoded_parts
    )
    return sanitize_filename(decoded_filename)

# メールから添付ファイルを保存する関数
def save_attachments(message, save_dir, email_address):
    for part in message.walk():
        if part.get_content_maintype() == 'multipart' or part.get('Content-Disposition') is None:
            continue

        filename = decode_filename(part.get_filename())
        if filename:
            current_time = datetime.now().strftime('%Y%m%d_%H%M%S')
            new_filename = f"{email_address}_{current_time}_{filename}"
            filepath = os.path.join(save_dir, new_filename)
            if os.path.exists(filepath):
                logging.warning(f"File {new_filename} already exists. Skipping.")
                continue
            try:
                with open(filepath, 'wb') as f:
                    f.write(part.get_payload(decode=True))
                logging.info(f"Saved attachment: {filepath}")
            except IOError as e:
                logging.error(f"Error saving attachment {new_filename}: {e}")

# 添付ファイルを印刷する関数
def print_attachments(save_dir, printer):
    if not printer:
        return

    try:
        for filename in os.listdir(save_dir):
            filepath = os.path.join(save_dir, filename)
            try:
                result = os.system(f"lp -d {printer} {filepath}")
                if result == 0:
                    logging.info(f"Printed: {filepath}")
                else:
                    logging.error(f"Error printing {filepath}. lp command failed.")
            except OSError as e:
                logging.error(f"Error printing file {filename}: {e}")
    except FileNotFoundError as e:
        logging.error(f"Error: {save_dir} not found.")
    except Exception as e:
        logging.error(f"Error printing attachments: {e}")
        traceback.print_exc()

# メールを処理する関数
def process_mailbox(server, email_address, password, save_dir, printer, delete_after_days):
    try:
        # IMAPサーバーに接続
        with imaplib.IMAP4_SSL(server) as mailbox:
            mailbox.login(email_address, password)
            mailbox.select('inbox')

            # メールを検索
            status, messages = mailbox.search(None, 'ALL')
            if status != 'OK':
                logging.error(f"Error fetching emails for {email_address}: {status}")
                return

            message_ids = messages[0].split()

            for message_id in message_ids:
                status, message_data = mailbox.fetch(message_id, '(RFC822)')
                if status != 'OK':
                    logging.error(f"Error fetching mail ID {message_id} for {email_address}: {status}")
                    continue

                for response_part in message_data:
                    if isinstance(response_part, tuple):
                        try:
                            message = email.message_from_bytes(response_part[1])
                            if message.is_multipart():
                                save_attachments(message, save_dir, email_address)
                                print_attachments(save_dir, printer)
                        except Exception as e:
                            logging.error(f"Error processing email ID {message_id}: {e}")
                            traceback.print_exc()

            # 古いメールを削除
            if delete_after_days > 0:
                cutoff = time.time() - (delete_after_days * 86400)
                for message_id in message_ids:
                    status, message_data = mailbox.fetch(message_id, '(RFC822.SIZE DATE)')
                    if status != 'OK':
                        logging.error(f"Error fetching mail ID {message_id} for deletion: {status}")
                        continue

                    try:
                        date_header = email.utils.parsedate_tz(message_data[0][1].decode().split()[-1])
                        if date_header:
                            email_date = time.mktime(email.utils.mktime_tz(date_header))
                            if email_date < cutoff:
                                mailbox.store(message_id, '+FLAGS', '\\Deleted')
                    except Exception as e:
                        logging.error(f"Error checking email date for deletion: {e}")
                        traceback.print_exc()

                mailbox.expunge()

    except imaplib.IMAP4.error as e:
        logging.error(f"IMAP error for {email_address}: {e}")
    except Exception as e:
        logging.error(f"Error processing mail for {email_address}: {e}")
        traceback.print_exc()

# メール受信を定期的に実行するスレッド
def mail_thread(config):
    while True:
        for account in config['accounts']:
            try:
                process_mailbox(
                    account['server'],
                    account['email'],
                    account['password'],
                    account['save_dir'],
                    account.get('printer', ''),
                    config['delete_after_days']
                )
            except Exception as e:
                logging.error(f"Error in processing account {account['email']}: {e}")
                traceback.print_exc()

        time.sleep(config['check_interval'])

# メイン関数
def main():
    logging.info("Program started.")
    config = load_config()
    if not config:
        logging.error("Failed to load config.")
        return

    thread = threading.Thread(target=mail_thread, args=(config,))
    thread.daemon = True
    thread.start()

    logging.info("Email processor thread started.")
    print("Email processor is running. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Program stopped by user.")
        print("Shutting down.")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        traceback.print_exc()

if __name__ == '__main__':
    main()