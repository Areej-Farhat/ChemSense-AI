# ChemSense AI

ChemSense AI is a simple web app for chemistry students. You can load electrochemical data from a CSV file, see it as a graph, and read a plain-language scientific explanation of what the graph shows.

You do **not** need to know how to code to use this app.

---

## What you need first

1. A computer (Windows, Mac, or Linux).
2. **Python 3.10 or newer**.
   - Windows or Mac: download Python from [https://www.python.org/downloads/](https://www.python.org/downloads/).
   - On Windows, during install, tick the box **Add python.exe to PATH**.
3. This project folder: `ChemSense-AI`.

To check if Python is installed, open a terminal (on Windows: PowerShell) and type:

```text
python --version
```

You should see something like `Python 3.12.x`. If that fails, try:

```text
py --version
```

---

## Easiest way on this computer (after the first setup)

On this Windows PC, Python and the app packages are already installed in the project folder.

After that first-time setup is done, double-click **`run_app.bat`**. A terminal window will open, then your browser should show ChemSense AI at `http://localhost:8501`.

If double-clicking does not work yet, follow the first-time steps below.

---

## How to run the app (do this once, then reuse)

Open a terminal in the ChemSense-AI folder.

**Windows (PowerShell):**

```text
cd C:\Users\Cheema\Desktop\ChemSense-AI
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

If PowerShell says scripts are disabled, run this once, then try Activate again:

```text
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

**Mac / Linux:**

```text
cd ~/Desktop/ChemSense-AI
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

Your browser should open automatically at `http://localhost:8501`. If it does not, copy that address into Chrome, Edge, or Firefox.

Leave the terminal window open while you use the app. To stop the app, click the terminal and press `Ctrl + C`.

---

## Next time you want to open the app

You only need to create the virtual environment and install packages the first time.

**Windows:**

```text
cd C:\Users\Cheema\Desktop\ChemSense-AI
.\.venv\Scripts\Activate.ps1
streamlit run app.py
```

**Mac / Linux:**

```text
cd ~/Desktop/ChemSense-AI
source .venv/bin/activate
streamlit run app.py
```

---

## How to use ChemSense AI

1. In the sidebar, choose **Use the built-in sample dataset** to try the app immediately.
2. Or upload your own CSV file.
3. If needed, pick which column is X (usually Potential or Time) and which column is Y (usually Current).
4. Read the graph and the explanation below it.

A CSV file is a spreadsheet saved as comma-separated values. In Excel or Google Sheets, use **File → Save As / Download → CSV**.

### Suggested column names

The app works best when your file has clear headers, for example:

- Cyclic voltammetry: `Potential_V`, `Current_uA`
- Time-based experiment: `Time_s`, `Current_uA`

Other common names such as `E`, `V`, `I`, `current`, and `time` are also recognized.

---

## Sample data included

The folder `sample_data` contains:

- `cyclic_voltammetry_sample.csv` — a typical current vs potential curve (cyclic voltammogram).
- `chronoamperometry_sample.csv` — current vs time after a potential step.

---

## Troubleshooting

**`python` is not recognized**  
Python is not installed, or it is not on PATH. Reinstall Python and tick **Add python.exe to PATH**.

**`streamlit` is not recognized**  
Activate the virtual environment first (the `Activate.ps1` or `source .venv/bin/activate` step), then run `pip install -r requirements.txt` again.

**The graph looks empty or wrong**  
Check that the CSV has a header row and at least two numeric columns. Then choose the X and Y columns in the sidebar.

**Windows blocked Activate.ps1**  
Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, then activate again.
