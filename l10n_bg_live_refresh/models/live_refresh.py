# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import api, models


class LiveRefresh(models.AbstractModel):
    """Generic bus-driven live-refresh dispatcher.

    Any server code can push a refresh to a user's open backend views::

        self.env["live.refresh"].notify(
            model="account.payment", res_ids=[42], mode="record")

    The browser-side ``live_refresh`` service forwards the bus message to
    the patched Form/List controllers, which reload the matching record or
    list and flash the changed fields / new rows.

    Channels (one per mode):

    - ``live_refresh/record`` -- full record/list reload
    - ``live_refresh/field``  -- reload + flash given fields
    - ``live_refresh/list``   -- reload + highlight given rows
    """

    _name = "live.refresh"
    _description = "Live Refresh Dispatcher"

    _MODE_CHANNEL = {
        "record": "live_refresh/record",
        "field": "live_refresh/field",
        "list": "live_refresh/list",
    }

    @api.model
    def notify(self, model=None, res_ids=None, mode="record",
               fields=None, values=None, user_ids=None):
        """Send a live-refresh bus notification.

        :param model: target model name (browser ignores non-matching views)
        :param res_ids: affected record ids
        :param mode: ``record`` | ``field`` | ``list``
        :param fields: list of field names to flash (mode ``field``)
        :param values: optional ``{field: value}`` dict; when ``fields`` is
            omitted its keys are flashed instead
        :param user_ids: recipient user ids (default: current user)
        """
        channel = self._MODE_CHANNEL.get(mode)
        if not channel:
            raise ValueError("live.refresh: unknown mode %r" % (mode,))
        users = (
            self.env["res.users"].browse(user_ids)
            if user_ids
            else self.env.user
        )
        payload = {
            "model": model,
            "res_ids": list(res_ids or []),
            "mode": mode,
            "fields": list(fields or list((values or {}).keys())),
            "values": values or {},
        }
        bus = self.env["bus.bus"]
        for user in users:
            if user.partner_id:
                bus._sendone(user.partner_id, channel, payload)
        return True


class LiveRefreshMixin(models.AbstractModel):
    """Convenience mixin -- call ``recs._live_refresh_notify()`` on any
    recordset to push a refresh for those records to the current (or given)
    users.
    """

    _name = "live.refresh.mixin"
    _description = "Live Refresh Mixin"

    def _live_refresh_notify(self, mode="record", fields=None,
                             values=None, user_ids=None):
        return self.env["live.refresh"].notify(
            model=self._name,
            res_ids=self.ids,
            mode=mode,
            fields=fields,
            values=values,
            user_ids=user_ids,
        )
