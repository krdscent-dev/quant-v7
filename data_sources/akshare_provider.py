"""AkShare data provider adapter.

This module provides a thin adapter around AkShare for A-share data
integration. It keeps the provider/source boundary separate from the
factor and scoring layers.

If AkShare is unavailable or a request fails, the provider falls back
to structured mock-shaped payloads so downstream code remains stable.
"""

from __future__ import annotations

from typing import Any, Mapping

from data_sources.mock_provider import MockDataProvider

from data_sources.base import DataProvider

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

    def _code_variants(self, code: str) -> list[str]:
        plain = code.split(".")[0]
        return [code, plain, plain.zfill(6), f"sh{plain}" if code.endswith(".SH") or plain.startswith("6") else f"sz{plain}"]

    def _find_first_success(self, candidates: list[tuple[str, Any]]) -> tuple[str, Any] | None:
        for label, value in candidates:
            try:
                if value is None:
                    continue
                return label, value
            except Exception:
                continue
        return None

    def get_company_basic_info(self, code: str) -> Mapping[str, Any]:
        def _fetch() -> Mapping[str, Any]:
            company_code = code.split(".")[0]
            name = ""
            industry = ""
            concept = ""
            listed_name = ""

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

            if not name:
                try:
                    all_df = ak.stock_info_a_code_name()
                    code_col = "code" if "code" in all_df.columns else all_df.columns[0]
                    name_col = "name" if "name" in all_df.columns else all_df.columns[1]
                    matched = all_df[all_df[code_col].astype(str).str.contains(company_code, na=False)]
                    if not matched.empty:
                        listed_name = str(matched.iloc[0][name_col])
                except Exception:
                    pass

            if not name:
                name = listed_name

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
            revenue = None
            net_profit = None
            roe = None

            financial_calls = [
                lambda: ak.stock_financial_analysis_indicator_em(symbol=company_code),
                lambda: ak.stock_financial_abstract(symbol=company_code),
                lambda: ak.stock_profit_sheet_by_yearly_em(symbol=company_code),
                lambda: ak.stock_profit_sheet_by_report_em(symbol=company_code),
            ]

            for call in financial_calls:
                try:
                    df = call()
                    if df is None or getattr(df, "empty", True):
                        continue
                    columns = {str(col): col for col in df.columns}
                    lower_columns = {str(col).lower(): col for col in df.columns}

                    def pick(*names: str) -> Any:
                        for name in names:
                            key = name.lower()
                            if key in lower_columns:
                                series = df.iloc[0][lower_columns[key]]
                                return series
                        return None

                    revenue = pick("营业收入", "营业总收入", "营业收入(元)", "revenue")
                    net_profit = pick("净利润", "归母净利润", "net_profit")
                    roe = pick("ROE", "净资产收益率", "roe")
                    if revenue is not None or net_profit is not None or roe is not None:
                        break
                except Exception:
                    continue

            if revenue is None or net_profit is None or roe is None:
                fallback = self._mock.get_financial_summary(code)
                revenue_growth = float(fallback.get("revenue_growth", 0.0))
                return {
                    "code": code,
                    "source": "akshare",
                    "available": False,
                    "status": "akshare_fallback_to_mock",
                    "营业收入": 0.0,
                    "净利润": 0.0,
                    "ROE": 0.0,
                    "revenue_growth": revenue_growth,
                    "gross_margin": float(fallback.get("gross_margin", 0.0)),
                    "rd_expense_ratio": float(fallback.get("rd_expense_ratio", 0.0)),
                    "capex_signal": 0.0,
                    "message": "AkShare financial data unavailable; fallback to mock-shaped summary.",
                }

            return {
                "code": code,
                "source": "akshare",
                "available": True,
                "status": "adapter_ready",
                "营业收入": revenue,
                "净利润": net_profit,
                "ROE": roe,
                "revenue_growth": 0.0,
                "gross_margin": 0.0,
                "rd_expense_ratio": 0.0,
                "capex_signal": 0.0,
                "message": "AkShare financial summary mapped from financial report endpoints.",
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
