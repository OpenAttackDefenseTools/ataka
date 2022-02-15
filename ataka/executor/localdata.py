from dataclasses import dataclass
from enum import Enum

from ataka.common.database.models import JobExecutionStatus


class LocalExploitStatus(str, Enum):
    BUILDING = "building"
    FINISHED = "finished"
    ERROR = "error"


@dataclass
class LocalExploit:
    file: str
    status: LocalExploitStatus
    build_output: str = ""
    docker_id: str = None
    docker_cmd: [] = None


@dataclass
class LocalTarget:
    ip: str
    extra: str = ""


@dataclass
class LocalExecution:
    database_id: int
    exploit: LocalExploit
    target: LocalTarget
    status: JobExecutionStatus
    stdout: str = ""
    stderr: str = ""


@dataclass
class LocalJob:
    exploit: LocalExploit
    timeout: float
    executions: [LocalExecution]
