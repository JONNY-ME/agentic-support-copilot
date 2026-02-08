from __future__ import annotations

PAYMENT_KEYWORDS = [
    # English
    "credit card", "debit card", "card number", "cvv", "cvc", "pin", "otp", "password",
    "bank transfer", "account number", "wire", "swift",
    "telebirr", "mpesa", "paypal",
    # Amharic (best-effort keywords)
    "ካርድ", "ፒን", "ፓስወርድ", "የባንክ መለያ", "ቴሌብር", "ኦቲፒ", "otp",
]

def is_payment_or_credentials_request(text: str) -> bool:
    t = text.lower()
    return any(k.lower() in t for k in PAYMENT_KEYWORDS)

def payment_refusal(language: str) -> str:
    if language == "am":
        return (
            "የክፍያ መረጃ (ካርድ ቁጥር፣ PIN፣ OTP እና ፓስወርድ) ለመስጠት አልችልም። "
            "እባክዎ በድርጅቱ የተፈቀደ የክፍያ መንገድ ብቻ ይጠቀሙ፣ ወይም የደንበኛ አገልግሎት ሰራተኛ እንዲያግዝዎ ልጠይቅ እችላለሁ።"
        )
    return (
        "I can’t help with payment or credential details (card numbers, PINs, OTPs, passwords). "
        "Please use the company’s official payment method, or I can escalate you to a human agent."
    )
