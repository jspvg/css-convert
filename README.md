The command to run the needed script is: `python ./script-name.py` or `python3 ./script-name.py` (some MacOS/Linux devices may need to use the python3 version)

`convert-css.py` converts px values to rem/em/unitless, and `clean-css.py`removes trailing zeroes from the converted css

`group-typography.py` reads `input.css`, finds typography tokens that only differ by viewport prefix such as `s`, `m`, and `l`, and writes merged tokens to `grouped_typography.css`.

Default assumptions used by `group-typography.py`:
- root font size: `16px`
- viewport widths: `s=375px`, `m=640px`, `l=1024px`

Example usage:

```bash
python3 group-typography.py
python3 group-typography.py --input input.css --output grouped_typography.css
python3 group-typography.py --viewport s=390 --viewport m=768 --viewport l=1440
```

The script only merges a token group when shared properties like `font-family` and `font-weight` are the same across the matched viewport variants. If those differ, the original viewport-specific tokens are kept.
