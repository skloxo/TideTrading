import os
import json
from pathlib import Path
from typing import Dict, Any, List

from src.config.paths import get_runs_dir

class SimulationGraphManager:
    """
    轻量级本地图谱管理器
    管理大屏中的题材、板块、个股与智能体节点关系，持久化在 runs 目录下。
    """
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        # Compute run directory based on active tenant context
        self.file_path = get_runs_dir() / f"simulation_graph_{tenant_id}.json"
        self._ensure_file()
        
    def _ensure_file(self):
        os.makedirs(self.file_path.parent, exist_ok=True)
        if not self.file_path.exists():
            # Seed default fallback graph data to make it look professional out of the box
            default_data = {
                "nodes": [
                    {"id": "low-alt", "name": "低空经济", "categoryName": "题材板块", "value": "2.8亿", "itemStyle": {"color": "#ff3366"}},
                    {"id": "ai-count", "name": "AI算力", "categoryName": "题材板块", "value": "4.5亿", "itemStyle": {"color": "#ff3366"}},
                    {"id": "wanfeng", "name": "万丰奥威", "categoryName": "热门个股", "value": "主买流入+1.2亿", "itemStyle": {"color": "#00ff88"}},
                    {"id": "fulan", "name": "工业富联", "categoryName": "热门个股", "value": "主力买入+2.3亿", "itemStyle": {"color": "#00ff88"}},
                    {"id": "ningde", "name": "宁德时代", "categoryName": "热门个股", "value": "机构买入+3.1亿", "itemStyle": {"color": "#00ff88"}},
                    {"id": "byd", "name": "比亚迪", "categoryName": "热门个股", "value": "北向资金流出-1.5亿", "itemStyle": {"color": "#e5a93c"}},
                    {"id": "yuzi", "name": "游资·游侠", "categoryName": "AI智能体", "value": "当前仓位: 85%", "itemStyle": {"color": "#00e5ff"}},
                    {"id": "beixiang", "name": "北向资金", "categoryName": "AI智能体", "value": "当前仓位: 42%", "itemStyle": {"color": "#00e5ff"}}
                ],
                "links": [
                    {"source": "low-alt", "target": "wanfeng", "weight": 0.89},
                    {"source": "ai-count", "target": "fulan", "weight": 0.92},
                    {"source": "yuzi", "target": "wanfeng", "weight": 0.78},
                    {"source": "beixiang", "target": "ningde", "weight": 0.85},
                    {"source": "beixiang", "target": "byd", "weight": 0.65}
                ]
            }
            self.save(default_data)
            
    def load(self) -> Dict[str, Any]:
        try:
            if self.file_path.exists():
                with open(self.file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return {"nodes": [], "links": []}
        
    def save(self, data: Dict[str, Any]):
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def add_node(self, node_id: str, name: str, category: str, value: str = "", color: str = ""):
        data = self.load()
        # Check if node already exists
        for node in data.get("nodes", []):
            if node["id"] == node_id:
                node["name"] = name
                node["categoryName"] = category
                if value:
                    node["value"] = value
                if color:
                    node["itemStyle"] = {"color": color}
                self.save(data)
                return
        
        # Add new node
        new_node = {
            "id": node_id,
            "name": name,
            "categoryName": category,
            "value": value,
            "itemStyle": {"color": color} if color else {}
        }
        data.setdefault("nodes", []).append(new_node)
        self.save(data)

    def add_link(self, source: str, target: str, weight: float = 0.5):
        data = self.load()
        for link in data.get("links", []):
            if link["source"] == source and link["target"] == target:
                link["weight"] = weight
                self.save(data)
                return
        
        new_link = {
            "source": source,
            "target": target,
            "weight": weight
        }
        data.setdefault("links", []).append(new_link)
        self.save(data)
