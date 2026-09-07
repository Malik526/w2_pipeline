## All accepted batch (4 known clean-render docs, run from ~/w2_pipeline)

PYTHONPATH=src python3 -m w2_pipeline.cli.run_batch \
  data/evaluation/external/symage-synthetic-us-forms-preview-final/documents/symage_900001-irs_w2_single_page_2026-p0_external_clean_render.png \
  data/evaluation/external/symage-synthetic-us-forms-preview-final/documents/symage_900002-irs_w2_single_page_2026-p0_external_clean_render.png \
  data/evaluation/external/symage-synthetic-us-forms-preview-final/documents/symage_900003-irs_w2_single_page_2026-p0_external_clean_render.png \
  data/evaluation/external/symage-synthetic-us-forms-preview-final/documents/symage_900004-irs_w2_single_page_2026-p0_external_clean_render.png \
  --output-dir output/batch_all_accepted

  ## Mixed Batch (3 accepted + 1 known needs_review — symage_900021 rotated)

  PYTHONPATH=src python3 -m w2_pipeline.cli.run_batch \
  data/evaluation/external/symage-synthetic-us-forms-preview-final/documents/symage_900001-irs_w2_single_page_2026-p0_external_clean_render.png \
  data/evaluation/external/symage-synthetic-us-forms-preview-final/documents/symage_900002-irs_w2_single_page_2026-p0_external_clean_render.png \
  data/evaluation/external/symage-synthetic-us-forms-preview-final/documents/symage_900003-irs_w2_single_page_2026-p0_external_clean_render.png \
  data/evaluation/external/symage-synthetic-us-forms-preview-final/documents/symage_900021-irs_w2_single_page_2026-p0_rotated.png \
  --output-dir output/batch_mixed

