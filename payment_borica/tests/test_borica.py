# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from werkzeug.exceptions import Forbidden

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon

from ..const import API_URL_TEST, SALE_SIGN_FIELDS
from ..controllers.main import BoricaController
from .common import BoricaCommon


@tagged("post_install", "-at_install")
class TestBorica(BoricaCommon, PaymentHttpCommon):
    def _rendered_tx(self, **values):
        """Транзакция, минала през формата за пренасочване (така получава ORDER)."""
        tx = self._create_transaction(flow="redirect", **values)
        with mute_logger("odoo.addons.payment.models.payment_transaction"):
            processing_values = tx._get_processing_values()
        return tx, self._extract_values_from_html_form(
            processing_values["redirect_form_html"]
        )

    def test_redirect_form_is_signed_and_points_to_test_gateway(self):
        tx, form = self._rendered_tx()
        inputs = form["inputs"]
        self.assertEqual(form["action"], API_URL_TEST)
        self.assertEqual(inputs["ORDER"], tx.borica_order)
        self.assertEqual(len(inputs["ORDER"]), 6)
        self.assertEqual(inputs["AMOUNT"], f"{self.amount:.2f}")
        self.assertEqual(inputs["CURRENCY"], "EUR")
        self.assertTrue(inputs["BACKREF"].endswith(BoricaController._return_url))
        self.assertNotIn("RFU", inputs)
        signed = dict(inputs, RFU=None)
        self.assertTrue(
            self.borica._borica_verify(signed, inputs["P_SIGN"], SALE_SIGN_FIELDS),
            "P_SIGN of the redirect form must verify against the signed fields",
        )

    def test_orders_differ_even_when_reference_digits_collide(self):
        # „S00012-1“ и „S0001-21“ имат едни и същи цифри — ORDER не бива да съвпада
        tx1, _form = self._rendered_tx(reference="S00012-1")
        tx2, _form = self._rendered_tx(reference="S0001-21")
        self.assertNotEqual(tx1.borica_order, tx2.borica_order)

    def test_approved_response_confirms_transaction(self):
        tx, _form = self._rendered_tx()
        tx._process("borica", self._response(tx))
        self.assertEqual(tx.state, "done")
        self.assertEqual(tx.provider_reference, "INTREF0123456789")

    def test_declined_response_cancels_transaction(self):
        tx, _form = self._rendered_tx()
        tx._process("borica", self._response(tx, ACTION="2", RC="05"))
        self.assertEqual(tx.state, "cancel")

    @mute_logger("odoo.addons.payment.models.payment_transaction")
    def test_amount_mismatch_sets_error(self):
        tx, _form = self._rendered_tx()
        tx._process("borica", self._response(tx, AMOUNT="0.01"))
        self.assertEqual(tx.state, "error")

    def test_search_by_order_finds_the_right_transaction(self):
        tx1, _form = self._rendered_tx(reference="BOR-1")
        tx2, _form = self._rendered_tx(reference="BOR-2")
        found = self.env["payment.transaction"]._search_by_reference(
            "borica", {"ORDER": tx2.borica_order}
        )
        self.assertEqual(found, tx2)
        self.assertNotEqual(found, tx1)

    @mute_logger("odoo.addons.payment_borica.controllers.main")
    def test_verify_signature_rejects_forged_response(self):
        tx, _form = self._rendered_tx()
        data = self._response(tx)
        data["AMOUNT"] = "0.01"
        with self.assertRaises(Forbidden):
            BoricaController._verify_signature(data, tx)
        data.pop("P_SIGN")
        with self.assertRaises(Forbidden):
            BoricaController._verify_signature(data, tx)

    @mute_logger(
        "odoo.addons.payment_borica.controllers.main",
        "odoo.addons.payment.models.payment_transaction",
    )
    def test_return_route_confirms_signed_payment(self):
        tx, _form = self._rendered_tx()
        url = self._build_url(BoricaController._return_url)
        self._make_http_post_request(url, data=self._response(tx))
        self.assertEqual(tx.state, "done")

    @mute_logger(
        "odoo.addons.payment_borica.controllers.main",
        "odoo.addons.payment.models.payment_transaction",
    )
    def test_return_route_ignores_forged_payment(self):
        tx, _form = self._rendered_tx()
        data = self._response(tx)
        data["ACTION"], data["RC"] = "0", "00"
        data["AMOUNT"] = f"{tx.amount + 1:.2f}"  # подписът вече не съвпада
        response = self._make_http_post_request(
            url=self._build_url(BoricaController._return_url), data=data
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(tx.state, "draft")
