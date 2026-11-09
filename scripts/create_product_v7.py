"""Build the v7 source archive with current, independently recorded evidence."""
from pathlib import Path
import create_product_v6 as package

package.DEST = package.ROOT / "deliverables/data-platform-product-v7.zip"
package.REQUIRED += [
    "docs/product_v7_acceptance.md", "data_pipeline/governance_outcome.py", "data_pipeline/governance_report.py",
    "frontend/src/pages/PreprojectData/types/metricMetadata.ts",
    "frontend/src/pages/PreprojectData/components/QualityMetricCard.test.tsx",
    "frontend/src/pages/PreprojectData/pages/QualityPage.tsx", "frontend/src/pages/PreprojectData/pages/VersionsPage.tsx",
    "evidence/functional_results.json", "evidence/baseline_acceptance.json", "evidence/synthetic_governance_report.md", "evidence/educhat_governance_report.md",
]

if __name__ == "__main__":
    package.main()
