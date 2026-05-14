# Part of Odoo. See LICENSE file for full copyright and licensing details.
"""EKATTE quarterly sync.

Tracks the periodic refresh of res.city / res.city.types from the
authoritative ЕКАТТЕ classifier published by НСИ. Downloads the
published ZIP deposit, parses the DBF tables (windows-1251), and
upserts res.city records by ЕКАТТЕ code.

The cron is shipped *inactive* by default — operators flip it on once
the source URL and column mapping have been verified against the
current НСИ deposit. The sync is idempotent: re-running matches by
ЕКАТТЕ code and updates only changed fields.
"""
import io
import logging
import tempfile
import zipfile

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Column name aliases for the НСИ DBF deposit. The deposit format has
# shifted between releases, so each canonical key lists every spelling
# seen in the wild.
_DBF_FIELD_ALIASES = {
    "ekatte": ("EKATTE", "Ekatte", "EK_CODE", "EKATTECODE"),
    "name": ("NAME", "Name", "NAME_BG", "T_V_M_NAME"),
    "type_code": ("T_V_M", "TVM", "TYPE", "TIP"),
    "kmetstvo": ("KMETSTVO", "Kmetstvo", "KMT_EKATTE"),
    "obshtina": ("OBSHTINA", "Obshtina", "OBSH_CODE", "OBL_OBSH"),
    "oblast": ("OBLAST", "Oblast", "OBL_CODE"),
    "kategoria": ("KATEGORIA", "Kategoria", "CATEGORY"),
    "altitude": ("ALTITUDE", "Altitude", "NAD_VIS"),
}

_DBF_CANDIDATE_FILENAMES = (
    "EkAtte.dbf",
    "Ekatte.dbf",
    "EKATTE.dbf",
)


