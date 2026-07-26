# Phase 03 — Bổ sung `docs/` theo cấu trúc bắt buộc

**Ưu tiên:** P2
**Trạng thái:** Xong

## Bối cảnh

CLAUDE.md quy định cấu trúc `docs/`. Trước phase này chỉ có:

```
docs/
├── project-notes.md      (spec, giữ nguyên)
├── api/viotp.md          (tài liệu API VIOTP, giữ nguyên)
└── journals/
```

## File tạo mới

| File | Nội dung |
|------|----------|
| `project-overview-pdr.md` | Mục tiêu, phạm vi, dữ liệu vào/ra, yêu cầu an toàn |
| `system-architecture.md` | Kiến trúc, luồng OAuth callback, mô hình 1 Chrome/tài khoản |
| `codebase-summary.md` | Bảng module → trách nhiệm → số dòng |
| `code-standards.md` | Quy ước thực tế đang dùng trong repo |
| `deployment-guide.md` | Chạy từ source, build EXE, vị trí file config |
| `project-roadmap.md` | Trạng thái từng hạng mục + mục ngoài phạm vi |

Bỏ `design-guidelines.md`: dự án không có design system, tạo file rỗng chỉ gây nhiễu.

## Yêu cầu nội dung

- Tiếng Việt, khớp README và UI.
- Phản ánh cấu trúc module **sau** refactor Phase 02.
- Nêu rõ VIOTP tự động thuê số là **quyết định thiết kế**, không phải việc chưa làm.
- Không bịa API, tên file hay lệnh. Không đưa secret vào ví dụ.

## Tiêu chí hoàn thành

- [x] 6 file được tạo
- [x] Mỗi file < ~120 dòng
- [x] Không sửa `README.md` và `docs/project-notes.md`
