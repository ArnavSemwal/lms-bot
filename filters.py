import json
from pathlib import Path
from datetime import datetime

CONFIG_FILE = Path("filter_config.json")
BLOCKED_LOG_FILE = Path("blocked_log.json")

def load_allowlist() -> list[str]:
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text()).get("allowed_keywords", [])
    return []

def is_allowed(assignment_title: str, course_title: str, allowlist: list[str]) -> bool:
    text = f"{assignment_title} {course_title}".lower()
    return any(keyword.lower() in text for keyword in allowlist)

def log_blocked(assignment_title: str, course_title: str):
    log_entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "course": course_title,
        "assignment": assignment_title
    }
    
    logs = []
    if BLOCKED_LOG_FILE.exists():
        try:
            logs = json.loads(BLOCKED_LOG_FILE.read_text())
        except json.JSONDecodeError:
            pass
            
    logs.append(log_entry)
    logs = logs[-50:] 
    
    BLOCKED_LOG_FILE.write_text(json.dumps(logs, indent=2))