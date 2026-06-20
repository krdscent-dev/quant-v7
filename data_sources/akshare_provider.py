"""AkShare data provider adapter.

This module provides a thin adapter around AkShare for A-share data
integration. It keeps the provider/source boundary separate from the
factor and scoring layers.

If AkShare is unavailable or a request fails, the provider falls back
to structured mock-shaped payloads so downstream code remains stable.
"""

from __future__ import annotations

from typing import Any, Mapping

from data_sources.base import DataProvider
from data_sources.mock_provider import MockDataProvider

try:  # pragma: no cover - optional dependency
    import akshare as ak
except ImportError:  # pragma: no cover - optional dependency
    ak = None


class AkShareDataProvider(DataProvider):
    """AkShare-backed data provider adapter."""

    def __init__(self) -> None:
        self.akshare_available = ak is not None
        self._mock = MockDataProvider()

    def _unavailable_payload(self, code: str, method: str) -> Mapping[str, Any]:
        return {
            "code": code,
            "source": "akshare",
            "available": False,
            "status": "akshare_not_installed",
            "method": method,
            "message": "akshare is not installed; returning adapter placeholder data.",
        }

    def _fallback_payload(self, code: str, method: str, reason: str) -> Mapping[str, Any]:
        payload = dict(getattr(self._mock, method)(code))
        payload.update(
            {
                "source": "akshare",
                "available": False,
                "status": "akshare_fallback_to_mock",
                "method": method,
                "fallback_reason": reason,
            }
        )
        return payload

    def _safe_call(self, code: str, method: str, fn: Any) -> Mapping[str, Any]:
        if ak is None:
            return self._fallback_payload(code, method, "akshare_not_installed")
        try:
            return fn()
        except Exception as exc:  # pragma: no cover - network/runtime dependent
            return self._fallback_payload(code, method, f"{type(exc).__name__}: {exc}")

    def _extract_first_value(self, frame: Any, names: list[str]) -> Any:
        if frame is None or getattr(frame, "empty", True):
            return None
        columns = {str(col).lower(): col for col in frame.columns}
        for name in names:
            key = name.lower()
            if key in columns:
                value = frame.iloc[0][columns[key]]
                if value is not None and str(value).strip() != "":
                    return value
        return None

    def get_company_basic_info(self, code: str) -> Mapping[str, Any]:
        def _fetch() -> Mapping[str, Any]:
            company_code = code.split(".")[0]
            name = ""
            industry = ""
            concept = ""
            try:
                info_df = ak.stock_individual_info_em(symbol=company_code)
                info_map = {
                    str(row.get("item", "")).strip(): str(row.get("value", "")).strip()
                    for _, row in info_df.iterrows()
                }
                name = info_map.get("股票名称") or info_map.get("股票简称") or info_map.get("公司名称") or ""
                industry = info_map.get("所属行业") or info_map.get("行业") or ""
                concept = info_map.get("所属概念") or info_map.get("概念") or ""
            except Exception:
                pass

            if not name or not industry:
                try:
                    all_df = ak.stock_info_a_code_name()
                    code_col = "code" if "code" in all_df.columns else all_df.columns[0]
                    name_col = "name" if "name" in all_df.columns else all_df.columns[1]
                    matched = all_df[all_df[code_col].astype(str).str.contains(company_code, na=False)]
                    if not matched.empty and not name:
                        name = str(matched.iloc[0][name_col])
                except Exception:
                    pass

            if not name or not industry:
                fallback = self._mock.get_company_basic_info(code)
                if not name:
                    name = str(fallback.get("name", ""))
                if not industry:
                    industry = str(fallback.get("industry", ""))

            return {
                "code": code,
                "source": "akshare",
                "available": True,
                "status": "adapter_ready",
                "stock_code": company_code,
                "stock_name": name or "",
                "name": name or "",
                "industry": industry or "",
                "concept": concept or "",
                "listing_status": "listed",
                "message": "AkShare company basic info mapped from stock profile endpoints.",
            }

        return self._safe_call(code, "get_company_basic_info", _fetch)

    def get_financial_summary(self, code: str) -> Mapping[str, Any]:
        def _fetch() -> Mapping[str, Any]:
            company_code = code.split(".")[0]
            raw_financial_fields: dict[str, list[str]] = {}
            mapped_financial_summary: dict[str, Any] = {
                "营业收入": None,
                "净利润": None,
                "ROE": None,
                "毛利率": None,
                "营收同比": None,
                "净利润同比": None,
            }

            endpoint_specs = [
                (
                    "stock_financial_analysis_indicator_em",
                    lambda: ak.stock_financial_analysis_indicator_em(symbol=company_code),
                    ["营业收入", "营业总收入", "主营业务收入", "营收"],
                ),
                (
                    "stock_financial_abstract",
                    lambda: ak.stock_financial_abstract(symbol=company_code),
                    ["营业收入", "净利润", "毛利率", "ROE", "营收同比", "净利润同比"],
                ),
                (
                    "stock_financial_abstract_ths",
                    lambda: ak.stock_financial_abstract_ths(symbol=company_code),
                    ["营业收入", "净利润", "毛利率", "ROE"],
                ),
                (
                    "stock_financial_analysis_indicator",
                    lambda: ak.stock_financial_analysis_indicator(symbol=company_code),
                    ["营业收入", "净利润", "ROE", "毛利率"],
                ),
                (
                    "stock_profit_sheet_by_report_em",
                    lambda: ak.stock_profit_sheet_by_report_em(symbol=company_code),
                    ["营业收入", "净利润", "营业收入同比", "净利润同比"],
                ),
                (
                    "stock_profit_sheet_by_yearly_em",
                    lambda: ak.stock_profit_sheet_by_yearly_em(symbol=company_code),
                    ["营业收入", "净利润"],
                ),
            ]

            for endpoint_name, call, field_names in endpoint_specs:
                try:
                    frame = call()
                except Exception:
                    continue
                if frame is None or getattr(frame, "empty", True):
                    continue
                raw_financial_fields[endpoint_name] = [str(col) for col in frame.columns]
                for field_name in field_names:
                    if mapped_financial_summary[field_name] is not None:
                        continue
                    value = self._extract_first_value(
                        frame,
                        [
                            field_name,
                            field_name.replace("同比", "增长"),
                            field_name.replace("ROE", "净资产收益率"),
                            field_name.replace("营业收入", "营收"),
                            field_name.replace("净利润", "归母净利润"),
                        ],
                    )
                    if value is not None:
                        mapped_financial_summary[field_name] = value

            mock_summary = self._mock.get_financial_summary(code)
            missing_fields = [field for field, value in mapped_financial_summary.items() if value is None]
            status = "adapter_ready" if not missing_fields else "partial_data"
            available = len(missing_fields) == 0

            def to_float(value: Any, default: float = 0.0) -> float:
                if value is None:
                    return default
                try:
                    return float(value)
                except Exception:
                    return default

            revenue_growth = to_float(mapped_financial_summary["营收同比"], float(mock_summary.get("revenue_growth", 0.0)))
            gross_margin = to_float(mapped_financial_summary["毛利率"], float(mock_summary.get("gross_margin", 0.0)))

            return {
                "code": code,
                "source": "akshare",
                "available": available,
                "status": status,
                "stock_code": company_code,
                "营业收入": mapped_financial_summary["营业收入"],
                "净利润": mapped_financial_summary["净利润"],
                "ROE": mapped_financial_summary["ROE"],
                "毛利率": mapped_financial_summary["毛利率"],
                "营收同比": mapped_financial_summary["营收同比"],
                "净利润同比": mapped_financial_summary["净利润同比"],
                "revenue_growth": revenue_growth,
                "gross_margin": gross_margin,
                "rd_expense_ratio": float(mock_summary.get("rd_expense_ratio", 0.0)),
                "capex_signal": 0.0,
                "raw_financial_fields": raw_financial_fields,
                "mapped_financial_summary": mapped_financial_summary,
                "missing_fields": missing_fields,
                "message": "AkShare financial summary mapped with field-level fallback.",
            }

        return self._safe_call(code, "get_financial_summary", _fetch)

    def get_order_signals(self, code: str) -> Mapping[str, Any]:
        if ak is None:
            return self._unavailable_payload(code, "get_order_signals")
        return {
            "code": code,
            "source": "akshare",
            "available": True,
            "status": "adapter_ready",
            "order_landing_score": 0.0,
            "revenue_confirmation_score": 0.0,
            "customer_validation_score": 0.0,
            "story_to_earnings_score": 0.0,
            "message": "Order signal mapping placeholder for future data sources.",
        }

    def get_news_signals(self, code: str) -> Mapping[str, Any]:
        if ak is None:
            return self._unavailable_payload(code, "get_news_signals")
        return {
            "code": code,
            "source": "akshare",
            "available": True,
            "status": "adapter_ready",
            "headline_count": 0,
            "positive_news_ratio": 0.0,
            "negative_news_ratio": 0.0,
            "guidance_signal": 0.0,
            "message": "News signal mapping placeholder for future AkShare integration.",
        }

    def get_theme_signals(self, code: str) -> Mapping[str, Any]:
        if ak is None:
            return self._unavailable_payload(code, "get_theme_signals")
        return {
            "code": code,
            "source": "akshare",
            "available": True,
            "status": "adapter_ready",
            "tau_factor_score": 0.0,
            "ascend_ecosystem_exposure": 0.0,
            "domestic_substitution_exposure": 0.0,
            "advanced_packaging_exposure": 0.0,
            "advanced_material_exposure": 0.0,
            "message": "Theme mapping placeholder for future factor contract alignment.",
        }
