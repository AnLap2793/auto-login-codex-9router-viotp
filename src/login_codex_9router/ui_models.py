from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ViotpConfig:
    token: str
    network: str
    balance: int | float

    @property
    def summary(self) -> str:
        balance = f"{self.balance:,.0f}".replace(",", ".")
        return f"VIOTP: Đã kết nối · {balance}đ"


@dataclass(frozen=True, slots=True)
class ResultStats:
    total: int = 0
    running: int = 0
    success: int = 0
    failed: int = 0
    cancelled: int = 0


def calculate_stats(statuses: dict[int, str]) -> ResultStats:
    values = tuple(statuses.values())
    terminal_known = {"pending", "running", "success", "cancelled"}
    return ResultStats(
        total=len(values),
        running=values.count("running"),
        success=values.count("success"),
        failed=sum(status not in terminal_known for status in values),
        cancelled=values.count("cancelled"),
    )
