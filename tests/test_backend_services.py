from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"

for path in (ROOT_DIR, BACKEND_DIR):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import models  # noqa: F401
from database import Base, get_db
from routers import exports, inventory
from schemas import InventorySetup, RecordExpenseArgs, RecordPurchaseArgs, RecordSaleArgs, normalize_item_name
from services.gemma_service import GemmaService
from services.inventory_service import InventoryService
from services.ledger_service import LedgerService
from services.report_service import ReportService
from services.rule_extraction_service import RuleExtractionService
from services.template_service import TemplateService


class AsyncDatabaseTestCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test.sqlite3"
        self.engine = create_async_engine(
            f"sqlite+aiosqlite:///{self.db_path}",
            connect_args={"check_same_thread": False},
        )
        self.session_factory = async_sessionmaker(
            self.engine,
            expire_on_commit=False,
            autoflush=True,
        )
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.session = self.session_factory()

    async def asyncTearDown(self) -> None:
        await self.session.close()
        await self.engine.dispose()
        self.temp_dir.cleanup()


class LedgerAndReportingTests(AsyncDatabaseTestCase):
    async def test_item_normalization_collapses_plural_aliases(self) -> None:
        self.assertEqual(normalize_item_name("plantain"), "plantains")
        self.assertEqual(normalize_item_name("plantains"), "plantains")
        self.assertEqual(normalize_item_name("bean"), "beans")

    async def test_purchase_normalizes_item_and_updates_inventory(self) -> None:
        ledger = LedgerService(self.session)
        inventory_service = InventoryService(self.session)

        result = await ledger.record_purchase(
            RecordPurchaseArgs(
                item="shinkafa",
                quantity=2,
                unit="bag",
                unit_price=120,
                supplier="Kofi",
                currency="cedis",
            ),
            language="tw",
            raw_input="Metoo shinkafa bag 2 a 120 cedis",
        )

        inventory = await inventory_service.get_item("rice")
        self.assertIsNotNone(inventory)
        self.assertEqual(result["item"], "rice")
        self.assertEqual(result["unit"], "bags")
        self.assertEqual(result["currency"], "GHS")
        self.assertEqual(result["new_stock_level"], 2.0)
        self.assertEqual(inventory.quantity, 2.0)
        self.assertEqual(inventory.unit, "bags")
        self.assertEqual(inventory.last_purchase_price, 120)

    async def test_sale_flags_low_stock_and_computes_profit(self) -> None:
        ledger = LedgerService(self.session)
        inventory_service = InventoryService(self.session)

        await ledger.record_purchase(
            RecordPurchaseArgs(
                item="rice",
                quantity=5,
                unit="bags",
                unit_price=100,
                supplier="Abena",
                currency="GHS",
            )
        )
        await inventory_service.update_threshold("rice", 2)

        sale_result = await ledger.record_sale(
            RecordSaleArgs(
                item="rice",
                quantity=4,
                unit="bags",
                sale_price=150,
                customer="Maame",
                currency="GHS",
            )
        )

        inventory = await inventory_service.get_item("rice")
        self.assertEqual(sale_result["remaining_stock"], 1.0)
        self.assertTrue(sale_result["low_stock_warning"])
        self.assertFalse(sale_result["out_of_stock"])
        self.assertEqual(sale_result["profit"], 200.0)
        self.assertIsNotNone(inventory)
        self.assertEqual(inventory.last_sale_price, 150)

    async def test_sales_first_inventory_pricing_infers_quantity_from_amount(self) -> None:
        inventory_service = InventoryService(self.session)
        ledger = LedgerService(self.session)

        await inventory_service.setup_item(
            InventorySetup(
                item="borɔdeɛ",
                quantity=40,
                unit="pieces",
                sale_price_amount=8,
                sale_price_quantity=4,
                avg_cost=1,
                low_stock_threshold=5,
            )
        )

        sale_result = await ledger.record_sale(
            RecordSaleArgs(
                item="plantains",
                quantity=1,
                unit="lot",
                sale_price=8,
                currency="GHS",
            )
        )

        inventory = await inventory_service.get_item("plantains")
        self.assertEqual(sale_result["quantity"], 4.0)
        self.assertEqual(sale_result["unit"], "pieces")
        self.assertEqual(sale_result["sale_price"], 2.0)
        self.assertEqual(sale_result["total_amount"], 8.0)
        self.assertIsNotNone(inventory)
        self.assertEqual(inventory.quantity, 36.0)

    async def test_daily_summary_and_credit_profile_are_consistent(self) -> None:
        ledger = LedgerService(self.session)
        report_service = ReportService(self.session)

        await ledger.record_purchase(
            RecordPurchaseArgs(
                item="onions",
                quantity=10,
                unit="kg",
                unit_price=5,
                supplier="Makola Wholesale",
                currency="GHS",
            )
        )
        await ledger.record_sale(
            RecordSaleArgs(
                item="onions",
                quantity=4,
                unit="kg",
                sale_price=10,
                customer="Kojo",
                currency="GHS",
            )
        )
        await ledger.record_expense(
            RecordExpenseArgs(
                category="transport",
                amount=20,
                description="transport to market",
                currency="GHS",
            )
        )

        summary = await report_service.daily_summary()
        credit_profile = await report_service.export_credit_profile(30)

        self.assertEqual(summary["total_revenue"], 40.0)
        self.assertEqual(summary["total_cost"], 50.0)
        self.assertEqual(summary["total_expenses"], 20.0)
        self.assertEqual(summary["net_profit"], -30.0)
        self.assertEqual(summary["top_selling_item"], "onions")
        self.assertEqual(summary["top_selling_quantity"], 4.0)
        self.assertGreaterEqual(credit_profile["active_days"], 1)
        self.assertEqual(credit_profile["total_transactions"], 3)

    async def test_template_service_falls_back_to_english(self) -> None:
        templates = TemplateService(BACKEND_DIR / "templates")
        rendered = templates.get_response(
            "purchase_confirmed",
            "missing-language",
            {
                "quantity": 2,
                "unit": "bags",
                "item": "rice",
                "currency": "GHS",
                "total_amount": 240.0,
                "new_stock_level": 10.0,
            },
        )
        self.assertIn("Recorded.", rendered)
        self.assertIn("rice", rendered)


