"""实体类型枚举与校验。"""
from __future__ import annotations

from enum import Enum


class EntityType(str, Enum):
    device = "device"
    component = "component"
    fault = "fault"
    fault_cause = "fault_cause"
    solution = "solution"

    @property
    def display_name(self) -> str:
        return _DISPLAY[self]

    @property
    def table_name(self) -> str:
        return _TABLE[self]


_DISPLAY = {
    EntityType.device: "设备",
    EntityType.component: "部件",
    EntityType.fault: "故障",
    EntityType.fault_cause: "故障原因",
    EntityType.solution: "解决方案",
}

_TABLE = {
    EntityType.device: "device",
    EntityType.component: "component",
    EntityType.fault: "fault",
    EntityType.fault_cause: "fault_cause",
    EntityType.solution: "solution",
}


def validate_type(value: str) -> EntityType | None:
    try:
        return EntityType(value)
    except ValueError:
        return None


def valid_types() -> list[str]:
    return [e.value for e in EntityType]
