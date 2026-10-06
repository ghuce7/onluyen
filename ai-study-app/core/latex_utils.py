import re

def clean_latex(s: str) -> str:
    """
    Làm sạch chuỗi LaTeX:
    - Bỏ backtick
    - Bỏ $ và $$ ở đầu cuối
    - Đổi \\( \\) \\[ \\] thành dạng trần
    - Bỏ khoảng trắng thừa
    - Kiểm tra ngoặc { } cân nhau
    """
    if not s:
        return ""
    
    # Bỏ backtick
    s = s.replace("`", "")
    
    # Xoá prefix/suffix marker toán học
    s = re.sub(r'^\$\$(.*?)\$\$$', r'\1', s, flags=re.DOTALL)
    s = re.sub(r'^\$(.*?)\$$', r'\1', s, flags=re.DOTALL)
    s = re.sub(r'^\\\[(.*?)\\\]$', r'\1', s, flags=re.DOTALL)
    s = re.sub(r'^\\\((.*?)\\\)$', r'\1', s, flags=re.DOTALL)
    
    # Strip whitespace
    s = s.strip()
    
    # Loại bỏ lặp lại $ bên trong nếu nó bọc toàn bộ (trường hợp cặn)
    if s.startswith('$') and s.endswith('$'):
        s = s[1:-1].strip()
        
    return s

def is_valid_latex(s: str) -> bool:
    """Kiểm tra cơ bản xem LaTeX có hợp lệ không (ví dụ: ngoặc nhọn cân bằng)."""
    if not s:
        return True
    
    # Kiểm tra cân bằng ngoặc nhọn {}
    balance = 0
    for char in s:
        if char == '{':
            balance += 1
        elif char == '}':
            balance -= 1
            if balance < 0:
                return False
    return balance == 0
