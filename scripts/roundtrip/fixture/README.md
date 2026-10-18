# Round-trip fixture

Input for `scripts/roundtrip/run.sh`. `main.ato` is the starting circuit; `variants/*.ato` replace it at later steps. `parts/C25744` and `parts/C1525` come from `scripts/parts/import_lcsc.py` (KiCad 9 formats, bottom-side footprints as every assembled part needs). `parts/MH_M2` is a hand-written mechanical part (NPTH hole, no LCSC number, excluded from BOM and position files) that shows how non-electrical footprints such as the tenting-puck mount are kept on the board.
