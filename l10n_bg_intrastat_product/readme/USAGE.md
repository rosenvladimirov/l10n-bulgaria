[ This file must be present and contains the usage instructions
  for end-users. As all other rst files included in the README,
  it MUST NOT contain reStructuredText sections
  only body text (paragraphs, lists, tables, etc). Should you need
  a more elaborate structure to explain the addon, please create a
  Sphinx documentation (which may include this file as a "quick start"
  section). ]

To use this module, you need to:

1. Go to Invoicing > Reporting > Intrastat > Generic Intrastat Product Declaration.
2. Create a new record.
3. Select or input following data:
   1. Year
   2. Month
   3. Type: for selecting if arrivals or dispatches.
   4. Reporting level: standard or extended.
   5. Action:
      - if "Nihil", no recomputation is possible and the report is considered empty.
      - if "Replace", everything is recomputed.
      - if "Append", only new lines are added.
4. Click on "Generate Lines from invoices" for populating transaction lines.

    You can review them on "Transactions" page of the report.
5. Click on "Generate Declaration Lines" for populating the lines that summarize transactions and will be the source for the exports.

   You can review them on "Declaration Lines" page.
6. Click on "Confirm" for getting the XML file for declaring the report.
7. Click on "paperclip" bellow and download file.
