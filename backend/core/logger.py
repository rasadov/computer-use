from dataclasses import dataclass
import json
import queue
import threading
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import os
from typing import Optional
import logging


@dataclass
class SMTPConfig:
    host: str
    port: int
    user: str
    password: str
    to: str


class JSONLogger:
    LEVELS = {'DEBUG': 10, 'INFO': 20, 'WARNING': 30, 'ERROR': 40, 'CRITICAL': 50}
    
    # Default configuration if the file is missing
    DEFAULT_CONFIG = {
        "version": 1,
        "formatters": {
            "json": {
                "format": "json",
                "fields": ["timestamp", "level", "message", "extras"]
            },
            "simple": {
                "format": "text",
                "template": "{timestamp} [{level}] {message}"
            },
            "email": {
                "format": "text",
                "template": "[{level: <8}] {timestamp} | {message} | {module} | {function} | {lineno}"
            }
        },
        "handlers": {
            "file": {
                "type": "file",
                "filename": "app.log",
                "formatter": "json",
                "level": "DEBUG"
            },
            "console": {
                "type": "stdout",
                "formatter": "simple",
                "level": "ERROR"
            },
            "email": {
                "type": "email",
                "formatter": "email",
                "level": "CRITICAL",
            }
        },
        "loggers": {
            "root": {
                "level": "DEBUG",
                "handlers": ["file", "console", "email"]
            }
        }
    }
    
    def __init__(
        self,
        logger_config_path: str,
        smtp_config: Optional[SMTPConfig] = None,
    ) -> None:
        self.config = self._load_config(logger_config_path)
        self.SMTP_CONFIG = smtp_config
        self.q = queue.Queue()
        self.worker = threading.Thread(target=self._worker, daemon=True)
        self.worker.start()
    
    def _load_config(self, config_path: str) -> dict:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(config_path) or '.', exist_ok=True)
        
        # If the config file doesn't exist, create it with the default config
        if not os.path.exists(config_path):
            try:
                with open(config_path, 'w') as f:
                    json.dump(self.DEFAULT_CONFIG, f, indent=2)
                return self.DEFAULT_CONFIG
            except Exception as e:
                raise RuntimeError(f"Failed to create config file {config_path}: {e}")
        
        # Load the existing config file
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON in config file {config_path}: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to load config file {config_path}: {e}")
        
        # Validate the config structure (basic validation)
        if not all(key in config for key in ['formatters', 'handlers', 'loggers']):
            raise RuntimeError(f"Invalid config structure in {config_path}")
        
        return config
    
    def _worker(self) -> None:
        while True:
            try:
                log_data = self.q.get()
                if log_data is None:
                    break
                
                level_num = self.LEVELS.get(log_data['level'], 0)
                
                for handler_name in self.config['loggers']['root']['handlers']:
                    handler = self.config['handlers'].get(handler_name)
                    if not handler:
                        logging.error(f"Handler {handler_name} not found in config")
                        continue
                    
                    handler_level = self.LEVELS.get(handler['level'], 0)
                    if level_num >= handler_level:
                        self._handle_log(log_data, handler)
            except Exception as e:
                logging.error(f"Error in worker thread: {e}")
            finally:
                self.q.task_done()
    
    def _handle_log(self, log_data, handler) -> None:
        try:
            formatter = self.config['formatters'].get(handler['formatter'])
            if not formatter:
                logging.error(f"Formatter {handler['formatter']} not found")
                return
            
            formatted_msg = self._format_message(log_data, formatter)
            handler_type = handler['type']
            
            if handler_type == 'stdout':
                print(formatted_msg, flush=True)  # Ensure immediate output
            elif handler_type == 'file':
                self._write_file(formatted_msg, handler['filename'])
            elif handler_type == 'email':
                self._send_email(formatted_msg, log_data)
        except Exception as e:
            logging.error(f"Error handling log for {handler['type']}: {e}")
    
    def _format_message(self, log_data, formatter) -> str:
        try:
            if formatter['format'] == 'json':
                return json.dumps({
                    field: log_data.get(field) if field != 'extras'
                    else {k: v for k, v in log_data.items() if k not in ['timestamp', 'level', 'message']}
                    for field in formatter['fields']
                })
            elif formatter['format'] == 'text':
                return formatter['template'].format(**log_data)
        except Exception as e:
            logging.error(f"Error formatting message: {e}")
        return json.dumps(log_data)
    
    def _write_file(self, message, filename) -> None:
        try:
            # Ensure the directory for the log file exists
            os.makedirs(os.path.dirname(filename) or '.', exist_ok=True)
            with open(filename, 'a') as f:
                f.write(message + '\n')
                f.flush()  # Ensure immediate write
        except Exception as e:
            logging.error(f"Error writing to file {filename}: {e}")
    
    def _send_email(self, message, log_data) -> None:
        if not self.SMTP_CONFIG:
            logging.error("SMTP configuration not provided, skipping email")
            return
        try:
            msg = MIMEText(message)
            msg['Subject'] = f"CRITICAL: {log_data.get('message', '')}"
            msg['From'] = self.SMTP_CONFIG.user
            msg['To'] = self.SMTP_CONFIG.to

            with smtplib.SMTP(self.SMTP_CONFIG.host, self.SMTP_CONFIG.port) as server:
                server.starttls()
                server.login(self.SMTP_CONFIG.user, self.SMTP_CONFIG.password)
                server.send_message(msg)
        except Exception as e:
            logging.error(f"Error sending email: {e}")
    
    def log(self, level, message, **kwargs) -> None:
        if level not in self.LEVELS:
            logging.error(f"Invalid log level: {level}")
            return
        log_data = {
            'timestamp': datetime.now().isoformat(),
            'level': level,
            'message': message,
            **kwargs
        }
        self.q.put(log_data)
    
    def debug(self, message, **kwargs) -> None:
        self.log('DEBUG', message, **kwargs)
    
    def info(self, message, **kwargs) -> None:
        self.log('INFO', message, **kwargs)
    
    def warning(self, message, **kwargs) -> None:
        self.log('WARNING', message, **kwargs)
    
    def error(self, message, **kwargs) -> None:
        self.log('ERROR', message, **kwargs)
    
    def critical(self, message, **kwargs) -> None:
        self.log('CRITICAL', message, **kwargs)
    
    def close(self) -> None:
        self.q.put(None)
        self.worker.join()


# Usage
if __name__ == "__main__":
    logger = JSONLogger("backend/config/logger_config.json")
    
    logger.debug("Debug message")      # Only to file
    logger.info("Info message")        # Only to file
    logger.error("Error occurred")     # To console + file
    logger.critical("System failure", module="main", function="main", lineno=1) # To email + console + file
    
    logger.close()
