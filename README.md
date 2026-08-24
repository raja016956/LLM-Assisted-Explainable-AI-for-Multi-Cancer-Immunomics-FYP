# ImmunoXAI Insights

Design a modern desktop web application UI for a computational biology platform called "ImmunoXAI – LLM-Assisted Explainable AI for Multi-Cancer Immunomics."

The application is intended for cancer researchers and bioinformatics scientists. Create a clean, professional, medical research interface with a white background, blue accent colors, rounded cards, and a minimalist dashboard.

Generate five connected desktop screens.

1. Login Screen

- ImmunoXAI logo

- Welcome message

- Primary "Continue with Google" button

- Divider with "OR"

- Email and Password fields

- Sign In button

- Clean medical/research aesthetic

2. Dashboard

- Left sidebar: Dashboard, Upload Dataset, Analysis Results, Reports, Logout

- Top navigation with user profile

- Summary cards:

  • Uploaded Datasets

  • Completed Analyses

  • Cancer Types

  • Generated Reports

- Recent Analyses table showing:

  Dataset Name, Cancer Type, Status, Date

3. Upload Dataset

- Dataset Name field

- Cancer Type dropdown (BRCA, LUAD, COAD, SKCM, GBM)

- Model selection dropdown (Random Forest)

- Drag-and-drop CSV upload area

- Upload Dataset button

- Analyze Dataset button

4. Analysis Results

Display realistic computational immunology results for the uploaded dataset "TCGA-BRCA Cohort A".

Prediction Card:

Predicted Tumor Immune Phenotype:

Inflamed (Immune-Active)

Confidence Score:

94.2%

SHAP Feature Importance chart using:

CXCL9

CD8A

GZMB

IFNG

PDCD1

LAG3

Biological Interpretation panel:

"The model predicts an Inflamed (Immune-Active) tumor microenvironment with 94.2% confidence. High expression of CXCL9, CD8A, GZMB, and IFNG suggests strong cytotoxic T-cell infiltration. Elevated PDCD1 and LAG3 indicate immune checkpoint activation and potential responsiveness to immune checkpoint inhibitor therapy."

Add a prominent "Generate Report" button.

5. Reports

Display previously generated reports in a table.

Example rows:

TCGA-BRCA Cohort A — Inflamed

TCGA-LUAD Cohort B — Immune-Excluded

TCGA-COAD Cohort C — Immune-Desert

TCGA-SKCM Cohort D — Inflamed

Each report should include:

- Dataset Name

- Predicted Immune Phenotype

- Generation Date

- Download PDF button

- Download CSV button

Overall Design:

- Professional biomedical software

- Suitable for researchers

- Responsive desktop dashboard

- Consistent spacing and typography

- Modern cards and tables

- Realistic scientific interface rather than a generic analytics dashboard

This project was built with [Lovable](https://lovable.dev).

**Live app**: https://immuno-xai-insight.lovable.app

## Build with Lovable

Continue developing this project in the [Lovable editor](https://lovable.dev/projects/c2313941-c741-4b6f-bf01-54faee1a6ac1).

- **Ship faster**: describe what you want to build and Lovable handles the code.
- **Stay in sync**: every change made in Lovable is committed straight to this repository.
- **Full ownership**: this code is yours. Push to `main` on GitHub and your changes sync back into Lovable, ready for your next prompt.

## Development

Prefer working locally? You need Node.js and npm — [install with nvm](https://github.com/nvm-sh/nvm#installing-and-updating).

```sh
git clone <this-repository-url>
cd <repository-name>
npm i
npm run dev
```
