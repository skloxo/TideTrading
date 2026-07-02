import os
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

class ReportLogger:
    """
    Report Agent 详细日志记录器
    在 runs 目录中生成 agent_log_{tenant_id}.jsonl 文件，记录每一步 ReACT 动作。
    """
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.log_file_path = Path(__file__).resolve().parents[2] / "runs" / f"agent_log_{tenant_id}.jsonl"
        self.start_time = datetime.now()
        self._ensure_log_file()
        
    def _ensure_log_file(self):
        os.makedirs(self.log_file_path.parent, exist_ok=True)
        
    def _get_elapsed_time(self) -> float:
        return (datetime.now() - self.start_time).total_seconds()
        
    def log(self, action: str, stage: str, details: Dict[str, Any], section_title: str = None):
        """
        记录一条日志到 JSONL 文件中
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "elapsed_seconds": round(self._get_elapsed_time(), 2),
            "tenant_id": self.tenant_id,
            "action": action,
            "stage": stage,
            "section_title": section_title,
            "details": details
        }
        try:
            with open(self.log_file_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def log_thought(self, thought: str, stage: str = "generating", section_title: str = None):
        self.log("thought", stage, {"thought": thought}, section_title)

    def log_tool_call(self, tool_name: str, tool_args: Any, stage: str = "generating", section_title: str = None):
        self.log("tool_call", stage, {"tool_name": tool_name, "tool_args": tool_args}, section_title)

    def log_observation(self, observation: str, stage: str = "generating", section_title: str = None):
        self.log("observation", stage, {"observation": observation}, section_title)

    def log_decision(self, decision: str, stage: str = "completed", section_title: str = None):
        self.log("decision", stage, {"text": decision}, section_title)

    def clear_logs(self):
        try:
            if self.log_file_path.exists():
                os.remove(self.log_file_path)
        except Exception:
            pass
