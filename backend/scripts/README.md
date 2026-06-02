HireHop import helper
=====================

This folder contains a small script to import HireHop JSON exports into two
JSON files suitable for ingestion into your product/device models.

Files
- `hirehop_import.py` - script. Usage:

```
python hirehop_import.py --input /path/to/inventory.json --mapping hirehop_mapping.json --outdir ./out --dry-run
```

- `hirehop_mapping.json` - default mapping for the HireHop JSON format. Edit
  this file to change field mappings if your export differs.

Output
- `out/products_output.json`
- `out/devices_output.json`

Optional API upload
Set `--api-url` and remove `--dry-run` to POST items to an API that exposes
`/products` and `/devices` endpoints. Provide an API key via `--api-key` if
required.

Notes
- The script is intentionally conservative. It preserves `source_id` and
  `source_serial_id` fields so you can map back to the original HireHop data.
- When a serial entry has `QTY` > 1 it will create that many device entries; if
  `QTY == 1` device entries will include serial, barcode, purchase date and
  price when present.