class GemmaFallbackTests(AsyncDatabaseTestCase):
    async def test_known_twi_purchase_uses_rule_fallback_without_waiting_for_model(self) -> None:
        service = GemmaService(self.session)

        async def fake_extraction_pass(_messages):
            raise AssertionError("Known deterministic phrases should not wait for Gemma.")

        service._run_extraction_pass = fake_extraction_pass
        try:
            response, transactions, calls = await service.chat("mereto gyeene 10 GHS", language="tw")
        finally:
            await service.close()

        self.assertEqual(len(transactions), 1)
        self.assertEqual(transactions[0].item, "onions")
        self.assertEqual(calls[0].name, "record_purchase")
        self.assertIn("onions", response)


class RuleExtractionTests(unittest.TestCase):
    def test_twi_onion_purchase_uses_safe_defaults(self) -> None:
        extractor = RuleExtractionService()

        calls = extractor.extract("mereto gyeene 10 GHS")

        self.assertEqual(len(calls), 1)
        function = calls[0]["function"]
        self.assertEqual(function["name"], "record_purchase")
        self.assertEqual(
            function["arguments"],
            {
                "item": "onions",
                "quantity": 1.0,
                "unit": "lot",
                "currency": "GHS",
                "unit_price": 10.0,
            },
        )

    def test_twi_asr_gyeene_mishearing_still_maps_to_onions(self) -> None:
        extractor = RuleExtractionService()

        calls = extractor.extract("me to j ne 10 GHS")

        self.assertEqual(calls[0]["function"]["name"], "record_purchase")
        self.assertEqual(calls[0]["function"]["arguments"]["item"], "onions")

    def test_twi_plantain_purchase_accepts_native_and_keyboard_spellings(self) -> None:
        extractor = RuleExtractionService()

        native_calls = extractor.extract("meretɔ borɔdeɛ 8 cedis")
        keyboard_calls = extractor.extract("mereto bor)de3 8 cedis")

        for calls in (native_calls, keyboard_calls):
            self.assertEqual(calls[0]["function"]["name"], "record_purchase")
            self.assertEqual(calls[0]["function"]["arguments"]["item"], "plantains")
            self.assertEqual(calls[0]["function"]["arguments"]["quantity"], 1.0)
            self.assertEqual(calls[0]["function"]["arguments"]["unit"], "lot")
            self.assertEqual(calls[0]["function"]["arguments"]["unit_price"], 8.0)

    def test_twi_purchase_with_explicit_quantity_and_total_calculates_unit_price(self) -> None:
        extractor = RuleExtractionService()

        calls = extractor.extract("meretɔ borɔdeɛ 4 bunches total 80 cedis")

        self.assertEqual(calls[0]["function"]["name"], "record_purchase")
        self.assertEqual(calls[0]["function"]["arguments"]["item"], "plantains")
        self.assertEqual(calls[0]["function"]["arguments"]["quantity"], 4.0)
        self.assertEqual(calls[0]["function"]["arguments"]["unit"], "bunches")
        self.assertEqual(calls[0]["function"]["arguments"]["unit_price"], 20.0)

    def test_twi_group_purchase_and_person_sale_markers_work(self) -> None:
        extractor = RuleExtractionService()

        purchase_calls = extractor.extract("yɛtɔ borɔdeɛ 2 GHS")
        sale_calls = extractor.extract("obi atɔ borɔdeɛ 2 GHS")

        self.assertEqual(purchase_calls[0]["function"]["name"], "record_sale")
        self.assertEqual(purchase_calls[0]["function"]["arguments"]["item"], "plantains")
        self.assertEqual(purchase_calls[0]["function"]["arguments"]["sale_price"], 2.0)
        self.assertEqual(sale_calls[0]["function"]["name"], "record_sale")
        self.assertEqual(sale_calls[0]["function"]["arguments"]["item"], "plantains")
        self.assertEqual(sale_calls[0]["function"]["arguments"]["sale_price"], 2.0)

    def test_item_and_amount_defaults_to_sale_in_sales_first_mode(self) -> None:
        extractor = RuleExtractionService()

        calls = extractor.extract("borɔdeɛ 8 cedis")

        self.assertEqual(calls[0]["function"]["name"], "record_sale")
        self.assertEqual(calls[0]["function"]["arguments"]["item"], "plantains")
        self.assertEqual(calls[0]["function"]["arguments"]["sale_price"], 8.0)


