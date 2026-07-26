import asyncio
import threading


class CancellationToken:
    """Cờ hủy phân cấp.

    Token con dùng cho từng tài khoản: hủy con chỉ bỏ qua tài khoản đó, hủy cha (nút Dừng)
    thì mọi con đều coi như đã hủy.
    """

    def __init__(self, parent: "CancellationToken | None" = None) -> None:
        self._event = threading.Event()
        self._parent = parent

    @property
    def cancelled(self) -> bool:
        return self._event.is_set() or (self._parent is not None and self._parent.cancelled)

    def cancel(self) -> None:
        self._event.set()

    def child(self) -> "CancellationToken":
        return CancellationToken(parent=self)

    def raise_if_cancelled(self) -> None:
        if self.cancelled:
            raise asyncio.CancelledError
