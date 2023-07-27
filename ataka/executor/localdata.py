from dataclasses import dataclass
from enum import Enum

from ataka.common.job_execution_status import JobExecutionStatus


class LocalExploitStatus(str, Enum):
    BUILDING = "building"
    FINISHED = "finished"
    ERROR = "error"


@dataclass
class LocalExploit:
    id: str
    service: str
    author: str
    docker_name: str
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
