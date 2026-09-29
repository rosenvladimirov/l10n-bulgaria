# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import importlib.util
from collections import OrderedDict
from pathlib import Path

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon

from ..controllers.main import MyPosController
from .test_signature import _generate_keypair


@tagged("post_install", "-at_install")
class TestMyPosProcessFlow(PaymentHttpCommon):
    """Пътят, по който реално идва плащането в o19: HTTP → `_process`.

    Старите тестове викат `_apply_updates` директно и затова не хванаха, че
    контролерът вика несъществуващия `_handle_notification_data`, а сумата
    се проверява с подразбиращия се `_extract_amount_data` (KeyError).
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        priv_pem, cert_pem = _generate_keypair()
        cls.mypos = cls._prepare_provider(
            "mypos",
            update_values={
                "mypos_sid": "000000000000010",
                "mypos_wallet": "61938166610",
                "mypos_key_index": 1,
                "mypos_private_key": priv_pem,
                "mypos_public_cert": cert_pem,
            },
        )
        cls.provider = cls.mypos
        cls.currency = cls.currency_euro
        cls.payment_method_id = cls.env.ref("payment.payment_method_card").id

    def _notification(self, tx, **overrides):
        fields = OrderedDict(
            [
                ("IPCmethod", "IPCPurchaseNotify"),
                ("OrderID", tx.reference),
                ("Status", "0"),
                ("IPC_Trnref", "MYPOS-TXREF-1"),
                ("Amount", f"{tx.amount:.2f}"),
                ("Currency", tx.currency_id.name),
            ]
        )
        fields.update(overrides)
        fields["Signature"] = self.mypos._mypos_sign(fields)
        return dict(fields)

    def test_redirect_form_is_rendered(self):
        tx = self._create_transaction(flow="redirect")
        with mute_logger("odoo.addons.payment.models.payment_transaction"):
            processing_values = tx._get_processing_values()
        self.assertTrue(
            processing_values.get("redirect_form_html"),
            "Without redirect_form_view_id the customer is never sent to myPOS",
        )
        form = self._extract_values_from_html_form(
            processing_values["redirect_form_html"]
        )
        self.assertEqual(form["action"], self.mypos._mypos_get_api_url())
        self.assertEqual(form["inputs"]["OrderID"], tx.reference)

    def test_process_confirms_signed_notification(self):
        tx = self._create_transaction(flow="redirect")
        self.env["payment.transaction"]._process("mypos", self._notification(tx))
        self.assertEqual(tx.state, "done")
        self.assertEqual(tx.provider_reference, "MYPOS-TXREF-1")

    @mute_logger("odoo.addons.payment.models.payment_transaction")
    def test_process_rejects_amount_mismatch(self):
        tx = self._create_transaction(flow="redirect")
        self.env["payment.transaction"]._process(
            "mypos", self._notification(tx, Amount="0.01")
        )
        self.assertEqual(tx.state, "error")

    def test_process_cancel_without_amount(self):
        tx = self._create_transaction(flow="redirect")
        data = OrderedDict(
            [
                ("IPCmethod", "IPCPurchaseNotify"),
                ("OrderID", tx.reference),
                ("Status", "cancel"),
            ]
        )
        data["Signature"] = self.mypos._mypos_sign(data)
        self.env["payment.transaction"]._process("mypos", dict(data))
        self.assertEqual(tx.state, "cancel")

    @mute_logger("odoo.addons.payment_mypos.controllers.main")
    def test_notify_route_confirms_payment(self):
        tx = self._create_transaction(flow="redirect")
        url = self._build_url(MyPosController._notify_url)
        response = self._make_http_post_request(url, data=self._notification(tx))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "OK")
        self.assertEqual(tx.state, "done")

    @mute_logger("odoo.addons.payment_mypos.controllers.main")
    def test_return_route_confirms_payment(self):
        tx = self._create_transaction(flow="redirect")
        url = self._build_url(MyPosController._return_url)
        self._make_http_post_request(url, data=self._notification(tx))
        self.assertEqual(tx.state, "done")

    def test_migration_links_redirect_form(self):
        self.mypos.redirect_form_view_id = False
        path = (
            Path(__file__).parents[1] / "migrations" / "19.0.2.0.1" / "post-migrate.py"
        )
        spec = importlib.util.spec_from_file_location("mypos_mig_19_0_2_0_1", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.migrate(self.env.cr, "19.0.2.0.0")
        self.mypos.invalidate_recordset(["redirect_form_view_id"])
        self.assertEqual(
            self.mypos.redirect_form_view_id,
            self.env.ref("payment_mypos.redirect_form"),
        )
