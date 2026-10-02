#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量更新敦煌商品信息（跑批脚本）

通过 HTTP 调用后端接口：
  POST /api/v1/common/utils/dhgate/updateproductfromfile
不在脚本内重复实现更新逻辑；服务端需已启动。

用法（在 hemu_oversea_fastapi 根目录）：
  uv run python script/batch_update_product_from_file.py [选项]

必填参数：
  --file              Excel 本地路径（.xlsx / .xlsm）
  --supplier-id       供应商 ID

常用可选参数：
  --extract-field-info
      字段映射 JSON。键=官网字段名，值=Excel 列字母。
      默认：{"itemCode":"B","grossWeight":"C","baseQt":"D","stepQt":"E","stepWeight":"F"}
  --start-row         起始行号（1 起，默认 2，跳过表头）
  --total-rows        计划处理的总行数（从 start-row 起算；0=一直跑到无有效数据，默认 0）
  --batch-size        每批提交行数（默认 10；接口单次最多 50，超过会自动截断为 50）
  --sheet-index       工作表索引（默认 1；0=全部 sheet）
  --dry-run           试跑：不写敦煌 / 不落库 / 不记日志（开关，默认关闭）
  --operator-id       操作人用户 ID（默认 0=系统）
  --base-url          服务根地址（默认 http://127.0.0.1:8600）
  --timeout           单批 HTTP 超时秒数（默认 600）

示例：
  # 本地阶梯计重表：第 4 个 sheet，有表头，供应商 4，共 12 条、每批 10 条
  uv run python script/batch_update_product_from_file.py --file "E:\\personal\\projects\\HeMuOversea\\相关资料\\佣金率-折扣-价格表-阶梯计重表.xlsx" --supplier-id 4 --sheet-index 4 --start-row 2 --total-rows 12 --batch-size 10 --base-url http://127.0.0.1:8600

  # 试跑（不写敦煌 / 不落库）：
  uv run python script/batch_update_product_from_file.py --file "E:\\personal\\projects\\HeMuOversea\\相关资料\\佣金率-折扣-价格表-阶梯计重表.xlsx" --supplier-id 4 --sheet-index 4 --start-row 2 --total-rows 12 --batch-size 10 --dry-run --base-url http://127.0.0.1:8600
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import httpx

_API_PATH = "/api/v1/common/utils/dhgate/updateproductfromfile"
_DEFAULT_FIELD_MAP = (
    '{"itemCode":"B","grossWeight":"C","baseQt":"D","stepQt":"E","stepWeight":"F"}'
)
_MAX_API_BATCH = 50
_EMPTY_HINT = "未解析到有效数据行"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="分批调用 updateproductfromfile 批量更新敦煌商品",
    )
    parser.add_argument(
        "--file",
        required=True,
        help="Excel 本地路径（.xlsx / .xlsm）",
    )
    parser.add_argument(
        "--supplier-id",
        type=int,
        required=True,
        help="供应商 ID",
    )
    parser.add_argument(
        "--extract-field-info",
        default=_DEFAULT_FIELD_MAP,
        help='字段映射 JSON，如 {"itemCode":"B","grossWeight":"C",...}',
    )
    parser.add_argument(
        "--start-row",
        type=int,
        default=2,
        help="起始行号（1 起，默认 2）",
    )
    parser.add_argument(
        "--total-rows",
        type=int,
        default=0,
        help="计划处理总行数（从 start-row 起；0=直到无有效数据）",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help=f"每批行数（默认 10，最大 {_MAX_API_BATCH}）",
    )
    parser.add_argument(
        "--sheet-index",
        type=int,
        default=1,
        help="工作表索引（默认 1；0=全部 sheet）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="试跑模式",
    )
    parser.add_argument(
        "--operator-id",
        type=int,
        default=0,
        help="操作人用户 ID（默认 0）",
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8600",
        help="服务根地址",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=600.0,
        help="单批请求超时秒数（默认 600）",
    )
    return parser.parse_args()


