"""Cấu hình mapping cho extraction và normalization.

File này gom các rule cố định về một nơi để:
- Dễ chỉnh khi demo
- Dễ mở rộng sang domain mới
- Tránh hardcode domain e-commerce
"""

# Danh sách từ khóa nhận diện human actor.
# Theo rule của project, actor là người dùng thật sẽ luôn được xếp "complex".
HUMAN_ACTOR_KEYWORDS = (
    "customer",
    "user",
    "reader",
    "librarian",
    "instructor",
    "member",
    "staff",
    "administrator",
    "admin",
    "manager",
    "employee",
    "teacher",
    "student",
    "doctor",
    "nurse",
    "patient",
    "receptionist",
    "guest",
    "client",
    "buyer",
    "seller",
    "cashier",
    "operator",
    "supervisor",
    "accountant",
    "borrower",
    "applicant",
    "vendor",
)

# Danh sách từ khóa nhận diện external actor.
# Các actor kiểu service, gateway, API... sẽ được xếp "simple".
EXTERNAL_ACTOR_KEYWORDS = (
    "payment gateway",
    "email service",
    "notification service",
    "sms service",
    "api",
    "third-party system",
    "third-party service",
    "external system",
    "authentication service",
    "identity provider",
    "banking service",
    "shipping service",
    "delivery service",
    "inventory system",
    "erp system",
    "crm system",
    "reporting service",
)

# Các từ không được xem là actor trong UCP.
# Ví dụ "System" chỉ là đối tượng mô tả hệ thống, không phải actor tương tác từ bên ngoài.
IGNORE_AS_ACTOR = (
    "system",
    "application",
    "platform",
    "software",
    "database",
    "server",
)

# Danh sách động từ/hành động thường gặp để nhận diện candidate use case.
# File extractor dùng danh sách này để kiểm tra một đoạn text có phải hành động chức năng hay không.
ACTION_VERB_PATTERNS = (
    "register",
    "enroll",
    "login",
    "logout",
    "search",
    "lookup",
    "view",
    "browse",
    "check",
    "display",
    "add",
    "create",
    "submit",
    "update",
    "delete",
    "place",
    "checkout",
    # Nhóm banking mới thêm để nhận ra các use case chuyển tiền.
    "transfer",
    "pay",
    "borrow",
    "return",
    "reserve",
    "schedule",
    "approve",
    "confirm",
    "generate",
    "manage",
    "upload",
    "download",
    "send",
    "notify",
    "assign",
    "review",
    "track",
    "book",
)

# Các internal step cần loại khỏi danh sách use case.
# Đây thường là hành vi nền của hệ thống, không phải business goal do actor chủ động thực hiện.
INTERNAL_STEP_EXCLUSIONS = (
    "send confirmation",
    "send reminder",
    "send notification",
    "notify user",
    "notify customer",
    "notify reader",
    "notify patient",
    "alert user",
    "alert customer",
    "alert reader",
    "alert patient",
    "overdue reminder",
    "overdue reminders",
    "validate input",
    "validate data",
    "update status",
    "log activity",
    "store data",
    "save record",
    "calculate total",
    "verify payment",
    "update stock",
    "update inventory",
)

# Rule gộp nhiều sub-action nhỏ thành một use case cha dễ hiểu hơn.
# Ví dụ "update room availability" sẽ được gom thành "Manage Room Information".
MERGE_RULES = {
    "update stock": "Manage Products",
    "update inventory": "Manage Inventory",
    "update book inventory": "Manage Book Information",
    "update room availability": "Manage Room Information",
    "edit room availability": "Manage Room Information",
    "delete room availability": "Manage Room Information",
    "add/edit/delete product": "Manage Products",
    "add edit delete product": "Manage Products",
    "send confirmation": None,
    "send reminder": None,
}

# Chuẩn hóa một số tên actor phổ biến để frontend hiển thị nhất quán.
ACTOR_NAME_NORMALIZATION = {
    "admin": "Administrator",
}

