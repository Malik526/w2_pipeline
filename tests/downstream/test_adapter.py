from w2_pipeline.contracts.w2 import W2Document
from w2_pipeline.downstream.adapter import OutputAdapter
from w2_pipeline.downstream.csv_output import export_csv
from w2_pipeline.downstream.finalize import finalize_document
from w2_pipeline.downstream.json_output import export_json
from w2_pipeline.validation.validator import validate_w2_document


def test_export_json_satisfies_output_adapter_protocol(happy_path_document: W2Document) -> None:
    assert isinstance(export_json, OutputAdapter)


def test_export_csv_satisfies_output_adapter_protocol(happy_path_document: W2Document) -> None:
    assert isinstance(export_csv, OutputAdapter)


def test_both_adapters_produce_equivalent_document_identity(happy_path_document: W2Document) -> None:
    finalized = finalize_document(happy_path_document, validate_w2_document(happy_path_document))

    json_text = export_json(finalized)
    csv_text = export_csv(finalized)

    assert happy_path_document.metadata.document_id in json_text
    assert happy_path_document.employee.ssn in csv_text