class L10nBgEkatteSync(models.Model):
    _name = "l10n.bg.ekatte.sync"
    _description = "EKATTE Quarterly Sync Run"
    _order = "date_started desc, id desc"

    name = fields.Char(
        compute="_compute_name",
        store=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("running", "Running"),
            ("done", "Done"),
            ("error", "Error"),
        ],
        default="draft",
        required=True,
    )
    date_started = fields.Datetime("Started At", readonly=True)
    date_finished = fields.Datetime("Finished At", readonly=True)
    source_url = fields.Char(
        "Source URL",
        default="https://www.nsi.bg/sites/default/files/files/EKATTE/Ekatte.zip",
        help="Authoritative ЕКАТТЕ deposit at НСИ.",
    )
    source_attachment_id = fields.Many2one(
        "ir.attachment",
        string="Manual ZIP/DBF",
        help="Optional uploaded ZIP/DBF — bypasses the HTTP fetch.",
    )
    records_created = fields.Integer("Created", readonly=True)
    records_updated = fields.Integer("Updated", readonly=True)
    records_skipped = fields.Integer("Skipped", readonly=True)
    error_message = fields.Text("Error Message", readonly=True)
    notes = fields.Text("Notes")

    @api.depends("date_started", "state")
    def _compute_name(self):
        for run in self:
            if run.date_started:
                run.name = "EKATTE %s" % fields.Datetime.to_string(run.date_started)
            else:
                run.name = "EKATTE (draft)"

    def action_run(self):
        """Trigger one sync attempt synchronously."""
        self.ensure_one()
        if self.state == "running":
            raise UserError(_("Sync already running."))
        self.write({
            "state": "running",
            "date_started": fields.Datetime.now(),
            "records_created": 0,
            "records_updated": 0,
            "records_skipped": 0,
            "error_message": False,
        })
        try:
            stats = self._do_sync()
            self.write({
                "state": "done",
                "date_finished": fields.Datetime.now(),
                "records_created": stats.get("created", 0),
                "records_updated": stats.get("updated", 0),
                "records_skipped": stats.get("skipped", 0),
            })
        except Exception as exc:  # noqa: BLE001 — top-level boundary
            _logger.exception("EKATTE sync failed")
            self.write({
                "state": "error",
                "date_finished": fields.Datetime.now(),
                "error_message": str(exc),
            })
            raise

    def _do_sync(self):
        zip_bytes = self._fetch_zip_bytes()
        dbf_payload = self._extract_dbf_payload(zip_bytes)
        records = self._parse_dbf(dbf_payload)
        return self._upsert_records(records)

    def _fetch_zip_bytes(self):
        """Return raw zip bytes from attachment OR HTTP source."""
        self.ensure_one()
        if self.source_attachment_id:
            return self.source_attachment_id.raw
        import requests  # local import — keep top-level import optional

        if not self.source_url:
            raise UserError(_("Either source_url or source_attachment_id must be set."))
        _logger.info("EKATTE: fetching %s", self.source_url)
        resp = requests.get(self.source_url, timeout=120)
        resp.raise_for_status()
        return resp.content

    def _extract_dbf_payload(self, zip_bytes):
        """Find the EKATTE DBF inside the deposit ZIP and return its bytes."""
        if not zip_bytes:
            raise UserError(_("Empty payload — nothing to extract."))
        try:
            archive = zipfile.ZipFile(io.BytesIO(zip_bytes))
        except zipfile.BadZipFile:
            # Maybe the upload is a raw DBF, not a ZIP
            if zip_bytes[:1] in (b"\x03", b"\x83"):
                return zip_bytes
            raise UserError(_("Source is not a valid ZIP archive."))
        for candidate in _DBF_CANDIDATE_FILENAMES:
            for entry in archive.namelist():
                if entry.lower().endswith(candidate.lower()):
                    _logger.info("EKATTE: matched DBF entry %s", entry)
                    return archive.read(entry)
        raise UserError(
            _("Could not locate EKATTE DBF inside ZIP. Entries: %s")
            % ", ".join(archive.namelist())
        )

    def _parse_dbf(self, dbf_bytes):
        """Parse DBF bytes into a list of canonical dicts."""
        try:
            from dbfread import DBF
        except ImportError as exc:
            raise UserError(_("Python package 'dbfread' not installed.")) from exc

        # dbfread reads from disk, so write to a tempfile
        with tempfile.NamedTemporaryFile(suffix=".dbf", delete=True) as tmp:
            tmp.write(dbf_bytes)
            tmp.flush()
            table = DBF(
                tmp.name,
                encoding="cp1251",
                char_decode_errors="replace",
                load=True,
                ignore_missing_memofile=True,
            )
            return [self._normalise_record(row) for row in table]

    @staticmethod
    def _pick(row, key):
        for alias in _DBF_FIELD_ALIASES[key]:
            if alias in row and row[alias] not in (None, ""):
                return row[alias]
        return None

    def _normalise_record(self, row):
        return {
            "ekatte": self._pick(row, "ekatte"),
            "name": (self._pick(row, "name") or "").strip(),
            "type_code": str(self._pick(row, "type_code") or "").strip(),
            "kmetstvo": self._pick(row, "kmetstvo"),
            "obshtina": self._pick(row, "obshtina"),
            "oblast": self._pick(row, "oblast"),
            "kategoria": self._pick(row, "kategoria"),
            "altitude": self._pick(row, "altitude"),
        }

    def _upsert_records(self, normalised_records):
        bg = self.env.ref("base.bg", raise_if_not_found=False)
        if not bg:
            raise UserError(_("Bulgaria (base.bg) country record missing."))

        City = self.env["res.city"].with_context(active_test=False)
        type_cache = self._build_type_cache()
        created = updated = skipped = 0

        for rec in normalised_records:
            ekatte = rec["ekatte"]
            if not ekatte or not rec["name"]:
                skipped += 1
                continue
            ekatte = str(ekatte).strip().zfill(5)
            existing = City.search(
                [("l10n_bg_ecattu", "=", ekatte), ("country_id", "=", bg.id)],
                limit=1,
            )
            vals = {
                "name": rec["name"],
                "country_id": bg.id,
                "l10n_bg_ecattu": ekatte,
            }
            type_rec = type_cache.get(rec["type_code"])
            if type_rec:
                vals["l10n_bg_type_settlement_id"] = type_rec.id
            if existing:
                # only write changed fields to keep write_date meaningful
                changed = {k: v for k, v in vals.items() if existing[k] != v}
                if changed:
                    existing.write(changed)
                    updated += 1
                else:
                    skipped += 1
            else:
                City.create(vals)
                created += 1

        return {"created": created, "updated": updated, "skipped": skipped}

    def _build_type_cache(self):
        cache = {}
        for t in self.env["res.city.types"].search([]):
            if t.code:
                cache[t.code.strip()] = t
        return cache

    @api.model
    def _cron_sync(self):
        run = self.create({})
        try:
            run.action_run()
        except Exception:  # noqa: BLE001 — swallow at cron boundary
            _logger.exception("Quarterly EKATTE sync via cron failed")