# Chuẩn hóa động từ về một tên use case canonical.
# Mục tiêu là đưa output về dạng ngắn gọn "Verb + Noun" để dễ tính UCP và dễ demo.
VERB_CANONICAL_MAP = {
    "log in": "Login",
    "login": "Login",
    "sign in": "Login",
    "log out": "Logout",
    "logout": "Logout",
    "sign out": "Logout",
    "sign up": "Register",
    "register account": "Register",
    "create account": "Register",
    "register": "Register",
    "enroll in": "Enroll In",
    "enroll": "Enroll",
    "look up": "Lookup",
    "lookup": "Lookup",
    "search": "Search",
    "view": "View",
    "browse": "Browse",
    "check": "Check",
    "display": "Display",
    "add": "Add",
    "create": "Create",
    "submit": "Submit",
    "update": "Update",
    "delete": "Delete",
    "place": "Place",
    "checkout": "Checkout",
    # Nhóm banking:
    # cố định các tên liên quan chuyển tiền để output không bị lung tung giữa nhiều cách viết.
    "transfer money": "Transfer Money",
    "transfer funds": "Transfer Funds",
    "transfer payment": "Transfer Payment",
    "transfer": "Transfer",
    "send money": "Send Money",
    "make payment": "Make Payment",
    "pay": "Pay",
    "borrow": "Borrow",
    "return": "Return",
    "reserve": "Reserve",
    "schedule": "Schedule",
    "approve": "Approve",
    "confirm": "Confirm",
    "generate": "Generate",
    "manage": "Manage",
    "upload": "Upload",
    "download": "Download",
    "notify": "Notify",
    "assign": "Assign",
    "review": "Review",
    "track": "Track",
    "book": "Book",
}

# Prefix ưu tiên cho nhóm simple.
# Nếu use case bắt đầu bằng các hành động này thì thường là thao tác tra cứu/hiển thị đơn giản.
SIMPLE_USE_CASE_PREFIXES = (
    "Login",
    "Logout",
    "Lookup",
    "Search",
    "View",
    "Browse",
    "Check",
    "Display",
    "Track",
)

# Prefix ưu tiên cho nhóm average.
# Đây là các use case có mức xử lý trung bình như đăng ký, xác nhận, thanh toán, tạo dữ liệu.
AVERAGE_USE_CASE_PREFIXES = (
    "Register",
    "Return",
    "Confirm",
    "Approve",
    "Pay",
    "Make Payment",
    "Schedule",
    "Generate",
    "Review",
    "Upload",
    "Download",
)

# Prefix ưu tiên cho nhóm complex.
# Các action ở đây thường là transactional workflow nhiều bước hoặc quản trị mức cao.
COMPLEX_USE_CASE_PREFIXES = (
    "Place Order",
    # Nhóm banking mới:
    # các use case chuyển tiền luôn được coi là complex vì có nhiều bước xác thực/giao dịch.
    "Transfer Money",
    "Transfer Funds",
    "Transfer Payment",
    "Send Money",
    "Checkout",
    "Enroll",
    "Borrow Books",
    "Manage",
    "Delete",
    "Assign",
    "Book Room",
    "Book Rooms",
    "Reserve",
)

# Bộ từ khóa action cho simple.
SIMPLE_USE_CASE_ACTION_KEYWORDS = (
    "login",
    "logout",
    "lookup",
    "search",
    "view",
    "browse",
    "check",
    "display",
    "track",
)

# Bộ từ khóa action cho average.
AVERAGE_USE_CASE_ACTION_KEYWORDS = (
    "register",
    "create",
    "submit",
    "update",
    "confirm",
    "approve",
    "return",
    "payment",
    "pay",
    "review",
)

# Bộ từ khóa action cho complex.
# Đây là lớp fallback khi prefix không match nhưng câu vẫn mang tính giao dịch nhiều bước.
COMPLEX_USE_CASE_ACTION_KEYWORDS = (
    # Banking:
    "transfer",
    "transfer money",
    "transfer funds",
    "transfer payment",
    "send money",
    "book",
    "booking",
    "reserve",
    "borrow",
    "enroll",
    "place order",
    "checkout",
    "order",
    "manage",
    "schedule",
    "assign",
)

# Hậu tố dùng để đoán một từ có thể là vai trò con người khi extractor chưa chắc chắn.
ROLE_LIKE_SUFFIXES = (
    "er",
    "or",
    "ian",
    "ist",
    "ant",
    "ent",
)

# Một vài từ nối thừa ở cuối use case sẽ bị cắt bỏ để tên ngắn và sạch hơn.
TRAILING_USE_CASE_FILLER_WORDS = (
    "by",
    "for",
    "to",
    "with",
    "from",
    "into",
    "through",
    "online",
)
