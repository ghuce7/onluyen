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
  <h1>đŸ§  MatGoc AI (AI Cho NgÆ°á»i Máº¥t Gá»‘c)</h1>
  <p>Há»‡ thá»‘ng Gia sÆ° AI cĂ¡ nhĂ¢n tá»± Ä‘á»™ng "nhai" tĂ i liá»‡u (PDF, TXT) vĂ  táº¡o ra lá»™ trĂ¬nh há»c, tháº» kiáº¿n thá»©c, vĂ­ dá»¥ thá»±c táº¿ vĂ  bĂ i kiá»ƒm tra. Hoáº¡t Ä‘á»™ng 100% báº±ng API miá»…n phĂ­!</p>
</div>

## âœ¨ TĂ­nh nÄƒng ná»•i báº­t

*   **TÆ° duy "Gia sÆ° máº¥t gá»‘c":** KhĂ´ng dĂ¹ng tá»« ngá»¯ hĂ n lĂ¢m. AI tá»± Ä‘á»™ng tĂ¬m kiáº¿m cĂ¡c phĂ©p áº©n dá»¥ (analogy) gáº§n gÅ©i vá»›i Ä‘á»i sá»‘ng Ä‘á»ƒ giáº£i thĂ­ch cĂ¡c khĂ¡i niá»‡m phá»©c táº¡p.
*   **đŸ”„ Multi-LLM Fallback ThĂ´ng minh:** Tá»± Ä‘á»™ng xoay tua API giá»¯a **Gemini 2.0 Flash/Lite -> Groq (Llama 3) -> OpenRouter (Free models)**. CĂ³ cÆ¡ cháº¿ tá»± Ä‘á»™ng chá» náº¿u bá»‹ Rate Limit, Ä‘áº£m báº£o báº¡n khĂ´ng tá»‘n 1 Ä‘á»“ng tiá»n API nĂ o.
*   **đŸ’¾ Zero-Setup Local Storage:** LÆ°u trá»¯ má»i thá»© dÆ°á»›i dáº¡ng JSON gá»n nháº¹ ngay trĂªn mĂ¡y. KHĂ”NG cáº§n cĂ i Ä‘áº·t Database (PostgreSQL/MongoDB). KHĂ”NG dĂ¹ng VectorDB phá»©c táº¡p. CĂ³ sáºµn tĂ­nh nÄƒng nĂ©n ZIP Backup dá»¯ liá»‡u.
*   **â¡ Local Auto-Grading:** Cháº¥m Ä‘iá»ƒm bĂ i thi tráº¯c nghiá»‡m báº±ng thuáº­t toĂ¡n Regex trá»±c tiáº¿p trĂªn mĂ¡y, giĂºp tiáº¿t kiá»‡m tá»‘i Ä‘a API cho cĂ¡c tĂ¡c vá»¥ táº¡o ná»™i dung.
*   **đŸ“ BĂ i táº­p & Thi thá»­:** Tá»± Ä‘á»™ng sinh bĂ i táº­p háº±ng ngĂ y vĂ  bá»™ Ä‘á» Ă´n thi cáº¥p tá»‘c tá»« chĂ­nh tĂ i liá»‡u cá»§a báº¡n.

## đŸ€ CĂ i Ä‘áº·t & Cháº¡y á»©ng dá»¥ng

**BÆ°á»›c 1:** Clone mĂ£ nguá»“n vá» mĂ¡y
```bash
git clone https://github.com/your-username/matgoc-ai.git
cd matgoc-ai
```

**BÆ°á»›c 2:** CĂ i Ä‘áº·t cĂ¡c thÆ° viá»‡n cáº§n thiáº¿t
```bash
pip install -r requirements.txt
```

**BÆ°á»›c 3:** Cáº¥u hĂ¬nh API Key
Copy file `.env.example` thĂ nh file `.env` vĂ  Ä‘iá»n API Keys cá»§a báº¡n vĂ o (Hoáº·c báº¡n cĂ³ thá»ƒ bá» qua bÆ°á»›c nĂ y vĂ  nháº­p trá»±c tiáº¿p Key ngay trĂªn giao diá»‡n Web).
```bash
cp .env.example .env
```

**BÆ°á»›c 4:** Khá»Ÿi cháº¡y á»©ng dá»¥ng
```bash
streamlit run app.py
```
á»¨ng dá»¥ng sáº½ tá»± Ä‘á»™ng má»Ÿ táº¡i: `http://localhost:8501`

## đŸ›  Kiáº¿n trĂºc há»‡ thá»‘ng
* **Framework:** Streamlit
* **LLM Routing:** Custom Router (Há»— trá»£ xá»­ lĂ½ lá»—i 429 theo phĂºt vĂ  theo ngĂ y, tá»± Ä‘á»™ng sá»­a lá»—i JSON mĂ³p mĂ©o).
* **Parsers:** Há»— trá»£ Ä‘á»c `.pdf`, `.txt`, `.md`.
* **Database:** Atomic Local JSON Files.

## đŸ¤ ÄĂ³ng gĂ³p (Contributing)
Má»i Pull Request Ä‘á»u Ä‘Æ°á»£c chĂ o Ä‘Ă³n! Náº¿u báº¡n tháº¥y lá»—i hoáº·c muá»‘n thĂªm tĂ­nh nÄƒng, hĂ£y táº¡o Issue má»›i nhĂ©.

## đŸ“œ Giáº¥y phĂ©p (License)
Dá»± Ă¡n Ä‘Æ°á»£c phĂ¢n phá»‘i dÆ°á»›i giáº¥y phĂ©p **GPL-3.0 License**. 
Äiá»u nĂ y cĂ³ nghÄ©a lĂ : Báº¥t ká»³ ai láº¥y mĂ£ nguá»“n nĂ y Ä‘á»ƒ sá»­ dá»¥ng hoáº·c phĂ¡t triá»ƒn thĂ nh má»™t pháº§n má»m khĂ¡c, há» **báº¯t buá»™c pháº£i cĂ´ng khai toĂ n bá»™ mĂ£ nguá»“n** cá»§a há» vĂ  khĂ´ng Ä‘Æ°á»£c phĂ©p Ä‘Ă³ng gĂ³i thĂ nh pháº§n má»m Ä‘á»™c quyá»n (nháº±m ngÄƒn cháº·n viá»‡c cĂ¡c cĂ´ng ty láº¥y Ă½ tÆ°á»Ÿng Ä‘i kinh doanh trá»¥c lá»£i cĂ¡ nhĂ¢n).

