from typing import List, Literal
from pydantic import BaseModel, Field

class SymbolDef(BaseModel):
    symbol: str = Field(..., description="Ký hiệu (LaTeX, không có $)")
    meaning: str = Field("", description="Ý nghĩa chi tiết theo ngữ cảnh")

class KnowledgeItem(BaseModel):
    type: Literal["formula", "concept", "process", "fact", "compare"] = Field(..., description="Phân loại kiến thức")
    title: str = Field(..., min_length=1, description="Tên mục ngắn gọn")
    plain: str = Field("", description="Giải thích 1-3 câu bằng lời đời thường")
    analogy: str = Field("", description="Ví von với đời sống hằng ngày (1-2 câu)")
    prereq: List[str] = Field(default_factory=list, description="Danh sách kiến thức cần biết trước (có thể rỗng)")
    formula_latex: str = Field("", description="Công thức LaTeX sạch (không $, không backtick, không text lẫn vào), rỗng nếu không phải công thức")
    formula_words: str = Field("", description="Đọc công thức bằng lời (ví dụ: A bằng B chia C), rỗng nếu không có công thức")
    symbols: List[SymbolDef] = Field(default_factory=list, description="Tất cả ký hiệu có trong công thức và ý nghĩa")
    steps: List[str] = Field(default_factory=list, description="3-5 bước ngắn (dưới 10 từ/bước) mô tả quy trình hoặc cách dùng công thức")
    example: str = Field("", description="Ví dụ có SỐ CỤ THỂ, tính ra kết quả, kèm đơn vị (nếu là tính toán)")
    pitfall: str = Field("", description="Lỗi hay nhầm lẫn thường gặp")
    exam_tip: str = Field("", description="Dạng câu hỏi hay ra thi và cách nhận ra")
    keywords: List[str] = Field(default_factory=list, description="2-5 từ khóa chính")

class KnowledgeResponse(BaseModel):
    items: List[KnowledgeItem] = Field(..., description="Danh sách các mục kiến thức được trích xuất")
