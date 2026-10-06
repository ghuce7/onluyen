---
title: MatGoc AI Tutor
emoji: 🧠
colorFrom: purple
colorTo: blue
sdk: streamlit
app_file: app.py
pinned: false
---

<div align="center">
  <h1>🧠 MatGoc AI (AI Cho Người Mất Gốc)</h1>
  <p>Hệ thống Gia sư AI cá nhân tự động "nhai" tài liệu (PDF, TXT) và tạo ra lộ trình học, thẻ kiến thức, ví dụ thực tế và bài kiểm tra. Hoạt động 100% bằng API miễn phí!</p>
</div>

## ✨ Tính năng nổi bật

*   **Tư duy "Gia sư mất gốc":** Không dùng từ ngữ hàn lâm. AI tự động tìm kiếm các phép ẩn dụ (analogy) gần gũi với đời sống để giải thích các khái niệm phức tạp.
*   **🔄 Multi-LLM Fallback Thông minh:** Tự động xoay tua API giữa **Gemini 2.0 Flash/Lite -> Groq (Llama 3) -> OpenRouter (Free models)**. Có cơ chế tự động chờ nếu bị Rate Limit, đảm bảo bạn không tốn 1 đồng tiền API nào.
*   **💾 Zero-Setup Local Storage:** Lưu trữ mọi thứ dưới dạng JSON gọn nhẹ ngay trên máy. KHÔNG cần cài đặt Database (PostgreSQL/MongoDB). KHÔNG dùng VectorDB phức tạp. Có sẵn tính năng nén ZIP Backup dữ liệu.
*   **⚡ Local Auto-Grading:** Chấm điểm bài thi trắc nghiệm bằng thuật toán Regex trực tiếp trên máy, giúp tiết kiệm tối đa API cho các tác vụ tạo nội dung.
*   **📝 Bài tập & Thi thử:** Tự động sinh bài tập hằng ngày và bộ đề ôn thi cấp tốc từ chính tài liệu của bạn.

## 🚀 Cài đặt & Chạy ứng dụng

**Bước 1:** Clone mã nguồn về máy
```bash
git clone https://github.com/your-username/matgoc-ai.git
cd matgoc-ai