class ExportRouterTests(AsyncDatabaseTestCase):
    async def asyncSetUp(self) -> None:
        await super().asyncSetUp()
        ledger = LedgerService(self.session)
        await ledger.record_purchase(
            RecordPurchaseArgs(
                item="rice",
                quantity=3,
                unit="bags",
                unit_price=120,
                supplier="Kofi",
                currency="GHS",
            ),
            raw_input="Bought 3 bags of rice from Kofi",
        )
        await self.session.commit()

    async def test_csv_and_backup_exports_work(self) -> None:
        app = FastAPI()
        app.include_router(exports.router)

        async def override_get_db():
            async with self.session_factory() as session:
                try:
                    yield session
                    await session.commit()
                except Exception:
                    await session.rollback()
                    raise

        app.dependency_overrides[get_db] = override_get_db

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            csv_response = await client.get("/api/export/transactions.csv")
            self.assertEqual(csv_response.status_code, 200)
            self.assertIn("text/csv", csv_response.headers["content-type"])
            self.assertIn("rice", csv_response.text)

            backup_response = await client.get("/api/export/backup.json")
            self.assertEqual(backup_response.status_code, 200)
            payload = json.loads(backup_response.text)
            self.assertEqual(payload["counts"]["transactions"], 1)
            self.assertIn("inventory", payload)
            self.assertNotIn("raw_input", payload["transactions"][0])


class InventoryRouterTests(AsyncDatabaseTestCase):
    async def test_setup_endpoint_creates_price_rule(self) -> None:
        app = FastAPI()
        app.include_router(inventory.router)

        async def override_get_db():
            async with self.session_factory() as session:
                try:
                    yield session
                    await session.commit()
                except Exception:
                    await session.rollback()
                    raise

        app.dependency_overrides[get_db] = override_get_db

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            response = await client.post(
                "/api/inventory/setup",
                json={
                    "item": "borɔdeɛ",
                    "quantity": 40,
                    "unit": "pieces",
                    "sale_price_amount": 8,
                    "sale_price_quantity": 4,
                },
            )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["item"], "plantains")
        self.assertEqual(payload["sale_price_amount"], 8)
        self.assertEqual(payload["sale_price_quantity"], 4)


class ApplicationSecurityTests(unittest.IsolatedAsyncioTestCase):
    async def test_root_sets_security_headers_and_request_id(self) -> None:
        from main import create_app

        async with AsyncClient(
            transport=ASGITransport(app=create_app()),
            base_url="http://testserver",
        ) as client:
            response = await client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["x-content-type-options"], "nosniff")
        self.assertEqual(response.headers["x-frame-options"], "DENY")
        self.assertIn("x-request-id", response.headers)


if __name__ == "__main__":
    unittest.main()
