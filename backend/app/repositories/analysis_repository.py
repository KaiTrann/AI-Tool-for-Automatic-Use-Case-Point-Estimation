"""Repository lưu và đọc kết quả phân tích UCP trong MySQL.

Repository là lớp trung gian giữa API route và database:
- route không cần viết SQL trực tiếp
- database schema có thể thay đổi nhẹ mà ít ảnh hưởng phần xử lý nghiệp vụ
- sinh viên có thể mở file này để chứng minh dữ liệu được lưu ở bảng nào
"""

# Cho phép dùng type hint hiện đại mà không làm Python đánh giá annotation quá sớm.
from __future__ import annotations

# json dùng để chuyển list/dict Python sang chuỗi JSON trước khi lưu vào MySQL.
import json

# date/datetime dùng để convert dữ liệu thời gian từ MySQL sang JSON trả về frontend.
from datetime import date, datetime

# Decimal là kiểu dữ liệu MySQL connector trả về cho cột DECIMAL.
from decimal import Decimal

# Any dùng vì repository nhận nhiều kiểu dữ liệu: model Pydantic, dict, list, cursor...
from typing import Any

# Hàm tạo connection MySQL, tách riêng để repository chỉ tập trung vào SQL.
from app.database import get_connection


class AnalysisRepository:
    """Lớp gom các thao tác CRUD đơn giản cho một lần phân tích UCP."""

    def __init__(self, raise_errors: bool = False) -> None:
        # raise_errors=False dùng cho luồng demo chính:
        # nếu MySQL chưa bật, API vẫn trả kết quả như trước để không làm hỏng demo extraction/UCP.
        # raise_errors=True dùng cho endpoint truy vấn dữ liệu đã lưu:
        # nếu DB lỗi thì báo lỗi rõ ràng cho người gọi.
        # Lưu cờ raise_errors để biết khi DB lỗi thì nên raise hay chỉ lưu last_error.
        self.raise_errors = raise_errors
        # Lưu lỗi DB gần nhất để dễ debug khi API chính vẫn trả kết quả.
        self.last_error: str | None = None

    def create_document(
        self,
        title: str,
        input_type: str,
        original_filename: str | None,
        raw_text: str | None,
        source_template_type: str | None,
        parsing_status: str = "pending",
        notes: str | None = None,
    ) -> int | None:
        """Tạo bản ghi document để lưu input gốc của người dùng."""
        # SQL này insert một dòng vào bảng documents để lưu input gốc.
        sql = """
            INSERT INTO documents (
                title, input_type, original_filename, raw_text,
                source_template_type, parsing_status, notes
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        # Dùng _insert để tái sử dụng logic mở connection, execute, commit và close.
        return self._insert(
            sql,
            (
                # title là tên hiển thị của document trong lịch sử.
                title,
                # input_type cho biết input đến từ text, file upload hay payload thủ công.
                input_type,
                # original_filename lưu tên file nếu người dùng upload file.
                original_filename,
                # raw_text có thể không có ở /ucp/calculate, nên dùng "" để tránh lỗi DB cũ NOT NULL.
                raw_text or "",
                # source_template_type cho biết free_text hay structured_srs.
                source_template_type,
                # parsing_status ban đầu là running, sau đó chuyển success/failed.
                parsing_status,
                # notes là ghi chú phục vụ debug/demo.
                notes,
            ),
        )

    def create_analysis_run(
        self,
        document_id: int | None,
        llm_mode: str,
        technical_complexity_factor: float,
        environmental_complexity_factor: float,
        productivity_factor: float,
        team_size: int,
        run_type: str,
        status: str = "running",
    ) -> int | None:
        """Tạo một lần chạy phân tích gắn với document."""
        # Nếu document không tạo được thì không tạo analysis_run để tránh lỗi foreign key.
        if document_id is None:
            return None

        # SQL này tạo một lần chạy mới trong bảng analysis_runs.
        sql = """
            INSERT INTO analysis_runs (
                document_id, llm_mode, technical_complexity_factor,
                environmental_complexity_factor, productivity_factor,
                team_size, run_type, status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        return self._insert(
            sql,
            (
                # document_id là khóa ngoại trỏ tới documents.id.
                document_id,
                # llm_mode là mock, placeholder hoặc manual.
                llm_mode,
                # TCF dùng trong công thức UCP.
                technical_complexity_factor,
                # ECF dùng trong công thức UCP.
                environmental_complexity_factor,
                # productivity_factor là số giờ công cho mỗi UCP.
                productivity_factor,
                # team_size dùng để tính schedule.
                team_size,
                # run_type phân biệt extract_only, calculate_only, analyze_and_calculate.
                run_type,
                # status ban đầu thường là running.
                status,
            ),
        )

    def save_parsed_use_case_document(self, analysis_run_id: int | None, document: Any) -> int | None:
        """Lưu một Use Case Specification đã parse/normalize vào bảng parsed_use_case_documents."""
        # Không có analysis_run_id thì không biết parsed document thuộc lần chạy nào.
        if analysis_run_id is None:
            return None

        # SQL này lưu bản use case document đã parse để sau này xem lại parser đọc được gì.
        sql = """
            INSERT INTO parsed_use_case_documents (
                analysis_run_id, use_case_id, use_case_name, actors_json,
                primary_actor, secondary_actors_json, description, goal,
                trigger_event, preconditions, postconditions,
                functional_requirement, main_flow_steps_json,
                alternative_flow_steps_json, exception_flow_steps_json,
                priority, business_rules, source_template_type, notes
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        return self._insert(
            sql,
            (
                # Khóa ngoại tới analysis_runs.
                analysis_run_id,
                # Use Case ID, ví dụ UC.01.
                getattr(document, "use_case_id", None),
                # Use Case Name đã chuẩn hóa.
                getattr(document, "use_case_name", None),
                # actors_json lưu danh sách actor dạng JSON.
                self._to_json(getattr(document, "actors", [])),
                # primary_actor nếu parser tìm được.
                getattr(document, "primary_actor", None),
                # secondary_actors_json lưu actor phụ dạng JSON.
                self._to_json(getattr(document, "secondary_actors", [])),
                # description lấy từ template nếu có.
                getattr(document, "description", None),
                # goal/objective nếu tài liệu có field này.
                getattr(document, "goal", None),
                # trigger event của use case.
                getattr(document, "trigger", None),
                # preconditions.
                getattr(document, "preconditions", None),
                # postconditions.
                getattr(document, "postconditions", None),
                # functional requirement liên quan nếu parse được.
                getattr(document, "functional_requirement", None),
                # main flow steps lưu JSON để giữ nguyên từng bước.
                self._to_json(getattr(document, "main_flow_steps", [])),
                # alternative flow steps lưu JSON.
                self._to_json(getattr(document, "alternative_flow_steps", [])),
                # exception flow steps lưu JSON.
                self._to_json(getattr(document, "exception_flow_steps", [])),
                # priority nếu tài liệu có.
                getattr(document, "priority", None),
                # business rules nếu tài liệu có.
                getattr(document, "business_rules", None),
                # loại template/source parser nhận diện được.
                getattr(document, "source_template_type", None),
                # notes từ parser/normalizer.
                getattr(document, "notes", None),
            ),
        )

    def save_extracted_actor(
        self,
        analysis_run_id: int | None,
        actor_name: str,
        actor_type: str | None,
        complexity: str,
        weight_value: int,
        source_text: str | None = None,
    ) -> int | None:
        """Lưu một actor đã extract và đã gán weight."""
        # Không có run_id thì không thể lưu vì extracted_actors có foreign key.
        if analysis_run_id is None:
            return None

        # SQL này lưu từng actor thành một dòng riêng.
        sql = """
            INSERT INTO extracted_actors (
                analysis_run_id, actor_name, actor_type,
                complexity, weight_value, source_text
            )
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        return self._insert(
            sql,
            # Lưu tên actor, loại actor, complexity và trọng số UCP.
            (analysis_run_id, actor_name, actor_type, complexity, weight_value, source_text),
        )

    def save_extracted_use_case(
        self,
        analysis_run_id: int | None,
        use_case_id: str | None,
        use_case_name: str,
        complexity: str,
        weight_value: int,
        transaction_count: int | None,
        description: str | None,
        source_kind: str | None,
        source_text: str | None = None,
    ) -> int | None:
        """Lưu một use case đã extract và đã gán weight."""
        # Không có run_id thì không thể lưu vì extracted_use_cases có foreign key.
        if analysis_run_id is None:
            return None

        # SQL này lưu từng use case thành một dòng riêng.
        sql = """
            INSERT INTO extracted_use_cases (
                analysis_run_id, use_case_id, use_case_name, complexity,
                weight_value, transaction_count, description, source_kind, source_text
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        return self._insert(
            sql,
            (
                # Khóa ngoại tới analysis_runs.
                analysis_run_id,
                # ID use case nếu có.
                use_case_id,
                # Tên use case hiển thị trên UI.
                use_case_name,
                # simple, average hoặc complex.
                complexity,
                # 5, 10 hoặc 15 theo chuẩn UCP.
                weight_value,
                # Số transaction nếu lấy được từ structured document.
                transaction_count,
                # Mô tả hoặc thông tin transaction count.
                description,
                # free_text hoặc structured_document.
                source_kind,
                # Text nguồn để debug lại nếu cần.
                source_text,
            ),
        )

    def save_calculation(
        self,
        analysis_run_id: int | None,
        uaw: float,
        uucw: float,
        uucp: float,
        tcf: float,
        ecf: float,
        ucp: float,
        productivity_factor: float,
        effort_hours: float,
        person_days: float,
        team_size: int,
        schedule_months: float,
        sprint_count: int,
        recommended_team_size: int,
    ) -> int | None:
        """Lưu kết quả tính UCP/Effort/Schedule cuối cùng."""
        # Không có run_id thì calculation không biết thuộc lần tính nào.
        if analysis_run_id is None:
            return None

        # SQL này lưu toàn bộ metric cuối cùng vào bảng calculations.
        sql = """
            INSERT INTO calculations (
                analysis_run_id, uaw, uucw, uucp, tcf, ecf, ucp,
                productivity_factor, effort_hours, person_days, team_size,
                schedule_months, sprint_count, recommended_team_size
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        return self._insert(
            sql,
            (
                # Khóa ngoại tới analysis_runs.
                analysis_run_id,
                # UAW = tổng trọng số actor.
                uaw,
                # UUCW = tổng trọng số use case.
                uucw,
                # UUCP = UAW + UUCW.
                uucp,
                # Technical Complexity Factor.
                tcf,
                # Environmental Complexity Factor.
                ecf,
                # UCP sau khi nhân TCF và ECF.
                ucp,
                # Số giờ công cho mỗi UCP.
                productivity_factor,
                # Effort theo giờ.
                effort_hours,
                # Effort quy đổi theo ngày công.
                person_days,
                # Số thành viên team.
                team_size,
                # Schedule theo tháng.
                schedule_months,
                # Số sprint ước lượng.
                sprint_count,
                # Team size khuyến nghị.
                recommended_team_size,
            ),
        )

    def save_run_log(
        self,
        analysis_run_id: int | None,
        stage: str,
        status: str,
        message: str | None = None,
        raw_output: Any | None = None,
    ) -> int | None:
        """Lưu log từng giai đoạn để dễ debug khi demo hoặc viết báo cáo."""
        # Nếu chưa có run thì log không có nơi để gắn vào.
        if analysis_run_id is None:
            return None

        # SQL này lưu log pipeline như file_read, parser, extract, normalize, calculate.
        sql = """
            INSERT INTO run_logs (analysis_run_id, stage, status, message, raw_output)
            VALUES (%s, %s, %s, %s, %s)
        """
        return self._insert(
            sql,
            # raw_output nếu có sẽ được convert sang JSON text.
            (analysis_run_id, stage, status, message, self._to_json(raw_output) if raw_output is not None else None),
        )

    def mark_run_success(self, analysis_run_id: int | None) -> None:
        """Đánh dấu một lần chạy đã thành công."""
        # Không có run_id thì không cần cập nhật gì.
        if analysis_run_id is None:
            return

        # Cập nhật status và finished_at để lịch sử biết run đã hoàn tất.
        sql = """
            UPDATE analysis_runs
            SET status = 'success', finished_at = CURRENT_TIMESTAMP, error_message = NULL
            WHERE id = %s
        """
        # Chạy update bảng analysis_runs.
        self._execute(sql, (analysis_run_id,))
        # Đồng bộ trạng thái document thành success.
        self._update_document_parsing_status(analysis_run_id, "success")

    def mark_run_failed(self, analysis_run_id: int | None, error_message: str) -> None:
        """Đánh dấu một lần chạy thất bại và lưu thông báo lỗi."""
        # Không có run_id thì không thể cập nhật trạng thái failed.
        if analysis_run_id is None:
            return

        # Lưu thông báo lỗi để khi mở lịch sử/debug có thể biết fail ở đâu.
        sql = """
            UPDATE analysis_runs
            SET status = 'failed', finished_at = CURRENT_TIMESTAMP, error_message = %s
            WHERE id = %s
        """
        # Chạy update bảng analysis_runs.
        self._execute(sql, (error_message, analysis_run_id))
        # Đồng bộ trạng thái document thành failed.
        self._update_document_parsing_status(analysis_run_id, "failed")

    def get_analysis_result(self, run_id: int) -> dict[str, Any] | None:
        """Lấy đầy đủ document, actors, use cases, calculation và logs của một run."""
        # Lấy dòng analysis_run chính trước.
        run = self._fetch_one("SELECT * FROM analysis_runs WHERE id = %s", (run_id,))
        # Nếu không có run thì trả None để route báo 404.
        if run is None:
            return None

        # Lấy document gốc của run.
        document = self._fetch_one("SELECT * FROM documents WHERE id = %s", (run["document_id"],))
        # Lấy các use case document đã parse nếu input là SRS/template.
        parsed_documents = self._fetch_all(
            "SELECT * FROM parsed_use_case_documents WHERE analysis_run_id = %s ORDER BY id",
            (run_id,),
        )
        # Lấy danh sách actor đã lưu.
        actors = self._fetch_all(
            "SELECT * FROM extracted_actors WHERE analysis_run_id = %s ORDER BY id",
            (run_id,),
        )
        # Lấy danh sách use case đã lưu.
        use_cases = self._fetch_all(
            "SELECT * FROM extracted_use_cases WHERE analysis_run_id = %s ORDER BY id",
            (run_id,),
        )
        # Lấy calculation mới nhất của run.
        calculation = self._fetch_one(
            "SELECT * FROM calculations WHERE analysis_run_id = %s ORDER BY id DESC LIMIT 1",
            (run_id,),
        )
        # Lấy log theo thứ tự tạo để xem pipeline chạy thế nào.
        logs = self._fetch_all(
            "SELECT * FROM run_logs WHERE analysis_run_id = %s ORDER BY id",
            (run_id,),
        )

        # Gom toàn bộ dữ liệu thành một object cho endpoint GET /analysis-runs/{run_id}.
        return self._make_json_safe(
            {
                "run": run,
                "document": document,
                "parsed_use_case_documents": parsed_documents,
                "actors": actors,
                "use_cases": use_cases,
                "calculation": calculation,
                "logs": logs,
            }
        )

    def list_saved_runs(self) -> list[dict[str, Any]]:
        """Liệt kê các lần phân tích đã lưu, dùng cho kiểm tra nhanh sau demo."""
        # Query danh sách run gần nhất kèm title document và metric chính.
        sql = """
            SELECT
                ar.id,
                ar.run_type,
                ar.status,
                ar.llm_mode,
                ar.started_at,
                ar.finished_at,
                d.title AS document_title,
                d.input_type,
                d.original_filename,
                c.ucp,
                c.effort_hours,
                c.schedule_months
            FROM analysis_runs ar
            JOIN documents d ON d.id = ar.document_id
            LEFT JOIN calculations c ON c.analysis_run_id = ar.id
            ORDER BY ar.started_at DESC, ar.id DESC
            LIMIT 50
        """
        # Trả về list JSON-safe để FastAPI serialize được.
        return self._make_json_safe(self._fetch_all(sql, ()))

    def delete_analysis_run(self, run_id: int) -> bool:
        """Xóa một analysis run.

        Các bảng con như actors, use cases, calculations, logs sẽ tự xóa theo
        foreign key ON DELETE CASCADE trong database/schema.sql.
        """
        # Khởi tạo connection/cursor là None để finally có thể đóng an toàn.
        connection = None
        cursor = None
        try:
            # Mở connection mới tới MySQL.
            connection = get_connection()
            # Tạo cursor thường vì DELETE không cần dict cursor.
            cursor = connection.cursor()
            # Xóa analysis_run; các bảng con sẽ cascade.
            cursor.execute("DELETE FROM analysis_runs WHERE id = %s", (run_id,))
            # Commit để thay đổi được lưu thật vào DB.
            connection.commit()
            # rowcount > 0 nghĩa là có dòng bị xóa.
            return cursor.rowcount > 0
        except Exception as error:  # noqa: BLE001
            # Lưu/raise lỗi tùy cấu hình raise_errors.
            self._handle_error(error)
            # Trả False để route có thể báo không xóa được.
            return False
        finally:
            # Luôn đóng cursor/connection để tránh rò rỉ kết nối.
            self._close(cursor, connection)

    def _insert(self, sql: str, params: tuple[Any, ...]) -> int | None:
        """Chạy INSERT và trả về id vừa tạo."""
        # Khởi tạo None để finally đóng được kể cả khi lỗi xảy ra trước lúc tạo cursor.
        connection = None
        cursor = None
        try:
            # Mở connection MySQL.
            connection = get_connection()
            # Tạo cursor thường cho INSERT.
            cursor = connection.cursor()
            # Execute SQL với params để tránh nối chuỗi SQL thủ công.
            cursor.execute(sql, params)
            # Commit để INSERT được ghi thật vào DB.
            connection.commit()
            # lastrowid là id auto_increment vừa tạo.
            return int(cursor.lastrowid)
        except Exception as error:  # noqa: BLE001 - repository cần bắt rộng để không làm vỡ demo khi DB tắt.
            # Lưu hoặc raise lỗi tùy chế độ repository.
            self._handle_error(error)
            # Trả None để caller biết thao tác insert thất bại.
            return None
        finally:
            # Luôn đóng tài nguyên DB.
            self._close(cursor, connection)

    def _execute(self, sql: str, params: tuple[Any, ...]) -> None:
        """Chạy UPDATE/DELETE không cần trả dữ liệu."""
        # Khởi tạo None để finally đóng an toàn.
        connection = None
        cursor = None
        try:
            # Mở connection MySQL.
            connection = get_connection()
            # Tạo cursor thường cho UPDATE/DELETE.
            cursor = connection.cursor()
            # Execute SQL với params an toàn.
            cursor.execute(sql, params)
            # Commit để update/delete có hiệu lực.
            connection.commit()
        except Exception as error:  # noqa: BLE001
            # Lưu hoặc raise lỗi tùy cấu hình.
            self._handle_error(error)
        finally:
            # Đóng cursor/connection sau khi dùng.
            self._close(cursor, connection)

    def _update_document_parsing_status(self, analysis_run_id: int, parsing_status: str) -> None:
        """Cập nhật trạng thái parse/xử lý ở bảng documents theo analysis_run."""
        # Update documents thông qua join với analysis_runs để không cần truyền document_id riêng.
        sql = """
            UPDATE documents d
            JOIN analysis_runs ar ON ar.document_id = d.id
            SET d.parsing_status = %s
            WHERE ar.id = %s
        """
        # Chạy update trạng thái document.
        self._execute(sql, (parsing_status, analysis_run_id))

    def _fetch_one(self, sql: str, params: tuple[Any, ...]) -> dict[str, Any] | None:
        """Chạy SELECT lấy một dòng."""
        # Tận dụng _fetch_all để không lặp code query.
        rows = self._fetch_all(sql, params)
        # Nếu có dữ liệu thì lấy dòng đầu tiên, nếu không thì trả None.
        return rows[0] if rows else None

    def _fetch_all(self, sql: str, params: tuple[Any, ...]) -> list[dict[str, Any]]:
        """Chạy SELECT lấy nhiều dòng."""
        # Khởi tạo None để finally đóng an toàn.
        connection = None
        cursor = None
        try:
            # Mở connection MySQL.
            connection = get_connection()
            # dictionary=True để mỗi dòng trả về dạng dict thay vì tuple.
            cursor = connection.cursor(dictionary=True)
            # Execute SELECT với params.
            cursor.execute(sql, params)
            # Lấy toàn bộ dòng kết quả.
            rows = cursor.fetchall()
            # Convert Decimal/datetime/JSON string để FastAPI trả JSON được.
            return self._make_json_safe(rows)
        except Exception as error:  # noqa: BLE001
            # Lưu hoặc raise lỗi tùy cấu hình.
            self._handle_error(error)
            # Nếu không raise thì trả list rỗng để UI không crash.
            return []
        finally:
            # Đóng cursor/connection.
            self._close(cursor, connection)

    def _handle_error(self, error: Exception) -> None:
        """Lưu lỗi gần nhất; tùy chế độ có thể raise để API truy vấn báo lỗi rõ."""
        # Lưu text lỗi để debug nếu không raise.
        self.last_error = str(error)
        # Với endpoint truy vấn/xóa lịch sử, cần raise để frontend biết DB lỗi.
        if self.raise_errors:
            raise error

    @staticmethod
    def _close(cursor: Any, connection: Any) -> None:
        """Đóng cursor và connection để tránh rò rỉ kết nối MySQL."""
        # Nếu cursor đã được tạo thì đóng cursor trước.
        if cursor is not None:
            cursor.close()
        # Nếu connection đã được tạo và còn mở thì đóng connection.
        if connection is not None and connection.is_connected():
            connection.close()

    @staticmethod
    def _to_json(value: Any) -> str:
        """Chuyển dict/list/object sang JSON text để lưu vào cột JSON/LONGTEXT."""
        # Nếu là Pydantic model thì chuyển về dict trước.
        if hasattr(value, "model_dump"):
            value = value.model_dump()
        # ensure_ascii=False để giữ tiếng Việt trong JSON.
        return json.dumps(value, ensure_ascii=False, default=str)

    @classmethod
    def _make_json_safe(cls, value: Any) -> Any:
        """Chuyển Decimal/datetime/JSON string thành dạng FastAPI trả JSON được."""
        # Nếu là list thì convert từng item.
        if isinstance(value, list):
            return [cls._make_json_safe(item) for item in value]
        # Nếu là dict thì convert từng key/value.
        if isinstance(value, dict):
            return {key: cls._make_json_safe(cls._maybe_parse_json(key, item)) for key, item in value.items()}
        # Decimal không serialize JSON trực tiếp được nên đổi sang float.
        if isinstance(value, Decimal):
            return float(value)
        # datetime/date đổi sang ISO string để frontend đọc được.
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        # Các kiểu còn lại giữ nguyên.
        return value

    @staticmethod
    def _maybe_parse_json(key: str, value: Any) -> Any:
        """Parse lại các cột *_json để API trả về list/dict thay vì chuỗi JSON."""
        # Chỉ parse các cột có hậu tố _json và value là string.
        if value is None or not key.endswith("_json") or not isinstance(value, str):
            return value
        # Thử parse JSON string thành list/dict.
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            # Nếu parse fail thì giữ nguyên string để không làm mất dữ liệu.
            return value
