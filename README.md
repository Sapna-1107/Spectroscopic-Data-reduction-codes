# HCT Spectroscopic Reduction Pipeline

A Python pipeline for end-to-end spectroscopic data reduction of spectra obtained with the **2m Himalayan Chandra Telescope (HCT)**, operated by the Indian Institute of Astrophysics (IIA). The pipeline wraps PyRAF/IRAF tasks and MIDAS routines into a menu-driven workflow covering everything from image list creation through wavelength-calibrated, normalised spectra.

---

## File

| File | Purpose |
|------|---------|
| `spectroscopy.py` | Main pipeline script — all reduction steps |
| `Spectroscopy.conf` | Configuration file — instrument parameters and FITS header keywords |

---

## Requirements

### Software

| Package | Notes |
|---------|-------|
| Python 2.x | Script uses `raw_input`, `pyfits`, and `except IOError,e` syntax — Python 2 only |
| [PyRAF](https://github.com/iraf-community/pyraf) | IRAF tasks accessed via `pyraf.iraf` |
| IRAF | Required by PyRAF; tasks used: `apall`, `apsum`, `reidentify`, `identify`, `dispcor`, `hedit`, `imcombine`, `imarith`, `imcopy`, `continuum` |
| [pyfits](https://pyfits.readthedocs.io) | FITS file I/O (superseded by `astropy.io.fits` in Python 3) |
| NumPy | Used for median sky estimation in cosmic ray removal |
| [ESO-MIDAS](https://www.eso.org/sci/software/esomidas/) | Required only for cosmic ray removal (step 2); must be callable as `inmidas` |

### Instrument

Designed for HCT HFOSC (Himalayan Faint Object Spectrograph and Camera) data. Should be adaptable to other instruments by adjusting `Spectroscopy.conf`.

---

## Directory Structure

The pipeline expects the following layout before starting:

```
MotherDIR/                        ← Run the script from here
│
├── Spectroscopy.conf             ← Configuration file (required)
├── Images4Spec.in                ← Created by step 1
├── directories                   ← Created automatically (list of sub-directories)
│
├── night1/                       ← One sub-directory per observing night (or grouping)
│   ├── StarSpectras.txt          ← Created by step 1; updated by steps 2, 4
│   ├── LampSpectras.txt          ← Created by step 1; updated by step 4
│   ├── BiasImages.txt            ← Created by step 1
│   └── *.fits                    ← Raw FITS images
│
├── night2/
│   └── ...
│
└── LampRepo/                     ← Master calibrated arc lamp reference library
    ├── Lamps.list                ← Created by step 1; edit to add lamp/star filenames
    ├── LampDataBase.txt          ← Created by step 5; index of calibrated lamp spectra
    ├── CALIBRATED                ← Sentinel file created after step 5 completes
    └── database/                 ← IRAF database files for arc line identifications
```

---

## Configuration File: `Spectroscopy.conf`

Must be present in `MotherDIR` before running. Each line has the format `KEY= VALUE` (space-separated). All keys are required unless noted.

### Instrument / CCD Parameters

| Key | Example Value | Description |
|-----|---------------|-------------|
| `EPADU=` | `1.22` | Gain in electrons per ADU |
| `READNOISE=` | `4.87` | CCD read noise in electrons |
| `DISPAXIS=` | `1` | Dispersion axis: 1 = horizontal (X), 2 = vertical (Y) |
| `APPERTURE=` | `0.1` | Aperture level for `apall` (`ylevel` parameter) |
| `BACKGROUND=` | `-100:-50,50:100` | Background sample regions for `apall` |
| `TRACEFUNC=` | `legendre` | Trace function for `apall` |
| `TRACEORDER=` | `2` | Polynomial order for trace fitting |
| `BIASSLICING=` | `[1:imgX,1:imgY]` | IRAF image section template for bias slicing; use `imgX`, `imgY`, `biasX`, `biasY` as placeholders |

### Continuum Normalisation Parameters

| Key | Example Value | Description |
|-----|---------------|-------------|
| `NORMFUNC=` | `spline3` | Fitting function for `continuum` task |
| `NORMORDER=` | `10` | Polynomial/spline order for continuum fitting |

### FITS Header Keywords

These tell the pipeline which header cards to read for each image classification decision.

| Key | Example HCT Value | Description |
|-----|-------------------|-------------|
| `EXPTIME=` | `EXPTIME` | Exposure time header keyword |
| `GRISM=` | `GRISM` | Grism/grating identifier keyword |
| `LAMP=` | `LAMP` | Arc lamp status keyword (`OFF` = not a lamp frame) |
| `UT=` | `UT` | UT time keyword |
| `OBJECT=` | `OBJECT` | Object name keyword |
| `COMMENT=` | `COMMENT` | Comment keyword (used during manual inspection) |

### Miscellaneous

| Key | Example Value | Description |
|-----|---------------|-------------|
| `VERBOSE=` | `yes` or `no` | Controls interactivity of IRAF tasks (`yes` = interactive mode) |
| `OUTPUT=` | `output.txt` | Output filename (reserved; not actively used in current code) |
| `BACKUP=` | `BACKUP` | Name of backup directory created by step 0 |

---

## Workflow

Run the script from `MotherDIR`:

```bash
python spectroscopy.py
```

The script reads `Spectroscopy.conf`, then presents a numbered menu. Enter one or more step numbers separated by spaces:

```
Enter the list : 1 3 4 5 6 7
```

Steps execute in the order you enter them.

---

## Steps

### 0 — Backup

Copies all files in `MotherDIR` to `../BACKUPDIR` (as defined by `BACKUP=` in the config).

**Always run this first before any destructive step.**

---

### 1 — Create Image List (`Createlist_subrout`)

Recursively finds all `.fits` files under `MotherDIR`, reads their headers, and classifies each image into one of three categories:

| Condition | Output file |
|-----------|-------------|
| `EXPTIME = 0` | `BiasImages.txt` |
| `LAMP ≠ OFF` | `LampSpectras.txt` |
| Rectangular spectrum, `LAMP = OFF` | `StarSpectras.txt` and `Images4Spec.in` |

A spectrum is considered rectangular (and thus a valid spectroscopic frame) only if the longer axis is more than twice the shorter axis. Dispersion axis is inferred from image shape: if Y > X, `DISPAXIS=2`; otherwise `DISPAXIS=1`.

Also creates `LampRepo/Lamps.list` listing all lamp–grism combinations that need calibrated reference spectra.

**After running step 1:** Edit `LampRepo/Lamps.list` to add the filename of a calibration lamp spectrum and a corresponding star spectrum for each entry (columns 2 and 3). Also review and edit `Images4Spec.in` to remove any unwanted frames.

---

### 2 — Cosmic Ray Removal (`Cosmicrays_subrout`)

Removes cosmic rays from all star and bias frames using ESO-MIDAS `filter/cosmic`. Operates **in-place** — original files are overwritten.

The MIDAS script (`crremove.prg`) written per image:
1. Imports the FITS file to MIDAS `.bdf` format.
2. Runs `filter/cosmic` using the median sky level (estimated from the central quarter of the image), `EPADU`, and `READNOISE`.
3. Exports the result back to FITS.

**Warning:** This step permanently modifies the original FITS files. Always run step 0 (backup) first.

---

### 3 — Manual Inspection (`Manual_Inspection`)

Displays each image in IRAF's `display` task one at a time, printing the object name and comment from the header. Prompts for a decision:

- Press **Enter** to keep the image.
- Enter **`d`** to discard — the image line is deleted from its list file (`StarSpectras.txt`, `LampSpectras.txt`, or `BiasImages.txt`) using `sed`.

Prompts you to choose which lists to inspect: `B` (bias), `L` (lamps), `S` (stars).

Requires an active IRAF/SAOImage DS9 display connection.

---

### 4 — Bias Subtraction (`BiasSub_subrout`)

For each night directory:

1. Determines all unique image dimensions present in the star and lamp lists.
2. For each bias frame, slices it to match each required image dimension (using the `BIASSLICING` template from the config).
3. If more than one bias exists for a given dimension, combines them by median using `imcombine` into `Zero_Y_X.fits`.
4. Subtracts the appropriate master bias from each star and lamp frame using `imarith`, producing `zs<original_name>.fits`.
5. Updates `StarSpectras.txt` and `LampSpectras.txt` by prepending `zs` to all filenames (via `sed -i`).

---

### 5 — Lamp Line Identification (`Lamp_identify_subrout`)

Builds the master arc lamp reference library in `LampRepo/`. Run this **once** per instrument configuration; the `CALIBRATED` sentinel file prevents re-running.

For each lamp–grism combination in `LampRepo/Lamps.list`:

1. Runs `apall` on the reference star spectrum to define the aperture and trace.
2. Runs `apsum` on the lamp spectrum using the star's trace as reference.
3. Runs `iraf.identify` **interactively** — you must manually identify arc lines and achieve an RMS fit of ~0.01 Å.
4. Records the calibrated lamp name, lamp type, and grism ID in `LampRepo/LampDataBase.txt`.

On completion, creates `LampRepo/CALIBRATED`.

**Important:** Line identification in step 5 is interactive. Carefully label lines and verify the wavelength solution RMS is ~0.01 Å before proceeding.

---

### 6 — Spectral Extraction and Wavelength Calibration (`Spectroscopy`)

The main reduction step. For each star spectrum in each night directory:

1. **Aperture extraction** — runs `apall` on the 2D star spectrum to extract the 1D spectrum (`<img>ms.fits`), fitting and subtracting the background.
2. **Lamp matching** — identifies the correct arc lamp for this spectrum by matching the grism ID (read from the star's filename columns) and verifying the lamp frame is at least as large as the star frame.
3. **Lamp extraction** — if not already done, runs `apsum` on the matched lamp frame using the star's aperture trace.
4. **Wavelength solution transfer** — copies the master calibrated lamp spectrum and its IRAF `database/` ID file from `LampRepo/`, then runs `reidentify` to adapt the reference solution to the current lamp frame.
5. **Header update** — adds `REFSPEC1` keyword to the extracted star spectrum pointing to the calibrated lamp.
6. **Dispersion correction** — runs `dispcor` to apply the wavelength solution, producing `S<img>ms.fits`.

Output files per star: `<img>ms.fits` (extracted, uncalibrated) and `S<img>ms.fits` (wavelength-calibrated).

---

### 7 — Continuum Normalisation (`Normalise_Counts`)

Fits and divides out the continuum from all wavelength-calibrated spectra (`Szs*.ms.fits` in each night directory) using the IRAF `continuum` task with the function and order specified in the config.

Output: `NSzs*.ms.fits` — normalised spectra.

---

### 8 — Flux Calibration (`Flux_Calibration`)

**Not yet implemented.** Placeholder function; does nothing currently.

---

## Typical Full Reduction Sequence

```
0   → Backup raw data
1   → Create image lists (then manually edit LampRepo/Lamps.list)
5   → Identify arc lines in LampRepo/ (interactive; run once per instrument config)
2   → Remove cosmic rays (overwrites originals — backup must already be done)
3   → Manual inspection (reject bad frames)
4   → Bias subtraction
6   → Spectral extraction + wavelength calibration
7   → Continuum normalisation
```

---

## Output File Naming Convention

| Prefix | Meaning |
|--------|---------|
| `zs` | Bias-subtracted (`zero-subtracted`) |
| `zs<img>ms.fits` | Extracted 1D spectrum from bias-subtracted image |
| `Szs<img>ms.fits` | Wavelength-calibrated extracted spectrum |
| `NSzs<img>ms.fits` | Normalised, wavelength-calibrated extracted spectrum |

---

## Notes and Known Issues

- **Python 2 only.** The script uses `raw_input()`, `except IOError, e:` syntax, and `pyfits` — none of which are compatible with Python 3 without modification. To modernise: replace `raw_input` → `input`, update exception syntax, and replace `import pyfits` with `from astropy.io import fits as pyfits`.

- **`VERBOSE=no` for batch runs.** Setting `VERBOSE= no` in the config passes `interactive=no` to all IRAF tasks, enabling fully automated (non-interactive) execution of steps 4, 6, and 7. Steps 3 and 5 are always interactive regardless of this setting.

- **Grism ID parsing is HCT-specific.** In `Spectroscopy()`, the grism ID is extracted from columns 1–3 of the `StarSpectras.txt` line (e.g., `"3 Grism 8"`), not from the FITS header directly. If adapting to another telescope, verify this parsing logic matches your header/list format.

- **`LampRepo/CALIBRATED` sentinel.** Step 5 checks for this file and refuses to re-run if it exists. To re-calibrate lamps, delete `LampRepo/CALIBRATED` manually.

- **Bias slicing template.** The `BIASSLICING` config value must use the exact placeholder strings `imgX`, `imgY`, `biasX`, `biasY` which the code replaces at runtime. Example for HCT: `[1:imgX,1:imgY]`.

- **`directories` file.** The pipeline auto-creates this file from `Images4Spec.in` on first run of steps that need it. It lists the subdirectories to process. You can edit it to restrict processing to a subset of nights.
