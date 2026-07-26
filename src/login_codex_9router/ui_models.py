from dataclasses import dataclass

from .auth.results import WAITING_MANUAL_STATUS


@dataclass(frozen=True, slots=True)
class ViotpConfig:
    token: str
    network: str
    balance: int | float | None

    @property
    def summary(self) -> str:
        if self.balance is None:
            return f"VIOTP: Đã lưu · {self.network}"
        balance = f"{self.balance:,.0f}".replace(",", ".")
        return f"VIOTP: Đã kết nối · {balance}đ"


@dataclass(frozen=True, slots=True)
class ResultStats:
    total: int = 0
    running: int = 0
    success: int = 0
    failed: int = 0
    cancelled: int = 0
    waiting: int = 0


# Trạng thái không phải lỗi. Mọi giá trị khác đều tính là thất bại, vì các mã lỗi auth
# (invalid_password, rate_limited, ...) được báo thẳng bằng tên mã.
_NON_FAILURE_STATUSES = {"pending", "running", "success", "cancelled", WAITING_MANUAL_STATUS}


def calculate_stats(statuses: dict[int, str]) -> ResultStats:
    values = tuple(statuses.values())
    return ResultStats(
        total=len(values),
        running=values.count("running"),
        success=values.count("success"),
        failed=sum(status not in _NON_FAILURE_STATUSES for status in values),
        cancelled=values.count("cancelled"),
        waiting=values.count(WAITING_MANUAL_STATUS),
    )
