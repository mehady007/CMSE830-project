# AI-use disclosure

I used Claude Code as a tool to speed up implementation, not as a substitute for my own work. The project
plan, the data analysis and the methods are my decisions. I specified what needed to be built, the AI wrote
and formatted code and files to that specification, and I ran, checked and corrected the results.

- **Tool/version:** Claude (Anthropic), Claude Opus 5.5, used through the Claude Code desktop app.

- **My contribution (what I decided and did):**
  - **Planning:** I defined the project: the question (which countries grew their economy while clearly
    cutting CO₂, and what changed in their electricity mix), the audience (non-expert users), the structure of
    the analysis, and what the app should show and how it should be organized into tabs.
  - **Data analysis:** I decided which data checks to run (joins, missing data, outliers), how to interpret
    them, and what the cleaned data should contain.
  - **Methods:** I chose the analytical approach and how results are measured, labelled and compared: the
    decoupling label (GDP up and CO₂ down by more than 5%), the 2005 → 2022 main comparison, and the checks on
    robustness (different year pairs and margins) and on whether emissions only moved abroad
    (consumption-based CO₂).
  - **Specific decisions I made:**
    - not to impute missing GDP, and to label such countries "Insufficient data" instead of inventing a verdict;
    - to start all comparisons in 2000, because electricity-mix data are mostly missing in the 1990s and the
      post-Soviet collapse would make some countries look like "decouplers";
    - to remove aggregate rows ("World", "Africa", …) so emissions are not double-counted;
    - to keep the real Kuwait 1991 outlier, annotate it, and use a log scale instead of deleting it;
    - to use a ±5% "about flat" margin and to let app users change it.
  - **Direction:** I wrote the instructions for each piece of AI-written code, reviewed what came back, and
    asked for changes until it matched what I intended.
  - **Verification and interpretation:** I ran the app and the notebook, checked numbers and charts against
    the data, interpreted the results, and drew the conclusions and limitations.


- **How I used the AI as a tool (always at my direction):**
  - **Organizing and formatting:** setting up the project structure (`data/`, `notebooks/`, `docs/`) and
    formatting the notebook, README, figures and slides consistently.
  - **Code writing:** drafting code to my specification: the data-preparation functions, the
    Streamlit app (`app.py`) and the analysis notebook (`notebooks/energy_transition_analysis.ipynb`), with its
    figures in `docs/figures/` and summary numbers in `docs/results.json`. The later additions were also my
    requests: the "Made here or consumed here?" tab (territorial vs. consumption-based CO₂ dumbbell chart), the
    "highlight a country" option on the comparison scatter, and the CO₂-per-person outlier chart.
  - **Debugging:** locating and fixing errors, handling empty or invalid selections, and explaining Streamlit
    syntax (`st.tabs`, `st.cache_data`, `st.plotly_chart`) while I learned it.
  - **Streamlit app building:** implementing the tabs, controls and interactive charts I had planned.
  - **GitHub repository building:** `requirements.txt`, `.gitignore`, `LICENSE`, the README, and getting the
    repository ready for GitHub and Streamlit Cloud.
  - **Presentation:**I asked Claude Code to build the presentation from my own figures, results and story. It produced an initial draft of the slides, and I then revised the content and wording myself.
- **Representative prompts** (paraphrased; each one gives Claude Code my plan or decision to implement, not an
  open request for it to decide):
  - "Build one notebook that follows my plan: data collection, data checks (IDA) and EDA, then the key results,
    using the decoupling definition and the 2005 → 2022 comparison I chose";
  - "Do not impute GDP; label countries without GDP 'Insufficient data', start all comparisons in 2000, and
    keep the Kuwait 1991 outlier with an annotation";
  - "Add the consumption-based CO₂ chart I planned and a highlight-a-country option on the comparison
    scatter, then check the app against the rubric";
  - "The app fails when no country is selected: find the cause and fix it";
  - "Get the repository ready for GitHub and Streamlit Cloud";
  - "Draft the slides from my figures, results and story; I will revise them".

- **How outputs were checked** (run during development with the AI assistant; I reviewed the results and
  did not accept any output without checking it):
  - The app was run locally and every tab and control was tried, including empty selections.
    An automated Streamlit test (`streamlit.testing.v1.AppTest`) also ran the app with every country selected
    and checked that no errors appear.
  - The app (`app.py`) and the self-contained notebook apply the same cleaning steps, and re-running the
    notebook reproduces `docs/results.json` exactly. The numbers in the app, README and
    slides were compared with the notebook outputs and `docs/results.json` (for example, 38 of 164 countries
    decoupled between 2005 and 2022; 26 of 33 decouplers with consumption data also cut consumption-based CO₂).
    The notebook also re-computes the decoupling label by hand and asserts that it matches its `decoupling_table`.
  - The joins, the missing-data counts and the Kuwait 1991 outlier were checked directly with pandas, and chart
    scales, units, labels and colours were checked by looking at each chart.