def _validate_args(args: argparse.Namespace) -> Path:
    path = Path(args.file).expanduser().resolve()
    if not path.is_file():
        raise SystemExit(f"文件不存在：{path}")
    if path.suffix.lower() not in {".xlsx", ".xlsm"}:
        raise SystemExit("仅支持 .xlsx / .xlsm")
    if args.start_row < 1:
        raise SystemExit("--start-row 须 >= 1")
    if args.total_rows < 0:
        raise SystemExit("--total-rows 须 >= 0")
    if args.batch_size < 1:
        raise SystemExit("--batch-size 须 >= 1")
    if args.sheet_index < 0:
        raise SystemExit("--sheet-index 须 >= 0")
    if args.supplier_id < 1:
        raise SystemExit("--supplier-id 须 >= 1")
    try:
        mapping = json.loads(args.extract_field_info)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"--extract-field-info 不是合法 JSON：{exc}") from exc
    if not isinstance(mapping, dict) or not mapping:
        raise SystemExit("--extract-field-info 须为非空 JSON 对象")
    return path


def _format_seconds(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes, sec = divmod(seconds, 60)
    if minutes < 60:
        return f"{int(minutes)}m{sec:04.1f}s"
    hours, minutes = divmod(int(minutes), 60)
    return f"{hours}h{minutes}m{sec:04.1f}s"


def _call_update_from_file(
    *,
    client: httpx.Client,
    url: str,
    file_path: Path,
    extract_field_info: str,
    start_row: int,
    row_count: int,
    sheet_index: int,
    supplier_id: int,
    dry_run: bool,
    operator_id: int,
) -> dict[str, Any]:
    with file_path.open("rb") as fp:
        files = {
            "file": (
                file_path.name,
                fp,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        }
        data = {
            "extract_field_info": extract_field_info,
            "start_row": str(start_row),
            "row_count": str(row_count),
            "sheet_index": str(sheet_index),
            "supplier_id": str(supplier_id),
            "dry_run": "true" if dry_run else "false",
            "operator_id": str(operator_id),
        }
        response = client.post(url, data=data, files=files)

    try:
        body = response.json()
    except ValueError as exc:
        raise RuntimeError(
            f"HTTP {response.status_code} 响应非 JSON：{response.text[:500]}"
        ) from exc

    if response.status_code >= 400:
        message = ""
        if isinstance(body, dict):
            message = str(body.get("message") or body.get("detail") or "")
        raise RuntimeError(
            f"HTTP {response.status_code}: {message or response.text[:500]}"
        )

    if not isinstance(body, dict):
        raise RuntimeError(f"响应格式异常：{body!r}")
    if int(body.get("code") or 0) != 0:
        raise RuntimeError(str(body.get("message") or "接口返回失败"))
    data = body.get("data")
    if not isinstance(data, dict):
        raise RuntimeError("响应缺少 data")
    return data


def _is_empty_batch_error(exc: Exception) -> bool:
    return _EMPTY_HINT in str(exc)


def main() -> int:
    args = _parse_args()
    file_path = _validate_args(args)

    batch_size = min(int(args.batch_size), _MAX_API_BATCH)
    if int(args.batch_size) > _MAX_API_BATCH:
        print(
            f"[warn] --batch-size={args.batch_size} 超过接口上限 "
            f"{_MAX_API_BATCH}，已按 {_MAX_API_BATCH} 执行"
        )

    base_url = str(args.base_url).rstrip("/")
    url = f"{base_url}{_API_PATH}"
    total_limit = int(args.total_rows)
    cursor = int(args.start_row)

    print("=" * 60)
    print("敦煌商品批量更新跑批")
    print(f"  file          = {file_path}")
    print(f"  supplier_id   = {args.supplier_id}")
    print(f"  field_map     = {args.extract_field_info}")
    print(f"  start_row     = {args.start_row}")
    print(f"  total_rows    = {total_limit or '不限（直到无有效数据）'}")
    print(f"  batch_size    = {batch_size}")
    print(f"  sheet_index   = {args.sheet_index}")
    print(f"  dry_run       = {bool(args.dry_run)}")
    print(f"  operator_id   = {args.operator_id}")
    print(f"  url           = {url}")
    print("=" * 60)

    total_success = 0
    total_failed = 0
    total_valid = 0
    total_skipped = 0
    batch_index = 0
    job_started = time.perf_counter()

    with httpx.Client(timeout=args.timeout) as client:
        while True:
            remaining = None
            if total_limit > 0:
                consumed = cursor - int(args.start_row)
                remaining = total_limit - consumed
                if remaining <= 0:
                    break
            this_count = batch_size if remaining is None else min(batch_size, remaining)
            batch_index += 1
            batch_started = time.perf_counter()
            print(
                f"\n[batch {batch_index}] start_row={cursor} "
                f"row_count={this_count} ..."
            )

            try:
                data = _call_update_from_file(
                    client=client,
                    url=url,
                    file_path=file_path,
                    extract_field_info=args.extract_field_info,
                    start_row=cursor,
                    row_count=this_count,
                    sheet_index=args.sheet_index,
                    supplier_id=args.supplier_id,
                    dry_run=bool(args.dry_run),
                    operator_id=args.operator_id,
                )
            except Exception as exc:
                elapsed = time.perf_counter() - batch_started
                if _is_empty_batch_error(exc):
                    print(
                        f"[batch {batch_index}] 无有效数据，结束跑批 "
                        f"（用时 {_format_seconds(elapsed)}）"
                    )
                    print(f"  reason: {exc}")
                    break
                print(
                    f"[batch {batch_index}] 失败 "
                    f"（用时 {_format_seconds(elapsed)}）"
                )
                print(f"  error: {exc}")
                # 本批失败仍推进游标，避免死循环卡在同一段
                cursor += this_count
                continue

            extract = data.get("extract") if isinstance(data.get("extract"), dict) else {}
            update = data.get("update") if isinstance(data.get("update"), dict) else {}
            valid_count = int(extract.get("valid_count") or 0)
            skipped_count = int(extract.get("skipped_count") or 0)
            success_count = int(update.get("success_count") or 0)
            failed_count = int(update.get("failed_count") or 0)
            failed_items = update.get("failed_items") or []

            total_valid += valid_count
            total_skipped += skipped_count
            total_success += success_count
            total_failed += failed_count

            elapsed = time.perf_counter() - batch_started
            print(
                f"[batch {batch_index}] 完成 "
                f"valid={valid_count} skipped={skipped_count} "
                f"success={success_count} failed={failed_count} "
                f"用时={_format_seconds(elapsed)}"
            )
            if isinstance(failed_items, list) and failed_items:
                preview = failed_items[:5]
                for item in preview:
                    if not isinstance(item, dict):
                        continue
                    print(
                        f"  - fail itemCode={item.get('itemCode')} "
                        f"err={item.get('error_message')}"
                    )
                if len(failed_items) > 5:
                    print(f"  ... 另有 {len(failed_items) - 5} 条失败明细未展开")

            cursor += this_count
            if valid_count <= 0:
                print(f"[batch {batch_index}] 本批无有效行，结束跑批")
                break

    job_elapsed = time.perf_counter() - job_started
    print("\n" + "=" * 60)
    print("全部批次结束")
    print(f"  batches       = {batch_index}")
    print(f"  valid_total   = {total_valid}")
    print(f"  skipped_total = {total_skipped}")
    print(f"  success_total = {total_success}")
    print(f"  failed_total  = {total_failed}")
    print(f"  elapsed       = {_format_seconds(job_elapsed)}")
    print("=" * 60)
    return 0 if total_failed == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
