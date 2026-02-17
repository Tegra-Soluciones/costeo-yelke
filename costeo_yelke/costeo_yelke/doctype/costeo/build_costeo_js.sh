#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODULES_DIR="${SCRIPT_DIR}/modules"
OUTPUT_FILE="${SCRIPT_DIR}/costeo.js"

MODULE_ORDER=(
  "00_constants.js"
  "10_main_form_events.js"
  "20_filters_and_cleanup.js"
  "30_automation_documents.js"
  "35_validations.js"
  "37_production_plan_tab.js"
  "38_production_plan_child_events.js"
  "40_bom_creation.js"
  "50_subcontracting_bom_creation.js"
  "60_child_table_events.js"
  "70_tree_view.js"
  "80_detail_editor_modal.js"
  "90_calculations.js"
  "99_utils_and_styles.js"
)

{
  echo "// AUTO-GENERATED FILE."
  echo "// Source modules: costeo_yelke/costeo_yelke/doctype/costeo/modules/"
  echo "// Build command: ./costeo_yelke/costeo_yelke/doctype/costeo/build_costeo_js.sh"
  echo

  for module in "${MODULE_ORDER[@]}"; do
    module_path="${MODULES_DIR}/${module}"
    if [[ ! -f "${module_path}" ]]; then
      echo "Missing module: ${module_path}" >&2
      exit 1
    fi

    echo "// -----------------------------------------------------------------------------"
    echo "// Module: ${module}"
    echo "// -----------------------------------------------------------------------------"
    cat "${module_path}"
    echo
  done
} > "${OUTPUT_FILE}"

echo "Generated: ${OUTPUT_FILE}"
